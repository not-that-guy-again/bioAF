from datetime import datetime

from pydantic import BaseModel

from app.schemas.notebook_session import ExperimentSummary, UserSummary


class JobResponse(BaseModel):
    id: int
    slurm_job_id: str
    job_name: str | None = None
    partition: str
    status: str
    user: UserSummary | None = None
    experiment: ExperimentSummary | None = None
    cpu_requested: int | None = None
    memory_gb_requested: int | None = None
    cpu_used: int | None = None
    memory_gb_used: int | None = None
    exit_code: int | None = None
    cost_estimate: float | None = None
    submitted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobResubmitRequest(BaseModel):
    pass
