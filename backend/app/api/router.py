import json
import uuid
import logging

import redis
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import settings
from app.models import (
    JobCreated,
    JobState,
    JobStatus,
    StageInfo,
    StageStatus,
    StageName,
    BuildPlan,
    ReadyResponse,
    ReadyStage,
)

from app.storage.local import save_upload, load_build_plan

logger = logging.getLogger(__name__)

router = APIRouter()

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

STAGE_MAP = {
    StageName.preview: 0,
    StageName.rough: 1,
    StageName.final: 2,
}

################ 
### HELPERS ####
################


def _job_key(job_id: str) -> str:
    return f"piccraft:job:{job_id}"


def _get_job_state(job_id: str) -> JobState | None:
    raw = _redis.get(_job_key(job_id))
    if raw is None:
        return None
    return JobState(**json.loads(raw))


def save_job_state(job_state: JobState) -> None:
    _redis.set(
        _job_key(job_state.job_id),
        job_state.model_dump_json(),
        ex=3600 * 24,
    )


# Push a complted stage onto the ready list for plugin polling
def _add_ready(job_id: str, stage: StageName) -> None:

    entry = ReadyStage(
        job_id=job_id,
        stage=stage,
        completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )
    
    _redis.rpush("piccraft:ready", entry.model_dump_json())



################
## ENDPOINTS ###
################


@router.post("/jobs", response_model=JobCreated)
async def create_job(file: UploadFile = File(...)):

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Unsupported image type")

    job_id = uuid.uuid4().hex[:12]

    # Save upload to disk
    await save_upload(job_id, file)

    # Initialize job state in Redis
    initial_state = JobState(
        job_id=job_id,
        status=JobStatus.queued,
        current_stage=None,
        stages={
            StageName.preview: StageInfo(),
            StageName.rough: StageInfo(),
            StageName.final: StageInfo(),
        },
    )
    save_job_state(initial_state)

    # Kick off the pipeline
    from app.tasks.pipeline_tasks import run_pipeline
    run_pipeline.delay(job_id)

    logger.info(f"Job {job_id} created")
    return JobCreated(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job(job_id: str):
    state = _get_job_state(job_id)
    if state is None:
        raise HTTPException(404, "Job not found")
    return state


@router.get("/jobs/{job_id}/stages/{stage}", response_model=BuildPlan)
async def get_build_plan(job_id: str, stage: StageName):
    stage_num = STAGE_MAP[stage]
    plan = load_build_plan(job_id, stage_num)
    if plan is None:
        raise HTTPException(404, "Build plan not ready")
    return plan


# Plugin polls this to discover completed stages
@router.get("/jobs/ready", response_model=ReadyResponse)
async def get_ready_stages():
    items: list[ReadyStage] = []

    # Drain the ready list
    while True:
        raw = _redis.lpop("piccraft:ready")
        if raw is None:
            break
        items.append(ReadyStage(**json.loads(raw)))

    return ReadyResponse(ready=items)