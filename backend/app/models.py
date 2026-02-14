from pydantic import BaseModel
from enum import Enum


class StageStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class StageInfo(BaseModel):
    status: StageStatus = StageStatus.pending
    started_at: str | None = None
    completed_at: str | None = None
    processing_time_ms: int | None = None


class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    current_stage: int
    stages: dict[int, StageInfo]


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
    stage: int
    stage_name: str
    dimensions: BuildPlanDimensions
    orientation: str = "north"
    anchor: str = "bottom_center"
    blocks: list[BuildPlanBlock]
    metadata: BuildPlanMetadata


class ReadyStage(BaseModel):
    job_id: str
    stage: int
    completed_at: str


class ReadyResponse(BaseModel):
    ready: list[ReadyStage]
