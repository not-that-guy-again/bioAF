"""GitHub App integration settings API endpoints.

Uses the GitHub App Manifest flow so admins never handle App IDs
or private keys directly. The admin enters their GitHub org name,
clicks a button, approves on GitHub, and the platform receives
credentials automatically via a server-side callback.
"""

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.services.github_service import GitHubService

logger = logging.getLogger("bioaf.github.api")

router = APIRouter(prefix="/api/v1/settings/github", tags=["github-settings"])


class ManifestRequest(BaseModel):
    org_name: str
    base_url: str


@router.post("/manifest")
async def create_manifest(
    body: ManifestRequest,
    current_user: dict = require_permission("settings", "configure"),
    session: AsyncSession = Depends(get_session),
):
    """Build a GitHub App manifest and return the URL to redirect the user to."""
    # Callback goes to the BACKEND endpoint (no auth required, handles code exchange)
    callback_url = f"{body.base_url}/api/v1/settings/github/callback"
    app_suffix = uuid.uuid4().hex[:6]

    manifest = {
        "name": f"bioAF-{body.org_name[:20]}-{app_suffix}",
        "url": body.base_url,
        "hook_attributes": {"url": callback_url, "active": False},
        "redirect_url": callback_url,
        "public": False,
        "default_permissions": {
            "contents": "write",
            "administration": "write",
            "members": "read",
        },
        "default_events": [],
    }

    # Store org_name and base_url for the callback to use
    await GitHubService._upsert_config(session, "github_org_name", body.org_name)
    await GitHubService._upsert_config(session, "github_setup_base_url", body.base_url)
    await session.commit()

    return {
        "manifest": manifest,
        "redirect_url": f"https://github.com/organizations/{body.org_name}/settings/apps/new",
    }


@router.get("/callback")
async def manifest_callback(
    code: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Handle the GitHub App Manifest callback (no auth -- called by GitHub redirect).

    GitHub redirects here with ?code=xxx after the user creates the app.
    We exchange the code for credentials, store them, and redirect to the
    frontend settings page.
    """
    # Get the base URL so we can redirect back to the frontend
    from sqlalchemy import text as sa_text

    row = await session.execute(sa_text("SELECT value FROM platform_config WHERE key = 'github_setup_base_url'"))
    base_url = (row.scalar() or "").strip()

    frontend_url = f"{base_url}/settings/github"

    # Exchange the code for app credentials
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/app-manifests/{code}/conversions",
                headers={"Accept": "application/vnd.github+json"},
            )

        if resp.status_code != 201:
            logger.error("GitHub manifest conversion failed: %s %s", resp.status_code, resp.text)
            return RedirectResponse(f"{frontend_url}?error=github_returned_{resp.status_code}")

        data = resp.json()
    except httpx.HTTPError as e:
        logger.error("GitHub manifest conversion request failed: %s", e)
        return RedirectResponse(f"{frontend_url}?error=github_unreachable")

    app_id = str(data.get("id", ""))
    pem = data.get("pem", "")
    owner = data.get("owner", {})
    org_name = owner.get("login", "")

    if not app_id or not pem:
        logger.error("GitHub did not return app credentials: %s", list(data.keys()))
        return RedirectResponse(f"{frontend_url}?error=missing_credentials")

    # Get the installation ID
    installation_id = ""

    # The manifest conversion response doesn't include installations directly,
    # but the app is auto-installed. Fetch installations via the app JWT.
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
                logger.info("Found installation %s for app %s", installation_id, app_id)
    except Exception as e:
        logger.warning("Could not fetch installation ID: %s", e)

    org_row = await session.execute(sa_text("SELECT value FROM platform_config WHERE key = 'github_org_name'"))
    stored_org = org_row.scalar() or ""
    await GitHubService.connect(
        session,
        app_id=app_id,
        installation_id=installation_id,
        org_name=org_name or stored_org,
        private_key=pem,
    )
    # Clean up temp config
    await session.execute(sa_text("DELETE FROM platform_config WHERE key = 'github_setup_base_url'"))
    await session.commit()

    logger.info("GitHub App created via manifest flow: app_id=%s org=%s", app_id, org_name)
    return RedirectResponse(f"{frontend_url}?connected=true")


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
