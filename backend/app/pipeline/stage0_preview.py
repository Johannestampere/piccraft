"""
Stage 0 — Fast 2D mosaic preview.

Resizes the cutout to a grid, selects a per-image palette subset,
applies Floyd-Steinberg dithering, and produces a flat BuildPlan (depth=1).

Target time: 2-5 seconds.
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

from app.pipeline.palette import nearest_block_from_palette, select_palette

logger = logging.getLogger(__name__)


# Apply Floyd-Steinberg dithering on the image. 
# RGB: (H, W, 3) float32 ; alpha: (H, W) uint8
# Returns (H, W) int array of palette indices (-1 = transparent)
def _floyd_steinberg_dither(rgb: np.ndarray, alpha: np.ndarray, palette_rgb: np.ndarray, palette_names: list[str]) -> np.ndarray:
    h, w = rgb.shape[:2]

    img = rgb.astype(np.float64).copy()
    res = np.full((h, w), -1, dtype=np.int32)

    for y in range(h):
        for x in range(w):
            if alpha[y, x] <= 128:
                continue

            old = img[y, x].copy()
            clamped = np.clip(old, 0, 255)

            name, matched_rgb = nearest_block_from_palette(clamped, palette_rgb, palette_names)
            res[y, x] = palette_names.index(name)

            # Error to be distributed around pixel
            error = old - matched_rgb.astype(np.float64)

            # Distribute error to opaque neighbors only (Floyd-Steinberg coefficients)
            if x + 1 < w and alpha[y, x + 1] > 128:
                img[y, x + 1] += error * (7.0 / 16.0)
            if y + 1 < h:
                if x - 1 >= 0 and alpha[y + 1, x - 1] > 128:
                    img[y + 1, x - 1] += error * (3.0 / 16.0)
                if alpha[y + 1, x] > 128:
                    img[y + 1, x] += error * (5.0 / 16.0)
                if x + 1 < w and alpha[y + 1, x + 1] > 128:
                    img[y + 1, x + 1] += error * (1.0 / 16.0)

    return res


# Generate 2D preview
def generate_preview(cutout_path: str, job_id: str, grid_size: int = 64) -> BuildPlan:
    start = time.perf_counter()

    img = Image.open(cutout_path).convert("RGBA")
    img_resized = img.resize((grid_size, grid_size), Image.LANCZOS)
    pixels = np.array(img_resized)

    alpha = pixels[:, :, 3]
    rgb = pixels[:, :, :3]

    # Select best palette subset for this image
    opaque_mask = alpha > 128
    opaque_rgb = rgb[opaque_mask]

    if len(opaque_rgb) == 0:
        logger.warning("No opaque pixels in cutout")

        return BuildPlan(
            job_id=job_id,
            stage=StageName.preview,
            dimensions=BuildPlanDimensions(width=grid_size, height=grid_size, depth=1),
            blocks=[],
            metadata=BuildPlanMetadata(total_blocks=0, processing_time_ms=0),
        )

    palette_rgb, palette_names = select_palette(opaque_rgb, max_colors=24)

    # Floyd-Steinberg dithering
    dithered = _floyd_steinberg_dither(rgb, alpha, palette_rgb, palette_names)

    # Build block list
    blocks: list[BuildPlanBlock] = []
    palette_set: set[str] = set()

    for row in range(grid_size):
        for col in range(grid_size):
            idx = dithered[row, col]
            if idx < 0:
                continue

            block_name = palette_names[idx]

            blocks.append(BuildPlanBlock(
                x=col,
                y=grid_size - 1 - row,
                z=0,
                block=block_name,
            ))
            
            palette_set.add(block_name)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(f"Stage 0 preview: {len(blocks)} blocks, {len(palette_set)} colors, {elapsed_ms}ms")

    return BuildPlan(
        job_id=job_id,
        stage=StageName.preview,
        dimensions=BuildPlanDimensions(
            width=grid_size,
            height=grid_size,
            depth=1,
        ),
        blocks=blocks,
        metadata=BuildPlanMetadata(
            total_blocks=len(blocks),
            palette_used=sorted(palette_set),
            processing_time_ms=elapsed_ms,
        ),
    )
