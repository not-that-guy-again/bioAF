from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.reference_dataset import REFERENCE_CATEGORIES, REFERENCE_SCOPES


# --- Request schemas ---


class ReferenceDatasetFileCreate(BaseModel):
    filename: str
    gcs_uri: str
    size_bytes: int | None = None
    md5_checksum: str | None = None
    file_type: str | None = None


class ReferenceDatasetCreate(BaseModel):
    name: str
    category: str
    scope: str
    version: str
    source_url: str | None = None
    gcs_prefix: str
    total_size_bytes: int | None = None
    md5_manifest_json: dict | None = None
    files: list[ReferenceDatasetFileCreate] = []

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in REFERENCE_CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(REFERENCE_CATEGORIES)}")
        return v

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v not in REFERENCE_SCOPES:
            raise ValueError(f"scope must be one of: {', '.join(REFERENCE_SCOPES)}")
        return v


class ReferenceDeprecateRequest(BaseModel):
    deprecation_note: str
    superseded_by_id: int | None = None


# --- Response schemas ---


class ReferenceDatasetFileResponse(BaseModel):
    id: int
    filename: str
    gcs_uri: str
    size_bytes: int | None
    md5_checksum: str | None
    file_type: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    id: int
    name: str | None = None
    email: str

    model_config = {"from_attributes": True}


class ReferenceDatasetResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    category: str
    scope: str
    version: str
    source_url: str | None
    gcs_prefix: str
    total_size_bytes: int | None
    file_count: int | None
    status: str
    deprecation_note: str | None
    superseded_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferenceDatasetDetailResponse(ReferenceDatasetResponse):
    files: list[ReferenceDatasetFileResponse] = []
    uploaded_by: UserSummary | None = None
    approved_by: UserSummary | None = None


class ReferenceDatasetListResponse(BaseModel):
    references: list[ReferenceDatasetResponse]
    total: int


# --- Impact schemas ---


class ImpactPipelineRun(BaseModel):
    pipeline_run_id: int
    pipeline_name: str
    pipeline_version: str | None
    experiment_id: int | None
    experiment_name: str | None
    status: str
    review_verdict: str | None = None
    completed_at: datetime | None


class ImpactSummary(BaseModel):
    reference_dataset_id: int
    total_pipeline_runs: int
    total_experiments: int
    pipeline_runs: list[ImpactPipelineRun]
