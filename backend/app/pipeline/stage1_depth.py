"""
Stage 2 — 360 double-sided relief with quality improvements.

Symmetric extrusion from center z so the build looks the same from front and back.
Includes morphological smoothing and improved color sampling.
"""

import logging
import time

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, binary_dilation

from app.models import (
    BuildPlan,
    BuildPlanBlock,
    BuildPlanDimensions,
    BuildPlanMetadata,
    StageName,
)
from app.pipeline.palette import _PALETTE_RGB, _PALETTE_NAMES

logger = logging.getLogger(__name__)

# Precompute palette array once
_PAL_RGB = np.array(_PALETTE_RGB, dtype=np.float32)  # (N, 3)


# Vectorized nearest-palette-entry lookup.
#
# rgb: (M, 3) float32
# Returns: (M,) int indices into _PALETTE_NAMES
def _nearest_block(rgb: np.ndarray) -> np.ndarray:

    diff = rgb[:, None, :] - _PAL_RGB[None, :, :]   # (M, N, 3)
    dist = np.sum(diff ** 2, axis=2)                  # (M, N)
    return np.argmin(dist, axis=1)                    # (M,)


# Convert cutout + depth map into a 360 degree symmetric 3D BuildPlan.
def generate_360(
    cutout_path: str,
    depth_map: np.ndarray,
    job_id: str,
    voxel_size: int = 64,
    palette_rgb: np.ndarray | None = None,
    palette_names: list[str] | None = None,
) -> BuildPlan:


    start = time.perf_counter()

    img = Image.open(cutout_path).convert("RGBA")
    img_resized = img.resize((voxel_size, voxel_size), Image.LANCZOS)
    pixels = np.array(img_resized)

    alpha = pixels[:, :, 3]          # (H, W)
    rgb   = pixels[:, :, :3].astype(np.float32)  # (H, W, 3)

    # Resize depth to match voxel grid
    depth_img = Image.fromarray(depth_map)
    depth_resized = np.array(
        depth_img.resize((voxel_size, voxel_size), Image.LANCZOS),
        dtype=np.float32,
    )

    # Opaque mask
    opaque_mask = alpha > 128

    if not opaque_mask.any():
        logger.warning("No opaque pixels in cutout")
        max_half = voxel_size // 4

        return BuildPlan(
            job_id=job_id,
            stage=StageName.rough,
            dimensions=BuildPlanDimensions(
                width=voxel_size,
                height=voxel_size,
                depth=max_half * 2,
            ),
            blocks=[],
            metadata=BuildPlanMetadata(total_blocks=0, processing_time_ms=0),
        )

    # Better color sampling: average a 3×3 neighbourhood per pixel
    # This smooths out JPEG artefacts before palette mapping.
    from scipy.ndimage import uniform_filter

    rgb_smooth = np.stack([
        uniform_filter(rgb[:, :, c], size=3)
        for c in range(3)
    ], axis=2)

    # Map opaque pixels to block names using the provided palette (or full palette as fallback)
    pal_rgb = palette_rgb if palette_rgb is not None else _PAL_RGB
    pal_names = palette_names if palette_names is not None else _PALETTE_NAMES

    opaque_rgb = rgb_smooth[opaque_mask]          # (M, 3)

    diff = opaque_rgb[:, None, :] - pal_rgb[None, :, :]
    block_indices = np.argmin(np.sum(diff ** 2, axis=2), axis=1)
    block_names_flat = [pal_names[i] for i in block_indices]

    # Build 3D occupancy grid with symmetric extrusion
    max_half_depth = voxel_size // 4   # 16 for voxel_size=64
    total_depth = max_half_depth * 2  # 32

    # occupancy[row, col, z] = block_name or None
    # We store as a 3D object array for smoothing, then flatten.
    # Dimensions: (H, W, total_depth)

    name_grid = np.empty((voxel_size, voxel_size, total_depth), dtype=object)
    name_grid[:] = None

    center = max_half_depth  # center z index (16)

    name_idx = 0
    for row in range(voxel_size):
        for col in range(voxel_size):
            if not opaque_mask[row, col]:
                name_idx += 1 if opaque_mask[row, col] else 0
                continue

            block_name = block_names_flat[name_idx]
            name_idx += 1

            d = float(depth_resized[row, col])
            # Symmetric extrusion: closer => thicker
            z_half = max(1, round(d * max_half_depth))

            z_lo = center - z_half
            z_hi = center + z_half  # inclusive end +1 in range

            name_grid[row, col, z_lo:z_hi] = block_name

    # Morphological smoothing on the occupancy boolean grid
    # Erode then dilate to remove single-voxel spikes.
    # Keep the same block assignment for surviving voxels.
    occupied = name_grid != None   # noqa: E711 (object array comparison)

    struct = np.ones((3, 3, 3), dtype=bool) # 26-connected neighbourhood

    # Opening: erode then dilate — removes isolated noise voxels
    eroded  = binary_erosion(occupied,  structure=struct, border_value=0)
    smoothed = binary_dilation(eroded,  structure=struct)

    # Any voxel gained back by dilation that had no block name:
    #   fill from nearest occupied neighbour (simple: inherit from same column center)
    # We skip re-filling and just use the block name already in name_grid;
    # dilation can only restore voxels that were eroded, so name_grid values
    # still exist there.

    # Collect final block list
    blocks: list[BuildPlanBlock] = []
    palette_set: set[str] = set()

    for row in range(voxel_size):
        for col in range(voxel_size):
            for z in range(total_depth):
                if not smoothed[row, col, z]:
                    continue

                bname = name_grid[row, col, z]
                if bname is None:
                    # Voxel was re-added by dilation — inherit from nearest
                    # filled z in the same column (prefer center)
                    col_names = name_grid[row, col, :]
                    filled = [n for n in col_names if n is not None]
                    if not filled:
                        continue
                    bname = filled[len(filled) // 2]  # pick middle

                y = voxel_size - 1 - row  # flip: row 0 = top of image = top of build
                blocks.append(BuildPlanBlock(x=col, y=y, z=z, block=bname))
                palette_set.add(bname)

    # Shift build down so the lowest block sits at y=0
    if blocks:
        min_y = min(b.y for b in blocks)

        if min_y > 0:
            blocks = [BuildPlanBlock(x=b.x, y=b.y - min_y, z=b.z, block=b.block) for b in blocks]

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        f"Stage 1: {len(blocks)} blocks, {len(palette_set)} colors, {elapsed_ms}ms"
    )

    return BuildPlan(
        job_id=job_id,
        stage=StageName.rough,
        dimensions=BuildPlanDimensions(
            width=voxel_size,
            height=voxel_size,
            depth=total_depth,
        ),
        blocks=blocks,
        metadata=BuildPlanMetadata(
            total_blocks=len(blocks),
            palette_used=sorted(palette_set),
            processing_time_ms=elapsed_ms,
        ),
    )