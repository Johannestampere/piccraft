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
import trimesh      # lib for working with triangle meshes
from scipy.spatial import cKDTree

from app.config import settings
from app.models import (
    BuildPlan,
    BuildPlanBlock,
    BuildPlanDimensions,
    BuildPlanMetadata,
    StageName,
)
from app.pipeline.palette import _PALETTE_LAB, _PALETTE_NAMES, _rgb_to_lab

logger = logging.getLogger(__name__)

_TRIPO_BASE = "https://api.tripo3d.ai/v2/openapi"


# Map (N, 3) float32 RGB 0-255 -> block names using perceptual LAB distance
def _nearest_blocks(rgb: np.ndarray) -> list[str]:
    rgb_lab = _rgb_to_lab(rgb)
    diff = rgb_lab[:, None, :] - _PALETTE_LAB[None, :, :]
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

    if resp.status_code != 200:
        logger.error(f"Tripo task creation failed {resp.status_code}: {resp.text}")
        
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
            output = data.get("output", {})
            logger.info(f"Tripo output: {output}")
            # model is a direct URL string (not a nested object)
            url = (
                output.get("model")
                or output.get("base_model")
                or output.get("pbr_model")
            )
            if not url:
                raise RuntimeError(f"No model URL in Tripo output: {output}")
            # handle if API returns a dict with url key instead of plain string
            if isinstance(url, dict):
                url = url["url"]
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



# Return (N, 3) float32 RGB colors for each sample face index.
# Tries UV+texture first, then to_color(), then gray fallback.
# Inputs:
#   geom - triangle mesh
#   fidx - array of triangle indices
def _sample_mesh_colors(geom: trimesh.Trimesh, fidx: np.ndarray) -> np.ndarray:

    # Method 1: UV texture sampling
    try:
        visual = geom.visual # get the mesh appearance data (UV coords, materials, face/vertex colors)

        uv = getattr(visual, "uv", None) # UV has shape (V, 2) - one row for each vertex, row[0] = U, row[1] = V

        if uv is not None and len(uv) > 0:
            material = getattr(visual, "material", None) # get the texture images

            tex_img = None

            if material is not None:
                tex_img = getattr(material, "baseColorTexture", None) or getattr(material, "image", None)

            # For each triangle, figure out where the triangle sits on the texture image via UV-s
            # and grab the RBG pixel from that location.
            if tex_img is not None:
                # convert tex_img into RGB format, shape (H, W, 3)
                tex = np.array(tex_img.convert("RGB"), dtype=np.float32)
                # now tex[y, x] returns an RGB color

                H, W = tex.shape[:2]
                uv_arr = np.array(uv)  # (V, 2)

                # Average UV across the 3 vertices of each sampled face
                #   geom.faces[fidx] - (N, 3) vertex indices
                #   uv_arr[geom.faces[fidx]] - (N, 3, 2) UV's for each face's 3 vertices
                #   .mean(axis=1) - (N,2) one representative UV per sampled face
                face_uv = uv_arr[geom.faces[fidx]].mean(axis=1)  # (N, 2)

                # Convert UV coordinates into pixel coordinates
                px = np.clip((face_uv[:, 0] * W).astype(int), 0, W - 1)
                py = np.clip(((1.0 - face_uv[:, 1]) * H).astype(int), 0, H - 1)

                return tex[py, px]

    except Exception as e:
        logger.debug(f"UV texture sampling failed: {e}")

    # Method 2
    try:
        cv = geom.visual.to_color()
        return cv.face_colors[fidx, :3].astype(np.float32)
    except Exception as e:
        logger.debug(f"to_color() failed: {e}")

    # Method 
    logger.warning("All color methods failed for submesh, using grey")
    return np.full((len(fidx), 3), 180.0, dtype=np.float32)


# Mesh voxelization
# Returns:
#   coords: (N, 3) int array of (x, y, z) voxel positions
#   colors: (N, 3) float32 RGB colors 0-255 for each voxel
def _voxelize_mesh(glb_path: str, voxel_size: int) -> tuple[np.ndarray, np.ndarray]:

    scene = trimesh.load(glb_path, force="scene")

    if not isinstance(scene, trimesh.Scene):
        scene_geoms = {"mesh": scene}
    else:
        scene_geoms = scene.geometry

    if not scene_geoms:
        raise ValueError("No geometry in GLB")

    # Compute scene-level bounds for normalization using merged mesh
    raw_meshes = list(scene_geoms.values())
    merged_raw = trimesh.util.concatenate(raw_meshes)
    bounds = merged_raw.bounds
    extents = bounds[1] - bounds[0]
    scale = (voxel_size - 1) / max(extents)
    translation = -bounds[0]

    # Decide how many surface samples per submesh
    n_per_mesh = max(500, (voxel_size * voxel_size * 20) // len(scene_geoms))
    all_points: list[np.ndarray] = []
    all_colors: list[np.ndarray] = []

    # For each submesh, 
    # sample N_PER_MESH random points on its surface,
    # compute an RGB color for each sampled point using _sample_mesh_colors,
    # store them
    for geom in scene_geoms.values():
        try:
            pts, fidx = trimesh.sample.sample_surface(geom, n_per_mesh)
            # Apply the same normalization as the merged mesh
            pts = (pts + translation) * scale

            sc = _sample_mesh_colors(geom, fidx)

            all_points.append(pts)
            all_colors.append(sc)
        except Exception as e:
            logger.warning(f"Sampling failed for submesh: {e}")

    if not all_points:
        raise ValueError("Could not sample any points from GLB")

    points = np.concatenate(all_points)
    sample_colors = np.concatenate(all_colors)

    # Use merged + normalized mesh for voxelization only
    mesh = merged_raw
    mesh.apply_translation(translation)
    mesh.apply_scale(scale)

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
def generate_tripo(cutout_path: str, job_id: str, voxel_size: int = 64) -> BuildPlan:
    start = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmp_dir:
        glb_path = str(Path(tmp_dir) / f"{job_id}.glb")

        # Run async Tripo pipeline synchronously inside Celery task
        asyncio.run(_generate_glb(cutout_path, glb_path))

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