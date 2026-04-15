from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.schemas.barcode_map import (
    BarcodeCollisionEntry,
    BarcodeMapBulkCreate,
    BarcodeMapCreate,
    BarcodeMapResponse,
)
from app.services.barcode_service import BarcodeService
from app.services.demux_reconciliation_service import (
    DemuxReconciliationService,
    ReconciliationReport,
)

router = APIRouter(tags=["barcode_maps"])


@router.post("/api/libraries/{library_id}/barcodes", response_model=BarcodeMapResponse)
async def create_barcode(
    library_id: int,
    body: BarcodeMapCreate,
    current_user: dict = require_permission("libraries", "edit"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    row = await BarcodeService.create_barcode_map(session, org_id, library_id, body)
    await session.commit()
    return BarcodeMapResponse.model_validate(row)


@router.post(
    "/api/libraries/{library_id}/barcodes/bulk",
    response_model=list[BarcodeMapResponse],
)
async def bulk_create_barcodes(
    library_id: int,
    body: BarcodeMapBulkCreate,
    current_user: dict = require_permission("libraries", "edit"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    rows = await BarcodeService.bulk_create_barcode_maps(session, org_id, library_id, body)
    await session.commit()
    return [BarcodeMapResponse.model_validate(r) for r in rows]


@router.get("/api/libraries/{library_id}/barcodes", response_model=list[BarcodeMapResponse])
async def list_barcodes(
    library_id: int,
    barcode_type: str | None = Query(default=None),
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    rows = await BarcodeService.list_barcode_maps_for_library(session, org_id, library_id, barcode_type)
    return [BarcodeMapResponse.model_validate(r) for r in rows]


@router.get("/api/barcodes/lookup", response_model=list[BarcodeMapResponse])
async def lookup_barcode(
    sequence: str = Query(...),
    barcode_type: str | None = Query(default=None),
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    rows = await BarcodeService.lookup_by_sequence(session, org_id, sequence, barcode_type)
    return [BarcodeMapResponse.model_validate(r) for r in rows]


@router.get(
    "/api/sequencing-batches/{batch_id}/barcode-collisions",
    response_model=list[BarcodeCollisionEntry],
)
async def list_batch_collisions(
    batch_id: int,
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    return await BarcodeService.detect_collisions_in_batch(session, org_id, batch_id)


@router.post(
    "/api/sequencing-batches/{batch_id}/reconcile",
    response_model=ReconciliationReport,
)
async def reconcile_batch(
    batch_id: int,
    current_user: dict = require_permission("libraries", "edit"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    user_id = int(current_user["sub"])
    report = await DemuxReconciliationService.reconcile_batch(
        session, org_id, batch_id, user_id=user_id
    )
    await session.commit()
    return report
