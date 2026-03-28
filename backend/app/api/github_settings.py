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


@router.post("/test")
async def test_github_connection(
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    """Test the GitHub connection by generating an installation token and listing repos."""
    import httpx
    import logging

    logger = logging.getLogger("bioaf.github.api")

    try:
        token_data = await GitHubService.get_installation_token(session)
        token = token_data["token"]
    except Exception as e:
        logger.error("GitHub test failed at token generation: %s", e)
        return {"status": "error", "message": f"Failed to generate installation token: {e}"}

    try:
        config = await GitHubService._get_config(session)
        org_name = config.get("github_org_name", "")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/orgs/{org_name}/repos",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json",
                },
                params={"per_page": 5},
            )

        if resp.status_code == 200:
            repos = [r["full_name"] for r in resp.json()]
            return {
                "status": "ok",
                "message": f"Connection verified. Found {len(repos)} repo(s).",
                "repos": repos,
            }
        else:
            return {
                "status": "error",
                "message": f"Token works but repo listing returned {resp.status_code}: {resp.text[:200]}",
            }
    except Exception as e:
        logger.error("GitHub test failed at repo listing: %s", e)
        return {"status": "error", "message": f"Token generated but repo listing failed: {e}"}


@router.delete("/disconnect")
async def disconnect_github(
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    await GitHubService.disconnect(session)
    await session.commit()
    return {"status": "ok"}
