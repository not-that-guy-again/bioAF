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

# Neighbour enumeration grows as C(n, k) * 3^k for length n and k mismatches;
# above this length the trigram-index path should be used (not yet implemented).
FUZZY_MAX_LENGTH_WITH_MISMATCHES = 16
_ACGTN = "ACGTN"


def _hamming_neighbours(seq: str, max_mismatches: int) -> set[str]:
    """All ACGTN strings within ``max_mismatches`` Hamming distance of ``seq``."""
    results = {seq}
    frontier = {seq}
    for _ in range(max_mismatches):
        next_frontier: set[str] = set()
        for s in frontier:
            for i in range(len(s)):
                for c in _ACGTN:
                    if c == s[i]:
                        continue
                    neighbour = s[:i] + c + s[i + 1 :]
                    if neighbour not in results:
                        results.add(neighbour)
                        next_frontier.add(neighbour)
        frontier = next_frontier
    return results


def _hamming_distance(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))


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
    async def fuzzy_lookup(
        session: AsyncSession,
        org_id: int,
        sequence: str,
        barcode_type: str | None = None,
        max_mismatches: int = 1,
    ) -> list[tuple[BarcodeMap, int]]:
        """Return (BarcodeMap, distance) pairs with Hamming distance <= max_mismatches."""
        canon = _canonicalize(sequence)
        if canon is None:
            raise HTTPException(status_code=422, detail="Empty sequence")
        if max_mismatches < 0 or max_mismatches > 2:
            raise HTTPException(
                status_code=422,
                detail="max_mismatches must be between 0 and 2",
            )
        if max_mismatches > 0 and len(canon) > FUZZY_MAX_LENGTH_WITH_MISMATCHES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Fuzzy lookup with mismatches is not supported for sequences "
                    f"longer than {FUZZY_MAX_LENGTH_WITH_MISMATCHES}bp. Use exact lookup "
                    "or a whitelist-backed search."
                ),
            )

        neighbours = _hamming_neighbours(canon, max_mismatches)
        stmt = select(BarcodeMap).where(
            BarcodeMap.organization_id == org_id,
            BarcodeMap.sequence.in_(neighbours),
        )
        if barcode_type is not None:
            stmt = stmt.where(BarcodeMap.barcode_type == barcode_type)
        rows = list((await session.execute(stmt)).scalars().all())
        out: list[tuple[BarcodeMap, int]] = []
        for row in rows:
            if row.sequence is None or len(row.sequence) != len(canon):
                continue
            d = _hamming_distance(row.sequence, canon)
            if d <= max_mismatches:
                out.append((row, d))
        return out

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
