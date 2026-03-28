"""GitHub App integration settings API endpoints.

Uses the GitHub App Manifest flow:
1. Admin enters org name, clicks "Install on GitHub"
2. GitHub creates the app, redirects to /callback with a code
3. Backend exchanges code for credentials (app_id, pem, slug)
4. Backend redirects user to install the app on their org
5. GitHub redirects to /installed with the installation_id
6. Backend stores installation_id, redirects to frontend showing "Connected"
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
    """Build a GitHub App manifest and return the redirect URL."""
    from sqlalchemy import text as sa_text

    callback_url = f"{body.base_url}/api/v1/settings/github/callback"
    app_suffix = uuid.uuid4().hex[:6]

    manifest = {
        "name": f"bioAF-{body.org_name[:20]}-{app_suffix}",
        "url": body.base_url,
        "hook_attributes": {"url": callback_url, "active": False},
        "redirect_url": callback_url,
        "setup_url": f"{body.base_url}/api/v1/settings/github/installed",
        "public": False,
        "default_permissions": {
            "contents": "write",
            "administration": "write",
            "members": "read",
        },
        "default_events": [],
    }

    # Store org_name and base_url for callbacks to use
    for key, value in [
        ("github_org_name", body.org_name),
        ("github_setup_base_url", body.base_url),
    ]:
        await session.execute(
            sa_text(
                "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": key, "v": value},
        )
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
    """Step 1 callback: exchange code for app credentials, then redirect to install."""
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
    slug = data.get("slug", "")
    owner = data.get("owner", {})
    org_name = owner.get("login", "")

    if not app_id or not pem:
        logger.error("GitHub did not return app credentials: keys=%s", list(data.keys()))
        return RedirectResponse(f"{frontend_url}?error=missing_credentials")

    # Store app credentials (without installation_id yet)
    org_row = await session.execute(sa_text("SELECT value FROM platform_config WHERE key = 'github_org_name'"))
    stored_org = org_row.scalar() or ""

    await GitHubService.connect(
        session,
        app_id=app_id,
        installation_id="",
        org_name=org_name or stored_org,
        private_key=pem,
    )

    # Store the slug for the install redirect
    await session.execute(
        sa_text(
            "INSERT INTO platform_config (key, value) VALUES ('github_app_slug', :v) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"v": slug},
    )
    await session.commit()

    logger.info("GitHub App created: app_id=%s slug=%s org=%s -- redirecting to install", app_id, slug, org_name)

    # Redirect user to install the app on their org
    install_url = f"https://github.com/apps/{slug}/installations/new"
    return RedirectResponse(install_url)


@router.get("/installed")
async def installation_callback(
    installation_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Step 2 callback: store installation_id after user installs the app."""
    from sqlalchemy import text as sa_text

    row = await session.execute(sa_text("SELECT value FROM platform_config WHERE key = 'github_setup_base_url'"))
    base_url = (row.scalar() or "").strip()
    frontend_url = f"{base_url}/settings/github"

    # Store the installation ID
    await session.execute(
        sa_text(
            "INSERT INTO platform_config (key, value) VALUES ('github_app_installation_id', :v) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"v": installation_id},
    )

    # Clean up temp keys
    await session.execute(
        sa_text("DELETE FROM platform_config WHERE key IN ('github_setup_base_url', 'github_app_slug')")
    )
    await session.commit()

    logger.info("GitHub App installed: installation_id=%s", installation_id)
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
