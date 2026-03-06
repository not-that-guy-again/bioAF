from sqlalchemy import func, select
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.dependencies import require_role
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogEntry, AuditLogResponse

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditLogResponse)
async def list_audit_log(
    page: int = 1,
    page_size: int = 25,
    entity_type: str | None = None,
    action: str | None = None,
    current_user: dict = require_role("admin"),
    session: AsyncSession = Depends(get_session),
):
    query = select(AuditLog)

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)

    count_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    result = await session.execute(
        query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    entries = list(result.scalars().all())

    return AuditLogResponse(
        entries=[
            AuditLogEntry(
                id=e.id,
                timestamp=e.timestamp,
                user=None,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                action=e.action,
                details=e.details_json,
                previous_value=e.previous_value_json,
            )
            for e in entries
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
