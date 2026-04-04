from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.schemas.backup import (
    BackupSettingsUpdate,
    BackupStatusResponse,
    BackupTierStatus,
    ConfigSnapshot,
    ConfigSnapshotDiff,
    ConfigSnapshotListResponse,
    PostgresSnapshot,
    PostgresSnapshotListResponse,
    RestoreRequest,
    RestoreResponse,
)
from app.services.backup_service import BackupService

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.get("/status", response_model=BackupStatusResponse)
async def get_backup_status(
    current_user: dict = require_permission("backups", "view"),
    session: AsyncSession = Depends(get_session),
):
    status = await BackupService.get_backup_status(session, current_user["org_id"])
    return BackupStatusResponse(
        tiers=[BackupTierStatus(**t) for t in status["tiers"]],
        overall_status=status["overall_status"],
    )


@router.get("/config-snapshots", response_model=ConfigSnapshotListResponse)
async def list_config_snapshots(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = require_permission("backups", "view"),
    session: AsyncSession = Depends(get_session),
):
    snapshots, total = await BackupService.get_config_snapshots(
        session,
        current_user["org_id"],
        page,
        page_size,
    )
    return ConfigSnapshotListResponse(
        snapshots=[ConfigSnapshot(**s) for s in snapshots],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/config-snapshots/{date}/diff", response_model=ConfigSnapshotDiff)
async def get_config_snapshot_diff(
    date: str,
    current_user: dict = require_permission("backups", "view"),
    session: AsyncSession = Depends(get_session),
):
    diff = await BackupService.get_config_snapshot_diff(current_user["org_id"], date)
    return ConfigSnapshotDiff(**diff)


@router.post("/restore/config", response_model=RestoreResponse)
async def restore_config(
    body: RestoreRequest,
    current_user: dict = require_permission("backups", "restore"),
    session: AsyncSession = Depends(get_session),
):
    result = await BackupService.restore_config(
        current_user["org_id"],
        body.restore_point or "latest",
    )
    return RestoreResponse(**result)


@router.get("/postgres-snapshots", response_model=PostgresSnapshotListResponse)
async def list_postgres_snapshots(
    current_user: dict = require_permission("backups", "view"),
    session: AsyncSession = Depends(get_session),
):
    snapshots, total = await BackupService.get_postgres_snapshots(session, current_user["org_id"])
    return PostgresSnapshotListResponse(
        snapshots=[PostgresSnapshot(**s) for s in snapshots],
        total=total,
    )


@router.post("/trigger/postgres")
async def trigger_postgres_backup(
    current_user: dict = require_permission("backups", "create"),
    session: AsyncSession = Depends(get_session),
):
    """Trigger a manual PostgreSQL backup to GCS."""
    result = await BackupService.run_postgres_backup(session, current_user["org_id"])
    if result["status"] == "error":
        raise HTTPException(500, detail=result.get("message", "Backup failed"))
    return result


@router.put("/settings")
async def update_backup_settings(
    body: BackupSettingsUpdate,
    current_user: dict = require_permission("backups", "create"),
    session: AsyncSession = Depends(get_session),
):
    errors = []
    if body.postgres_retention_days is not None and body.postgres_retention_days < 1:
        errors.append("PostgreSQL backup retention must be at least 1 day")
    if body.config_retention_days is not None and body.config_retention_days < 1:
        errors.append("Config backup retention must be at least 1 day")
    if errors:
        raise HTTPException(400, detail="; ".join(errors))

    return {"status": "updated", "settings": body.model_dump(exclude_unset=True)}
