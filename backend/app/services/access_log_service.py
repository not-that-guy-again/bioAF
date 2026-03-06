"""Access log service for tracking user resource access."""

import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_log import AccessLog

logger = logging.getLogger("bioaf.access_log_service")


class AccessLogService:
    @staticmethod
    async def log_access(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        resource_type: str,
        resource_id: str,
        action: str,
        metadata: dict | None = None,
    ) -> AccessLog:
        entry = AccessLog(
            organization_id=org_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            metadata_json=metadata or {},
        )
        session.add(entry)
        await session.flush()
        return entry

    @staticmethod
    async def list_access_logs(
        session: AsyncSession,
        org_id: int,
        page: int = 1,
        page_size: int = 50,
        user_id: int | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[AccessLog], int]:
        base = select(AccessLog).where(AccessLog.organization_id == org_id)
        count_base = select(func.count(AccessLog.id)).where(AccessLog.organization_id == org_id)

        if user_id is not None:
            base = base.where(AccessLog.user_id == user_id)
            count_base = count_base.where(AccessLog.user_id == user_id)
        if resource_type:
            base = base.where(AccessLog.resource_type == resource_type)
            count_base = count_base.where(AccessLog.resource_type == resource_type)
        if action:
            base = base.where(AccessLog.action == action)
            count_base = count_base.where(AccessLog.action == action)
        if start_date:
            base = base.where(func.date(AccessLog.created_at) >= start_date)
            count_base = count_base.where(func.date(AccessLog.created_at) >= start_date)
        if end_date:
            base = base.where(func.date(AccessLog.created_at) <= end_date)
            count_base = count_base.where(func.date(AccessLog.created_at) <= end_date)

        count_result = await session.execute(count_base)
        total = count_result.scalar() or 0

        result = await session.execute(
            base.order_by(AccessLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        logs = list(result.scalars().all())
        return logs, total
