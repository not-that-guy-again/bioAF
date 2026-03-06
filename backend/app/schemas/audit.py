from datetime import datetime

from pydantic import BaseModel

from app.schemas.experiment import UserSummary


class AuditLogEntry(BaseModel):
    id: int
    timestamp: datetime
    user: UserSummary | None = None
    entity_type: str
    entity_id: int
    action: str
    details: dict | None = None
    previous_value: dict | None = None

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    entries: list[AuditLogEntry]
    total: int
    page: int
    page_size: int


class AuditLogExportRequest(BaseModel):
    format: str = "json"
    experiment_id: int | None = None
    entity_type: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
