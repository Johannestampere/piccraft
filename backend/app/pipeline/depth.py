"""
Depth estimation using Depth Anything V2 Base via HuggingFace transformers.

Produces a normalized depth map from a cutout image.
"""

import logging
import time

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

logger = logging.getLogger(__name__)

MODEL_ID = "depth-anything/Depth-Anything-V2-Base-hf"

_model = None
_processor = None


def _load_model():
    global _model, _processor

    if _model is None:
        logger.info("Loading Depth Anything V2...")
        t0 = time.perf_counter()
        _processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        _model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID)
        _model.eval()
        elapsed = time.perf_counter() - t0
        logger.info(f"Depth model loaded in {elapsed:.1f}s")

    return _model, _processor


# Estimate depth from a cutout image (RGBA PNG)
# 
# Returns a (H, W) float32 array normalized to 0-1.
#
# Higher value => closer ; lower value => further.
#
# Transparent pixels = 0.
def estimate_depth(cutout_path: str) -> np.ndarray:

    start = time.perf_counter()

    img = Image.open(cutout_path).convert("RGBA")
    alpha = np.array(img)[:, :, 3]
    rgb = img.convert("RGB")

    model, processor = _load_model()

    # Run depth estimation
    inputs = processor(images=rgb, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)

    # Interpolate to original image size
    predicted_depth = outputs.predicted_depth
    
    depth = torch.nn.functional.interpolate(
        predicted_depth.unsqueeze(1),
        size=(rgb.size[1], rgb.size[0]),  # (H, W)
        mode="bicubic",
        align_corners=False,
    ).squeeze().numpy()

    # Normalize to 0-1 (only opaque pixels)
    opaque = alpha > 128

    if opaque.any():
        d_min = depth[opaque].min()
        d_max = depth[opaque].max()

        if d_max > d_min:
            depth = (depth - d_min) / (d_max - d_min)
        else:
            depth = np.zeros_like(depth)
    else:
        depth = np.zeros_like(depth)

    # Zero out transparent pixels
    depth[~opaque] = 0.0

    elapsed = time.perf_counter() - start
    logger.info(f"Depth estimation: {elapsed:.2f}s")

    return depth.astype(np.float32)
