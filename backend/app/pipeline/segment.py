"""Subject segmentation — extract the main object from a photo."""

import logging
import time

import numpy as np
from PIL import Image
from rembg import remove

logger = logging.getLogger(__name__)

# Remove BG from image using rembg and return (cutout_rbg, mask)
def segment_subject(image_path: str) -> tuple[Image.Image, Image.Image]:

    start = time.perf_counter()

    img = Image.open(image_path).convert("RGB")
    cutout_rgba = remove(img)   # Returns RGBA with transparent background

    # Extract the alpha channel (transparency) as the mask
    mask = cutout_rgba.split()[3]

    # Crop to subject bounding box
    bbox = mask.getbbox()

    # No subject found — use the full image
    if bbox is None:
        logger.warning("No subject detected, using full image")
        mask = Image.new("L", img.size, 255)
        cutout_rgba = img.convert("RGBA")
    else:
        cutout_rgba = cutout_rgba.crop(bbox)
        mask = mask.crop(bbox)

    # Pad to square canvas
    w, h = cutout_rgba.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    offset_x = (side - w) // 2
    offset_y = (side - h) // 2
    canvas.paste(cutout_rgba, (offset_x, offset_y))

    mask_canvas = Image.new("L", (side, side), 0)
    mask_canvas.paste(mask, (offset_x, offset_y))

    elapsed = time.perf_counter() - start
    logger.info(f"Segmentation completed in {elapsed:.2f}s ({side}x{side})")

    # Canvas - RGBA format PIL image
    # Mask Canvas - grayscale format PIL image
    return canvas, mask_canvas


# Save cutout and mask PNGs. Returns (cutout_path, mask_path)
def save_segmentation(cutout: Image.Image, mask: Image.Image, output_dir: str) -> tuple[str, str]:

    from pathlib import Path
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cutout_path = str(out / "cutout.png")
    mask_path = str(out / "mask.png")
    cutout.save(cutout_path)
    mask.save(mask_path)

    return cutout_path, mask_path