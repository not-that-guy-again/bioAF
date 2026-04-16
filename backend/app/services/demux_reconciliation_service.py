"""Demux reconciliation: attach newly ingested files to Libraries in a sequencing batch.

Reads all unlinked files in the batch, extracts library identifiers from
each filename, and matches against Libraries in the same batch. Unambiguous
matches set ``File.library_id``; ambiguous or missing matches are reported
so a human can resolve them.
"""

import asyncio
import re

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.component import PlatformConfig
from app.models.file import File
from app.models.library import Library
from app.models.sequencing_batch import SequencingBatch
from app.services import event_types
from app.services.audit_service import log_action
from app.services.event_bus import event_bus


DEMUX_FILENAME_PATTERN_KEY = "demux.filename_pattern"

# Default patterns (tried in order):
#  1. Library external id at the start of the filename (bcl-convert / bcl2fastq).
#     Example: ``LIB-001_S1_L001_R1_001.fastq.gz``.
#  2. Illumina dual-index pair inside the filename: ``_I7+I5_`` or ``_I7-I5_``.
#     Example: ``sample_AAGTCCGT+GCATACGA_L001_R1_001.fastq.gz``.
_DEFAULT_LIBRARY_ID_PATTERN = re.compile(r"^(?P<library_external_id>[^_]+)_")
_DEFAULT_INDEX_PAIR_PATTERN = re.compile(r"_(?P<i7>[ACGTN]{4,16})[+\-](?P<i5>[ACGTN]{4,16})_")


class FileReconciliationOutcome(BaseModel):
    file_id: int
    filename: str
    status: str  # matched | ambiguous | unmatched
    library_id: int | None = None
    reason: str | None = None


class ReconciliationReport(BaseModel):
    sequencing_batch_id: int
    matched: int = 0
    ambiguous: int = 0
    unmatched: int = 0
    outcomes: list[FileReconciliationOutcome] = []


async def _load_custom_pattern(session: AsyncSession) -> re.Pattern | None:
    row = (
        await session.execute(select(PlatformConfig).where(PlatformConfig.key == DEMUX_FILENAME_PATTERN_KEY))
    ).scalar_one_or_none()
    if row is None or not row.value:
        return None
    try:
        return re.compile(row.value)
    except re.error:
        return None


def _extract_identifiers(filename: str, custom: re.Pattern | None) -> dict[str, str]:
    """Return any of library_external_id, i5, i7 that the filename exposes."""
    out: dict[str, str] = {}
    if custom is not None:
        m = custom.search(filename)
        if m:
            out.update({k: v for k, v in m.groupdict().items() if v})
    m1 = _DEFAULT_LIBRARY_ID_PATTERN.match(filename)
    if m1:
        out.setdefault("library_external_id", m1.group("library_external_id"))
    m2 = _DEFAULT_INDEX_PAIR_PATTERN.search(filename)
    if m2:
        out.setdefault("i5", m2.group("i5").upper())
        out.setdefault("i7", m2.group("i7").upper())
    return out


class DemuxReconciliationService:
    @staticmethod
    async def reconcile_batch(
        session: AsyncSession,
        org_id: int,
        batch_id: int,
        user_id: int | None = None,
    ) -> ReconciliationReport:
        batch = await session.get(SequencingBatch, batch_id)
        if batch is None or batch.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Sequencing batch not found")

        libraries = list(
            (
                await session.execute(
                    select(Library).where(
                        Library.organization_id == org_id,
                        Library.sequencing_batch_id == batch_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        files = list(
            (
                await session.execute(
                    select(File).where(
                        File.organization_id == org_id,
                        File.sequencing_batch_id == batch_id,
                        File.library_id.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )

        custom = await _load_custom_pattern(session)
        report = ReconciliationReport(sequencing_batch_id=batch_id)

        for f in files:
            ids = _extract_identifiers(f.filename, custom)
            candidates: list[Library] = []
            if "library_external_id" in ids:
                ext = ids["library_external_id"]
                candidates = [lib for lib in libraries if lib.library_id_external == ext]
            if not candidates and "i5" in ids and "i7" in ids:
                i5, i7 = ids["i5"], ids["i7"]
                candidates = [lib for lib in libraries if lib.i5_sequence == i5 and lib.i7_sequence == i7]

            if len(candidates) == 1:
                lib = candidates[0]
                f.library_id = lib.id
                report.matched += 1
                report.outcomes.append(
                    FileReconciliationOutcome(
                        file_id=f.id,
                        filename=f.filename,
                        status="matched",
                        library_id=lib.id,
                    )
                )
                await log_action(
                    session,
                    user_id,
                    "file",
                    f.id,
                    "library_linked",
                    details={"library_id": lib.id, "source": "demux_reconciliation"},
                )
            elif len(candidates) > 1:
                report.ambiguous += 1
                report.outcomes.append(
                    FileReconciliationOutcome(
                        file_id=f.id,
                        filename=f.filename,
                        status="ambiguous",
                        reason=f"{len(candidates)} candidate libraries in batch",
                    )
                )
            else:
                report.unmatched += 1
                report.outcomes.append(
                    FileReconciliationOutcome(
                        file_id=f.id,
                        filename=f.filename,
                        status="unmatched",
                        reason="no candidate library found in batch",
                    )
                )

        await session.flush()

        asyncio.create_task(
            event_bus.emit(
                event_types.DEMUX_RECONCILED,
                {
                    "event_type": event_types.DEMUX_RECONCILED,
                    "org_id": org_id,
                    "entity_type": "sequencing_batch",
                    "entity_id": batch_id,
                    "matched": report.matched,
                    "ambiguous": report.ambiguous,
                    "unmatched": report.unmatched,
                },
            )
        )
        return report
