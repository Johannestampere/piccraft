import json
import os
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.models import BuildPlan

# Safe storage directory initializer
def _storage_path() -> Path:
    p = Path(settings.storage_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


# Saves upload to a specific job's storage
async def save_upload(job_id: str, file: UploadFile) -> str:
    upload_dir = _storage_path() / "uploads" / job_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / "original.jpg"
    content = await file.read()
    dest.write_bytes(content)
    return str(dest)


# Save build plan
def save_build_plan(job_id: str, stage: int, plan: BuildPlan) -> str:
    artifact_dir = _storage_path() / "artifacts" / job_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dest = artifact_dir / f"stage{stage}.json"
    dest.write_text(plan.model_dump_json(indent=2))
    return str(dest)


# Load build plan
def load_build_plan(job_id: str, stage: int) -> BuildPlan | None:
    path = _storage_path() / "artifacts" / job_id / f"stage{stage}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return BuildPlan(**data)


# Get upload path
def get_upload_path(job_id: str) -> str | None:
    path = _storage_path() / "uploads" / job_id / "original.jpg"
    if not path.exists():
        return None
    return str(path)