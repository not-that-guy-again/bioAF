from datetime import datetime

from pydantic import BaseModel, field_validator


class IngestEventResponse(BaseModel):
    id: int
    file_id: int | None = None
    source_bucket: str
    source_path: str
    naming_profile_id: int | None = None
    parsed_project_code: str | None = None
    parsed_experiment_code: str | None = None
    parsed_sample_id: str | None = None
    resolved_project_id: int | None = None
    resolved_experiment_id: int | None = None
    resolved_sample_id: int | None = None
    auto_created_entities: dict | None = None
    ingest_status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestSimulateRequest(BaseModel):
    filename: str
    file_size_bytes: int | None = None
    content_md5: str | None = None

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("filename must not be empty")
        return v


class BulkReassignRequest(BaseModel):
    file_ids: list[int]
    target_project_id: int | None = None
    target_experiment_id: int | None = None
    target_sample_id: int | None = None

    @field_validator("file_ids")
    @classmethod
    def validate_file_ids(cls, v: list[int]) -> list[int]:
        if len(v) == 0:
            raise ValueError("at least one file_id is required")
        return v


class BulkReassignResponse(BaseModel):
    reassigned_count: int
    file_ids: list[int]


class UnclaimedEntityResponse(BaseModel):
    entity_type: str
    entity_id: int
    name: str
    created_at: datetime


class ClaimRequest(BaseModel):
    name: str | None = None
    description: str | None = None
