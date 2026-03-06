from datetime import datetime

from pydantic import BaseModel

from app.schemas.file import FileResponse


class DocumentUpload(BaseModel):
    title: str | None = None
    experiment_id: int | None = None
    sample_id: int | None = None


class DocumentResponse(BaseModel):
    id: int
    title: str | None
    file: FileResponse | None = None
    has_extracted_text: bool = False
    linked_experiment_id: int | None
    linked_sample_id: int | None
    linked_pipeline_run_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentSearchResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentUpdate(BaseModel):
    title: str | None = None


class DocumentLinkRequest(BaseModel):
    experiment_id: int | None = None
    sample_id: int | None = None
    pipeline_run_id: int | None = None
