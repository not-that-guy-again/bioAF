from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.schemas.sample_swap_check import (
    SampleSwapCheckCreate,
    SampleSwapCheckResolve,
    SampleSwapCheckResponse,
)
from app.services.sample_swap_service import SampleSwapService

router = APIRouter(tags=["sample_swap_checks"])


@router.get(
    "/api/libraries/{library_id}/swap-checks",
    response_model=list[SampleSwapCheckResponse],
)
async def list_swap_checks(
    library_id: int,
    unresolved_only: bool = Query(default=False),
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    rows = await SampleSwapService.list_checks(session, org_id, library_id, unresolved_only)
    return [SampleSwapCheckResponse.model_validate(r) for r in rows]


@router.post(
    "/api/libraries/{library_id}/swap-checks",
    response_model=SampleSwapCheckResponse,
)
async def create_swap_check(
    library_id: int,
    body: SampleSwapCheckCreate,
    current_user: dict = require_permission("libraries", "edit"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    row = await SampleSwapService.create_check(session, org_id, library_id, body)
    await session.commit()
    return SampleSwapCheckResponse.model_validate(row)


@router.patch(
    "/api/swap-checks/{check_id}/resolve",
    response_model=SampleSwapCheckResponse,
)
async def resolve_swap_check(
    check_id: int,
    body: SampleSwapCheckResolve,
    current_user: dict = require_permission("libraries", "edit"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    user_id = int(current_user["sub"])
    row = await SampleSwapService.resolve_check(session, org_id, check_id, body, user_id=user_id)
    await session.commit()
    return SampleSwapCheckResponse.model_validate(row)
