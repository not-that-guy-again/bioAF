from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.component import TerraformRunListResponse, TerraformRunResponse
from app.services.terraform_service import TerraformService

router = APIRouter(prefix="/api/terraform", tags=["terraform"])


def _require_admin(request: Request) -> dict:
    current_user = request.state.current_user
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/runs", response_model=TerraformRunListResponse)
async def list_runs(request: Request, session: AsyncSession = Depends(get_session)):
    _require_admin(request)
    runs = await TerraformService.list_runs(session)
    return TerraformRunListResponse(
        runs=[
            TerraformRunResponse(
                id=r.id,
                triggered_by_user_id=r.triggered_by_user_id,
                action=r.action,
                component_key=r.component_key,
                plan_summary=r.plan_summary_json,
                status=r.status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                error_message=r.error_message,
            )
            for r in runs
        ],
        total=len(runs),
    )


@router.get("/runs/active", response_model=TerraformRunResponse | None)
async def get_active_run(request: Request, session: AsyncSession = Depends(get_session)):
    _require_admin(request)
    run = await TerraformService.get_active_run(session)
    if not run:
        return None
    return TerraformRunResponse(
        id=run.id,
        triggered_by_user_id=run.triggered_by_user_id,
        action=run.action,
        component_key=run.component_key,
        plan_summary=run.plan_summary_json,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
    )


@router.get("/runs/{run_id}", response_model=TerraformRunResponse)
async def get_run(run_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    _require_admin(request)
    run = await TerraformService.get_run(session, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return TerraformRunResponse(
        id=run.id,
        triggered_by_user_id=run.triggered_by_user_id,
        action=run.action,
        component_key=run.component_key,
        plan_summary=run.plan_summary_json,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
    )


@router.post("/runs/{run_id}/confirm", response_model=TerraformRunResponse)
async def confirm_run(run_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    current_user = _require_admin(request)
    user_id = int(current_user["sub"])

    try:
        run = await TerraformService.apply_plan(session, run_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await session.commit()
    return TerraformRunResponse(
        id=run.id,
        triggered_by_user_id=run.triggered_by_user_id,
        action=run.action,
        component_key=run.component_key,
        plan_summary=run.plan_summary_json,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
    )


@router.post("/runs/{run_id}/cancel", response_model=TerraformRunResponse)
async def cancel_run(run_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    current_user = _require_admin(request)
    user_id = int(current_user["sub"])

    try:
        run = await TerraformService.cancel_run(session, run_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await session.commit()
    return TerraformRunResponse(
        id=run.id,
        triggered_by_user_id=run.triggered_by_user_id,
        action=run.action,
        component_key=run.component_key,
        plan_summary=run.plan_summary_json,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_message=run.error_message,
    )
