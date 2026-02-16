from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


#####################
     # ENUMS #
#####################


class StageName(str, Enum):
    preview = "preview"
    rough = "rough"
    final = "final"


class StageStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"



#####################
   # JOB MODELS #
#####################


class StageInfo(BaseModel):
    status: StageStatus = StageStatus.pending
    started_at: datetime | None = None
    completed_at: datetime | None = None
    processing_time_ms: int | None = None


# Returned after image upload
class JobCreated(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.queued
    created_at: datetime = Field(default_factory=_utcnow)


# Full job status with per-stage breakdown
class JobState(BaseModel):
    job_id: str
    status: JobStatus
    current_stage: StageName | None = None
    stages: dict[StageName, StageInfo]



#####################
# BUILD PLAN MODELS #
#####################


class BuildPlanBlock(BaseModel):
    x: int
    y: int
    z: int
    block: str


class BuildPlanDimensions(BaseModel):
    width: int
    height: int
    depth: int


class BuildPlanMetadata(BaseModel):
    total_blocks: int
    palette_used: list[str] = []
    processing_time_ms: int = 0


class BuildPlan(BaseModel):
    job_id: str
    stage: StageName
    dimensions: BuildPlanDimensions
    orientation: str = "north"
    anchor: str = "bottom_center"
    blocks: list[BuildPlanBlock]
    metadata: BuildPlanMetadata


###############
# POLLING MODELS
###############


class ReadyStage(BaseModel):
    job_id: str
    stage: StageName
    completed_at: datetime


class ReadyResponse(BaseModel):
    ready: list[ReadyStage]