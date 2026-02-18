"""
Stage 2 — Tripo AI image-to-3d -> MC build

Calls the Tripo API to generate a textured 3D mesh from the input image, downloads the GLB, voxelizes it, maps colors to the block palette.
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path

import httpx
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from app.config import settings
from app.models import (
    BuildPlan,
    BuildPlanBlock,
    BuildPlanDimensions,
    BuildPlanMetadata,
    StageName,
)
from app.pipeline.palette import _PALETTE_RGB, _PALETTE_NAMES

logger = logging.getLogger(__name__)

_PAL_RGB = np.array(_PALETTE_RGB, dtype=np.float32)
_TRIPO_BASE = "https://api.tripo3d.ai/v2/openapi"


# Palette lookups
def _nearest_blocks(rgb: np.ndarray) -> list[str]:
    diff = rgb[:, None, :] - _PAL_RGB[None, :, :]
    dist = np.sum(diff ** 2, axis=2)
    indices = np.argmin(dist, axis=1)
    return [_PALETTE_NAMES[i] for i in indices]


# Tripo AI: upload image, return file_token
async def _upload_image(client: httpx.AsyncClient, image_path: str) -> str:
    with open(image_path, "rb") as f:
        data = f.read()

    suffix = Path(image_path).suffix.lstrip(".").lower() or "png"
    resp = await client.post(
        f"{_TRIPO_BASE}/upload",
        headers={"Authorization": f"Bearer {settings.tripo_api_key}"},
        files={"file": (Path(image_path).name, data, f"image/{suffix}")},
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()
    token = body["data"]["image_token"]
    logger.info(f"Tripo upload OK, token={token[:8]}...")
    return token


# Create image_to_model task, return task_id
async def _create_task(client: httpx.AsyncClient, file_token: str) -> str:
    resp = await client.post(
        f"{_TRIPO_BASE}/task",
        headers={
            "Authorization": f"Bearer {settings.tripo_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "type": "image_to_model",
            "file": {
                "type": "png",
                "file_token": file_token,
            },
            "texture": True,
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    task_id = body["data"]["task_id"]
    logger.info(f"Tripo task created: {task_id}")
    return task_id


# Poll until task is complete, return GLB download URL
async def _poll_task(client: httpx.AsyncClient, task_id: str, timeout: int = 300) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = await client.get(
            f"{_TRIPO_BASE}/task/{task_id}",
            headers={"Authorization": f"Bearer {settings.tripo_api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["status"]
        logger.info(f"Tripo task {task_id} status: {status}")

        if status == "success":
            url = data["output"]["model"]["url"]
            return url
        if status in ("failed", "cancelled", "unknown"):
            raise RuntimeError(f"Tripo task {task_id} ended with status: {status}")

        await asyncio.sleep(5)

    raise TimeoutError(f"Tripo task {task_id} timed out after {timeout}s")


# Download GLB file
async def _download_glb(client: httpx.AsyncClient, url: str, dest: str) -> None:
    resp = await client.get(url, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        f.write(resp.content)
    logger.info(f"GLB downloaded to {dest} ({len(resp.content) // 1024} KB)")


# Full Tripo pipeline
async def _generate_glb(image_path: str, glb_path: str) -> None:
    async with httpx.AsyncClient() as client:
        file_token = await _upload_image(client, image_path)
        task_id = await _create_task(client, file_token)
        glb_url = await _poll_task(client, task_id)
        await _download_glb(client, glb_url, glb_path)



# Mesh voxelization
# Returns:
#   coords: (N, 3) int array of (x, y, z) voxel positions
#   colors: (N, 3) float32 RGB colors 0-255 for each voxel
def _voxelize_mesh(glb_path: str, voxel_size: int) -> tuple[np.ndarray, np.ndarray]:

    scene = trimesh.load(glb_path, force="scene")

    # Merge all meshes in the scene
    if isinstance(scene, trimesh.Scene):
        geoms = list(scene.geometry.values())
        if not geoms:
            raise ValueError("No geometry in GLB")
        mesh = trimesh.util.concatenate(geoms)
    else:
        mesh = scene

    # Normalize: fit the longest axis into voxel_size
    bounds = mesh.bounds
    extents = bounds[1] - bounds[0]
    scale = (voxel_size - 1) / max(extents)
    mesh.apply_translation(-bounds[0])
    mesh.apply_scale(scale)

    # Surface sampling for color coverage
    n_surface = voxel_size * voxel_size * 20
    try:
        points, face_idx = trimesh.sample.sample_surface(mesh, n_surface)
        color_vis = mesh.visual.to_color()
        face_colors = color_vis.face_colors[:, :3].astype(np.float32)
        sample_colors = face_colors[face_idx]
    except Exception:
        logger.warning("Color sampling failed, using grey fallback")
        points = trimesh.sample.sample_surface(mesh, n_surface)[0]
        sample_colors = np.full((len(points), 3), 180.0, dtype=np.float32)

    # Bin surface points into voxels, averaging colors per cell
    surf_coords = np.clip(np.floor(points).astype(int), 0, voxel_size - 1)
    vox_color: dict[tuple, list] = {}
    for coord, color in zip(map(tuple, surf_coords), sample_colors):
        vox_color.setdefault(coord, []).append(color)

    surf_vox = np.array(list(vox_color.keys()), dtype=int)
    surf_rgb = np.array(
        [np.mean(v, axis=0) for v in vox_color.values()], dtype=np.float32
    )

    # Solid fill via trimesh voxelization
    try:
        vox_grid = trimesh.voxel.creation.voxelize(mesh, pitch=1.0)
        fill_coords = np.clip(
            vox_grid.sparse_indices.astype(int), 0, voxel_size - 1
        )
    except Exception:
        logger.warning("Voxelization failed, using surface only")
        fill_coords = surf_vox.copy()

    # Color each filled voxel from nearest surface voxel    
    if len(surf_vox) > 0:
        tree = cKDTree(surf_vox)
        _, nearest = tree.query(fill_coords)
        fill_rgb = surf_rgb[nearest]
    else:
        fill_rgb = np.full((len(fill_coords), 3), 180.0, dtype=np.float32)

    # Merge: surface colors take priority over interior fill
    merged: dict[tuple, np.ndarray] = {}
    for coord, rgb in zip(map(tuple, fill_coords), fill_rgb):
        merged[coord] = rgb
    for coord, rgb in zip(map(tuple, surf_vox), surf_rgb):
        merged[coord] = rgb  # overwrite with surface color

    all_coords = np.array(list(merged.keys()), dtype=int)
    all_colors = np.array(list(merged.values()), dtype=np.float32)

    return all_coords, all_colors


# Public entrypoint
def generate_tripo(upload_path: str, job_id: str, voxel_size: int = 64) -> BuildPlan:
    start = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmp_dir:
        glb_path = str(Path(tmp_dir) / f"{job_id}.glb")

        # Run async Tripo pipeline synchronously inside Celery task
        asyncio.run(_generate_glb(upload_path, glb_path))

        coords, colors = _voxelize_mesh(glb_path, voxel_size)

    block_names = _nearest_blocks(colors)

    blocks: list[BuildPlanBlock] = []
    palette_set: set[str] = set()
    for (x, y, z), block in zip(coords, block_names):
        blocks.append(BuildPlanBlock(x=int(x), y=int(y), z=int(z), block=block))
        palette_set.add(block)

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(f"[{job_id}] Stage 2 Tripo: {len(blocks)} blocks in {elapsed_ms}ms")

    return BuildPlan(
        job_id=job_id,
        stage=StageName.final,
        dimensions=BuildPlanDimensions(
            width=voxel_size,
            height=voxel_size,
            depth=voxel_size,
        ),
        blocks=blocks,
        metadata=BuildPlanMetadata(
            total_blocks=len(blocks),
            palette_used=sorted(palette_set),
            processing_time_ms=elapsed_ms,
        ),
    )