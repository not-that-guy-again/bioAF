from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.dependencies import require_role
from app.models.access_log import AccessLog
from app.models.user import User
from app.schemas.access_log import AccessLogEntry, AccessLogListResponse
from app.services.access_log_service import AccessLogService

router = APIRouter(prefix="/api/access-logs", tags=["access-logs"])


@router.get("/never-logged-in")
async def never_logged_in_users(
    current_user: dict = require_role("admin"),
    session: AsyncSession = Depends(get_session),
):
    """List users in the org who have never logged in."""
    org_id = current_user["org_id"]

    logged_in_subq = (
        select(AccessLog.user_id)
        .where(AccessLog.organization_id == org_id)
        .where(AccessLog.resource_type == "auth")
        .where(AccessLog.action == "login")
        .distinct()
        .subquery()
    )

    result = await session.execute(
        select(User.id, User.email, User.name, User.role, User.status, User.created_at)
        .where(User.organization_id == org_id)
        .where(User.id.notin_(select(logged_in_subq.c.user_id)))
        .order_by(User.created_at.asc())
    )
    rows = result.all()

    return {
        "users": [
            {
                "id": r.id,
                "email": r.email,
                "name": r.name,
                "role": r.role,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("", response_model=AccessLogListResponse)
async def list_access_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: int | None = Query(None),
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: dict = require_role("admin"),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    logs, total = await AccessLogService.list_access_logs(
        session,
        org_id,
        page,
        page_size,
        user_id=user_id,
        resource_type=resource_type,
        action=action,
        start_date=start_date,
        end_date=end_date,
    )
    return AccessLogListResponse(
        logs=[AccessLogEntry.model_validate(entry) for entry in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
