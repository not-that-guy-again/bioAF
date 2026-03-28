"""GitHub App integration settings API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.services.github_service import GitHubService

router = APIRouter(prefix="/api/v1/settings/github", tags=["github-settings"])


class GitHubConnectRequest(BaseModel):
    app_id: str
    installation_id: str
    org_name: str
    private_key: str


@router.post("/connect")
async def connect_github(
    body: GitHubConnectRequest,
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    await GitHubService.connect(
        session,
        app_id=body.app_id,
        installation_id=body.installation_id,
        org_name=body.org_name,
        private_key=body.private_key,
    )
    await session.commit()
    return {"status": "ok"}


@router.get("/status")
async def github_status(
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    return await GitHubService.get_status(session)


@router.delete("/disconnect")
async def disconnect_github(
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    await GitHubService.disconnect(session)
    await session.commit()
    return {"status": "ok"}
