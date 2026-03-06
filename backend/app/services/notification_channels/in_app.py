"""In-app notification channel - writes to the notifications table."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

logger = logging.getLogger("bioaf.notifications.in_app")


class InAppChannel:
    @staticmethod
    async def deliver(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        event_type: str,
        title: str,
        message: str,
        severity: str,
        metadata: dict | None = None,
    ) -> Notification:
        notification = Notification(
            organization_id=org_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            severity=severity,
            metadata_json=metadata or {},
        )
        session.add(notification)
        await session.flush()
        logger.info("In-app notification created for user %d: %s", user_id, title)
        return notification
