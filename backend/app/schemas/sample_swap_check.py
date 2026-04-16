from datetime import datetime
from typing import Literal

from pydantic import BaseModel


SwapCheckStatus = Literal["match", "mismatch", "inconclusive"]


class SampleSwapCheckCreate(BaseModel):
    expected_attribute: str
    observed_attribute: str
    status: SwapCheckStatus
    evidence_json: dict | None = None
    run_id: int | None = None


class SampleSwapCheckResolve(BaseModel):
    resolution_notes: str | None = None


class SampleSwapCheckResponse(BaseModel):
    id: int
    organization_id: int
    library_id: int
    run_id: int | None = None
    expected_attribute: str
    observed_attribute: str
    status: str
    evidence_json: dict | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by_user_id: int | None = None
    resolution_notes: str | None = None

    model_config = {"from_attributes": True}
