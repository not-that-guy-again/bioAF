"""GitHub App integration settings API endpoints.

Uses the GitHub App Manifest flow so admins never handle App IDs
or private keys directly. The admin enters their GitHub org name,
clicks a button, approves on GitHub, and the platform receives
credentials automatically via callback.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.services.github_service import GitHubService

logger = logging.getLogger("bioaf.github.api")

router = APIRouter(prefix="/api/v1/settings/github", tags=["github-settings"])


class ManifestRequest(BaseModel):
    org_name: str
    callback_url: str


@router.post("/manifest")
async def create_manifest(
    body: ManifestRequest,
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    """Build a GitHub App manifest and return the URL to redirect the user to."""
    manifest = {
        "name": f"bioAF-{body.org_name[:20]}",
        "url": body.callback_url.rsplit("/", 1)[0],
        "hook_attributes": {"url": body.callback_url, "active": False},
        "redirect_url": f"{body.callback_url}",
        "callback_urls": [body.callback_url],
        "public": False,
        "default_permissions": {
            "contents": "write",
            "administration": "write",
            "members": "read",
        },
        "default_events": [],
    }

    # Store org_name now so the callback can use it
    await GitHubService._upsert_config(session, "github_org_name", body.org_name)
    await session.commit()

    return {
        "manifest": manifest,
        "redirect_url": f"https://github.com/organizations/{body.org_name}/settings/apps/new",
    }


@router.post("/callback")
async def manifest_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Handle the GitHub App Manifest callback.

    GitHub redirects back with a `code` query param. We exchange it
    for the full app credentials (id, pem, webhook_secret) and store them.
    No auth required since this is a redirect from GitHub.
    """
    body = await request.json()
    code = body.get("code", "")
    if not code:
        raise HTTPException(400, "Missing code from GitHub callback")

    # Exchange the code for app credentials
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/app-manifests/{code}/conversions",
                headers={"Accept": "application/vnd.github+json"},
            )

        if resp.status_code != 201:
            logger.error("GitHub manifest conversion failed: %s %s", resp.status_code, resp.text)
            raise HTTPException(502, f"GitHub returned {resp.status_code}")

        data = resp.json()
    except httpx.HTTPError as e:
        logger.error("GitHub manifest conversion request failed: %s", e)
        raise HTTPException(502, "Failed to reach GitHub API")

    app_id = str(data.get("id", ""))
    pem = data.get("pem", "")
    owner = data.get("owner", {})
    org_name = owner.get("login", "")

    # Get the installation ID -- the manifest flow creates an installation automatically
    installation_id = ""
    installations = data.get("installations", [])
    if installations:
        installation_id = str(installations[0].get("id", ""))

    # If no installation in the response, fetch it from the app
    if not installation_id and app_id and pem:
        try:
            jwt_token = GitHubService._generate_jwt(app_id, pem)
            async with httpx.AsyncClient() as client:
                inst_resp = await client.get(
                    "https://api.github.com/app/installations",
                    headers={
                        "Authorization": f"Bearer {jwt_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
            if inst_resp.status_code == 200:
                inst_list = inst_resp.json()
                if inst_list:
                    installation_id = str(inst_list[0].get("id", ""))
        except Exception as e:
            logger.warning("Could not fetch installation ID: %s", e)

    if not app_id or not pem:
        raise HTTPException(502, "GitHub did not return app credentials")

    await GitHubService.connect(
        session,
        app_id=app_id,
        installation_id=installation_id,
        org_name=org_name or (await GitHubService.get_status(session)).get("org_name", ""),
        private_key=pem,
    )
    await session.commit()

    logger.info("GitHub App created via manifest flow: app_id=%s org=%s", app_id, org_name)
    return {"status": "ok", "app_id": app_id, "org_name": org_name}


class ManualConnectRequest(BaseModel):
    app_id: str
    installation_id: str
    org_name: str
    private_key: str


@router.post("/connect")
async def connect_github(
    body: ManualConnectRequest,
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    """Manual connect fallback for pre-existing GitHub Apps."""
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
