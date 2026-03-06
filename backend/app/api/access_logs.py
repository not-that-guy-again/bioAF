from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.dependencies import require_role
from app.schemas.access_log import AccessLogEntry, AccessLogListResponse
from app.services.access_log_service import AccessLogService

router = APIRouter(prefix="/api/access-logs", tags=["access-logs"])


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
        session, org_id, page, page_size,
        user_id=user_id, resource_type=resource_type, action=action,
        start_date=start_date, end_date=end_date,
    )
    return AccessLogListResponse(
        logs=[AccessLogEntry.model_validate(entry) for entry in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
