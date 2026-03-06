from datetime import datetime

from pydantic import BaseModel

from app.schemas.experiment import UserSummary
from app.schemas.file import FileResponse


class CellxgenePublishRequest(BaseModel):
    file_id: int
    experiment_id: int | None = None
    dataset_name: str


class CellxgenePublicationResponse(BaseModel):
    id: int
    dataset_name: str
    stable_url: str | None
    status: str
    file: FileResponse | None = None
    experiment_id: int | None
    published_by: UserSummary | None = None
    published_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
