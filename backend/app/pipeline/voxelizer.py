"""
Voxelizer — converts a cutout image + depth map into a 3D BuildPlan.
"""

import logging
import time

import numpy as np
from PIL import Image

from app.models import (
    BuildPlan,
    BuildPlanBlock,
    BuildPlanDimensions,
    BuildPlanMetadata,
    StageName,
)
from app.pipeline.palette import _PALETTE_RGB, _PALETTE_NAMES, map_image_to_blocks

logger = logging.getLogger(__name__)


# Convert cutout + depth map into a 3D voxel BuildPlan.
#
# For each opaque pixel, extrude voxels from z = 0 to z based on depth.
#
# Closer pixels get more extrusion.
def voxelize(cutout_path: str, depth_map: np.ndarray, job_id: str, voxel_size: int = 32) -> BuildPlan:

    start = time.perf_counter()

    img = Image.open(cutout_path).convert("RGBA")
    img_resized = img.resize((voxel_size, voxel_size), Image.LANCZOS)
    pixels = np.array(img_resized)

    alpha = pixels[:, :, 3]
    rgb = pixels[:, :, :3]

    # Resize depth map to match voxel grid
    depth_resized = np.array(
        Image.fromarray(depth_map).resize((voxel_size, voxel_size), Image.LANCZOS)
    )

    max_depth = voxel_size // 4  # 16 blocks deep for 32^3

    # Get block names for all pixels at once (flat array)
    opaque_mask = alpha > 128
    opaque_rgb = rgb[opaque_mask]

    if len(opaque_rgb) == 0:
        logger.warning("No opaque pixels in cutout")
        
        return BuildPlan(
            job_id=job_id,
            stage=StageName.rough,
            dimensions=BuildPlanDimensions(width=voxel_size, height=voxel_size, depth=max_depth),
            blocks=[],
            metadata=BuildPlanMetadata(total_blocks=0, processing_time_ms=0),
        )

    # Map all opaque pixels to block names
    block_names = map_image_to_blocks(opaque_rgb)

    # Build voxel grid
    blocks: list[BuildPlanBlock] = []
    palette_set: set[str] = set()
    name_idx = 0

    for row in range(voxel_size):
        for col in range(voxel_size):
            if not opaque_mask[row, col]:
                continue

            block_name = block_names[name_idx]
            name_idx += 1

            d = depth_resized[row, col]
            z_extent = max(1, int(round(d * max_depth)))

            # y is flipped: row 0 = top of image = top of build
            y = voxel_size - 1 - row

            # Extrude from the back: flat back at z=max_depth-1, textured front
            z_start = max_depth - z_extent
            for z in range(z_start, max_depth):
                blocks.append(BuildPlanBlock(x=col, y=y, z=z, block=block_name))

            palette_set.add(block_name)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(f"Voxelizer: {len(blocks)} blocks, {len(palette_set)} colors, {elapsed_ms}ms")

    return BuildPlan(
        job_id=job_id,
        stage=StageName.rough,
        dimensions=BuildPlanDimensions(
            width=voxel_size,
            height=voxel_size,
            depth=max_depth,
        ),
        blocks=blocks,
        metadata=BuildPlanMetadata(
            total_blocks=len(blocks),
            palette_used=sorted(palette_set),
            processing_time_ms=elapsed_ms,
        ),
    )