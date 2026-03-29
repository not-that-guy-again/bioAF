"""Slack OAuth API endpoints: auth URL, callback, status, disconnect, channels, mappings."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.api.dependencies import require_permission
from app.schemas.notification import (
    SlackAuthUrlResponse,
    SlackChannelMappingCreate,
    SlackChannelMappingResponse,
    SlackChannelMappingUpdate,
    SlackChannelResponse,
    SlackStatusResponse,
)
from app.services.slack_oauth_service import SlackOAuthService

logger = logging.getLogger("bioaf.api.slack_oauth")

router = APIRouter(prefix="/api/notifications/slack", tags=["slack"])


@router.get("/auth-url", response_model=SlackAuthUrlResponse)
async def get_auth_url(
    current_user: dict = require_permission("notifications", "configure"),
    session: AsyncSession = Depends(get_session),
):
    if not settings.slack_client_id or not settings.slack_client_secret:
        raise HTTPException(400, "Slack OAuth is not configured. Set BIOAF_SLACK_CLIENT_ID and BIOAF_SLACK_CLIENT_SECRET.")

    auth_url = SlackOAuthService.build_auth_url(
        org_id=current_user["org_id"],
        user_id=int(current_user["sub"]),
    )
    return SlackAuthUrlResponse(auth_url=auth_url)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Handle the OAuth redirect from Slack. No auth header -- state carries identity."""
    try:
        claims = SlackOAuthService.decode_state(state)
    except Exception:
        raise HTTPException(400, "Invalid or expired state token")

    org_id = claims["org_id"]
    user_id = claims["user_id"]

    try:
        token_data = await SlackOAuthService.exchange_code(code)
    except ValueError as e:
        raise HTTPException(400, str(e))

    install = await SlackOAuthService.save_installation(session, org_id, user_id, token_data)
    await session.commit()

    return {
        "status": "connected",
        "team_name": install.team_name,
        "team_id": install.team_id,
    }


@router.get("/status", response_model=SlackStatusResponse)
async def get_status(
    current_user: dict = require_permission("notifications", "view"),
    session: AsyncSession = Depends(get_session),
):
    status = await SlackOAuthService.get_status(session, current_user["org_id"])
    return SlackStatusResponse(**status)


@router.delete("/disconnect")
async def disconnect(
    current_user: dict = require_permission("notifications", "configure"),
    session: AsyncSession = Depends(get_session),
):
    removed = await SlackOAuthService.disconnect(session, current_user["org_id"])
    if not removed:
        raise HTTPException(404, "No Slack installation found")
    await session.commit()
    return {"disconnected": True}


@router.get("/channels", response_model=list[SlackChannelResponse])
async def list_channels(
    current_user: dict = require_permission("notifications", "configure"),
    session: AsyncSession = Depends(get_session),
):
    install = await SlackOAuthService.get_installation(session, current_user["org_id"])
    if not install:
        raise HTTPException(404, "Slack not connected")

    channels = await SlackOAuthService.list_channels(session, current_user["org_id"])
    return [SlackChannelResponse(**ch) for ch in channels]


# ---- Channel mappings ----


@router.get("/channel-mappings", response_model=list[SlackChannelMappingResponse])
async def list_channel_mappings(
    current_user: dict = require_permission("notifications", "view"),
    session: AsyncSession = Depends(get_session),
):
    mappings = await SlackOAuthService.list_channel_mappings(session, current_user["org_id"])
    return [SlackChannelMappingResponse.model_validate(m) for m in mappings]


@router.post("/channel-mappings", response_model=SlackChannelMappingResponse)
async def create_channel_mapping(
    body: SlackChannelMappingCreate,
    current_user: dict = require_permission("notifications", "configure"),
    session: AsyncSession = Depends(get_session),
):
    install = await SlackOAuthService.get_installation(session, current_user["org_id"])
    if not install:
        raise HTTPException(404, "Slack not connected")

    mapping = await SlackOAuthService.create_channel_mapping(
        session, current_user["org_id"], body.model_dump()
    )
    await session.commit()
    return SlackChannelMappingResponse.model_validate(mapping)


@router.put("/channel-mappings/{mapping_id}", response_model=SlackChannelMappingResponse)
async def update_channel_mapping(
    mapping_id: int,
    body: SlackChannelMappingUpdate,
    current_user: dict = require_permission("notifications", "configure"),
    session: AsyncSession = Depends(get_session),
):
    mapping = await SlackOAuthService.update_channel_mapping(
        session, mapping_id, current_user["org_id"], body.model_dump(exclude_unset=True)
    )
    if not mapping:
        raise HTTPException(404, "Channel mapping not found")
    await session.commit()
    return SlackChannelMappingResponse.model_validate(mapping)


@router.delete("/channel-mappings/{mapping_id}")
async def delete_channel_mapping(
    mapping_id: int,
    current_user: dict = require_permission("notifications", "configure"),
    session: AsyncSession = Depends(get_session),
):
    deleted = await SlackOAuthService.delete_channel_mapping(
        session, mapping_id, current_user["org_id"]
    )
    if not deleted:
        raise HTTPException(404, "Channel mapping not found")
    await session.commit()
    return {"deleted": True}
