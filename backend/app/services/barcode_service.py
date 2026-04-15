"""BarcodeService: per-library barcode map CRUD, reverse lookup, collision detection."""

import asyncio

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.barcode_map import BarcodeMap
from app.models.library import Library
from app.schemas.barcode_map import (
    BarcodeCollisionEntry,
    BarcodeMapBulkCreate,
    BarcodeMapCreate,
)
from app.services import event_types
from app.services.event_bus import event_bus
from app.services.library_service import LibraryService, _canonicalize


MAX_BARCODES_PER_LIBRARY = 10_000


class BarcodeService:
    @staticmethod
    def _build_row(org_id: int, library_id: int, payload: BarcodeMapCreate) -> BarcodeMap:
        seq = _canonicalize(payload.sequence)
        if payload.barcode_type == "library_index" and seq is None:
            raise HTTPException(
                status_code=422,
                detail="library_index rows require a sequence",
            )
        if payload.barcode_type == "library_index" and payload.read_position not in (
            "I1",
            "I2",
        ):
            raise HTTPException(
                status_code=422,
                detail="library_index rows require read_position in {I1, I2}",
            )
        if seq is not None and payload.length is not None and len(seq) != payload.length:
            raise HTTPException(
                status_code=422,
                detail="sequence length does not match declared length",
            )
        return BarcodeMap(
            organization_id=org_id,
            library_id=library_id,
            barcode_type=payload.barcode_type,
            sequence=seq,
            name=payload.name,
            read_position=payload.read_position,
            offset_in_read=payload.offset_in_read,
            length=payload.length,
            allowed_mismatches=payload.allowed_mismatches,
            whitelist_reference=payload.whitelist_reference,
            attributes_json=payload.attributes_json,
        )

    @staticmethod
    async def create_barcode_map(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        payload: BarcodeMapCreate,
    ) -> BarcodeMap:
        await LibraryService._get_library_in_org(session, org_id, library_id)
        row = BarcodeService._build_row(org_id, library_id, payload)
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def bulk_create_barcode_maps(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        payload: BarcodeMapBulkCreate,
    ) -> list[BarcodeMap]:
        await LibraryService._get_library_in_org(session, org_id, library_id)

        existing_count = (
            (await session.execute(select(BarcodeMap).where(BarcodeMap.library_id == library_id))).scalars().all()
        )
        if len(existing_count) + len(payload.entries) > MAX_BARCODES_PER_LIBRARY:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Library {library_id} would exceed {MAX_BARCODES_PER_LIBRARY} "
                    "barcode rows. Use whitelist_reference for large sets."
                ),
            )

        rows = [BarcodeService._build_row(org_id, library_id, entry) for entry in payload.entries]
        session.add_all(rows)
        await session.flush()
        return rows

    @staticmethod
    async def list_barcode_maps_for_library(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        barcode_type: str | None = None,
    ) -> list[BarcodeMap]:
        await LibraryService._get_library_in_org(session, org_id, library_id)
        stmt = select(BarcodeMap).where(BarcodeMap.library_id == library_id)
        if barcode_type is not None:
            stmt = stmt.where(BarcodeMap.barcode_type == barcode_type)
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def lookup_by_sequence(
        session: AsyncSession,
        org_id: int,
        sequence: str,
        barcode_type: str | None = None,
    ) -> list[BarcodeMap]:
        canon = _canonicalize(sequence)
        stmt = select(BarcodeMap).where(
            BarcodeMap.organization_id == org_id,
            BarcodeMap.sequence == canon,
        )
        if barcode_type is not None:
            stmt = stmt.where(BarcodeMap.barcode_type == barcode_type)
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def detect_collisions_in_batch(
        session: AsyncSession,
        org_id: int,
        sequencing_batch_id: int,
    ) -> list[BarcodeCollisionEntry]:
        """Return pairs of libraries in the batch sharing an (i5, i7)."""
        a = aliased(Library)
        b = aliased(Library)
        stmt = select(a, b).where(
            a.organization_id == org_id,
            b.organization_id == org_id,
            a.sequencing_batch_id == sequencing_batch_id,
            b.sequencing_batch_id == sequencing_batch_id,
            a.id < b.id,
            a.i5_sequence.isnot(None),
            a.i7_sequence.isnot(None),
            a.i5_sequence == b.i5_sequence,
            a.i7_sequence == b.i7_sequence,
        )
        results = (await session.execute(stmt)).all()
        out = [
            BarcodeCollisionEntry(
                library_a_id=row[0].id,
                library_b_id=row[1].id,
                i5_sequence=row[0].i5_sequence,
                i7_sequence=row[0].i7_sequence,
            )
            for row in results
        ]
        if out:
            asyncio.create_task(
                event_bus.emit(
                    event_types.BARCODE_COLLISION_DETECTED,
                    {
                        "event_type": event_types.BARCODE_COLLISION_DETECTED,
                        "org_id": org_id,
                        "entity_type": "sequencing_batch",
                        "entity_id": sequencing_batch_id,
                        "collision_count": len(out),
                    },
                )
            )
        return out
