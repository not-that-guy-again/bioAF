from datetime import datetime

from pydantic import BaseModel


class TemplateNotebookResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str | None = None
    compatible_with: str | None = None
    parameters: dict
    is_builtin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplateNotebookListResponse(BaseModel):
    notebooks: list[TemplateNotebookResponse]
    total: int


class TemplateCloneRequest(BaseModel):
    new_name: str
    experiment_id: int | None = None
    parameters: dict = {}
