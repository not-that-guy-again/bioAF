from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.dependencies import require_role
from app.schemas.activity_feed import ActivityFeedItem, ActivityFeedListResponse
from app.services.activity_feed_service import ActivityFeedService

router = APIRouter(prefix="/api/activity-feed", tags=["activity-feed"])


@router.get("", response_model=ActivityFeedListResponse)
async def list_activity_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_type: str | None = Query(None),
    entity_type: str | None = Query(None),
    user_id: int | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: dict = require_role("admin", "comp_bio", "bench", "viewer"),
    session: AsyncSession = Depends(get_session),
):
    org_id = current_user["org_id"]
    events, total = await ActivityFeedService.list_events(
        session,
        org_id,
        page,
        page_size,
        event_type=event_type,
        entity_type=entity_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ActivityFeedListResponse(
        events=[ActivityFeedItem.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )
