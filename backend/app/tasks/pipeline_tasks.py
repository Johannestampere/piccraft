"""
Celery tasks for the pipeline.

run_pipeline chains: segment -> stage0 (preview stage).
"""

import json
import logging
import time
from datetime import datetime, timezone

import redis

from app.celery_app import celery
from app.config import settings
from app.models import (
    JobState,
    JobStatus,
    StageInfo,
    StageStatus,
    StageName,
    ReadyStage,
)
from app.storage.local import get_upload_path, save_build_plan
from app.pipeline.segment import segment_subject, save_segmentation
from app.pipeline.stage0_preview import generate_preview

logger = logging.getLogger(__name__)

_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)


##################
### HELPERS ######
##################

def _job_key(job_id: str) -> str:
    return f"piccraft:job:{job_id}"


def _load_state(job_id: str) -> JobState:
    raw = _redis.get(_job_key(job_id))
    if raw is None:
        raise RuntimeError(f"No job state for {job_id}")
    return JobState(**json.loads(raw))


def _save_state(state: JobState) -> None:
    _redis.set(_job_key(state.job_id), state.model_dump_json(), ex=3600 * 24)


def _mark_stage_started(job_id: str, stage: StageName) -> JobState:
    state = _load_state(job_id)
    state.status = JobStatus.processing
    state.current_stage = stage
    state.stages[stage].status = StageStatus.processing
    state.stages[stage].started_at = datetime.now(timezone.utc)
    _save_state(state)
    return state


def _mark_stage_completed(job_id: str, stage: StageName, elapsed_ms: int) -> None:
    state = _load_state(job_id)
    state.stages[stage].status = StageStatus.completed
    state.stages[stage].completed_at = datetime.now(timezone.utc)
    state.stages[stage].processing_time_ms = elapsed_ms
    _save_state(state)

    # Notify the ready list for plugin polling
    entry = ReadyStage(
        job_id=job_id,
        stage=stage,
        completed_at=datetime.now(timezone.utc),
    )
    _redis.rpush("piccraft:ready", entry.model_dump_json())


def _mark_job_failed(job_id: str, stage: StageName) -> None:
    state = _load_state(job_id)
    state.status = JobStatus.failed
    state.stages[stage].status = StageStatus.failed
    _save_state(state)





#######################
## PIPELINE TASK ######
#######################


@celery.task(name="run_pipeline")
def run_pipeline(job_id: str) -> None:
    logger.info(f"[{job_id}] Pipeline started")

    upload_path = get_upload_path(job_id)
    if upload_path is None:
        logger.error(f"[{job_id}] Upload not found")
        return

    # Segmentation of image
    try:
        _mark_stage_started(job_id, StageName.preview)
        t0 = time.perf_counter()

        cutout, mask = segment_subject(upload_path)

        artifact_dir = str(settings.storage_dir) + f"/artifacts/{job_id}"
        cutout_path, mask_path = save_segmentation(cutout, mask, artifact_dir)

        seg_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(f"[{job_id}] Segmentation done in {seg_ms} ms")
    except Exception:
        logger.exception(f"[{job_id}] Segmentation failed")
        _mark_job_failed(job_id, StageName.preview)
        return

    # Stage 0/2: Mosaic preview
    try:
        t0 = time.perf_counter()

        plan = generate_preview(
            cutout_path=cutout_path,
            job_id=job_id,
            grid_size=settings.stage0_grid_size,
        )
        save_build_plan(job_id, stage=0, plan=plan)

        preview_ms = int((time.perf_counter() - t0) * 1000)
        total_ms = seg_ms + preview_ms
        _mark_stage_completed(job_id, StageName.preview, total_ms)
        logger.info(f"[{job_id}] Stage 0 done in {preview_ms}ms (total {total_ms}ms)")
    except Exception:
        logger.exception(f"[{job_id}] Stage 0 failed")
        _mark_job_failed(job_id, StageName.preview)
        return

    # ── Stage 1 & 2: TODO ────────────────────────────────────

    # Mark job completed (for now, only preview stage exists)
    state = _load_state(job_id)
    state.status = JobStatus.completed
    state.current_stage = None
    _save_state(state)
    logger.info(f"[{job_id}] Pipeline finished")