from datetime import datetime

from pydantic import BaseModel


class AccessLogEntry(BaseModel):
    id: int
    user_id: int
    resource_type: str
    resource_id: str
    action: str
    metadata_json: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class AccessLogListResponse(BaseModel):
    logs: list[AccessLogEntry]
    total: int
    page: int
    page_size: int
