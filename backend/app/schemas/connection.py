"""Connection command response schema for SSH access."""

from typing import Literal

from pydantic import BaseModel


class ConnectionCommandResponse(BaseModel):
    command: str
    setup_guide: str
    warning: str
    target_type: Literal["pipeline_job", "notebook_session"]
    target_id: str
    namespace: str | None = None
