"""Library service: create/update libraries and maintain derived library_index barcodes.

Canonicalisation rule (§6): all index sequences are uppercased and validated
against ``[ACGTN]`` before persistence. Invalid input raises 422.
"""

import asyncio
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barcode_map import BarcodeMap
from app.models.file import File
from app.models.library import Library
from app.models.sample import Sample, sample_files
from app.schemas.library import LibraryCreate, LibraryUpdate
from app.services import event_types
from app.services.audit_service import log_action
from app.services.event_bus import event_bus


_SEQ_RE = re.compile(r"^[ACGTN]+$")


def _canonicalize(seq: str | None) -> str | None:
    if seq is None:
        return None
    cleaned = seq.strip().upper()
    if cleaned == "":
        return None
    if not _SEQ_RE.match(cleaned):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid barcode sequence: '{seq}'. Must match [ACGTN]+.",
        )
    return cleaned


class LibraryService:
    @staticmethod
    async def _assert_sample_in_org(session: AsyncSession, org_id: int, sample_id: int) -> Sample:
        """Verify sample belongs to an experiment in the caller's organization."""
        from app.models.experiment import Experiment

        row = (
            await session.execute(
                select(Sample, Experiment.organization_id)
                .join(Experiment, Sample.experiment_id == Experiment.id)
                .where(Sample.id == sample_id)
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Sample not found")
        sample, sample_org_id = row
        if sample_org_id != org_id:
            raise HTTPException(status_code=403, detail="Sample belongs to another organization")
        return sample

    @staticmethod
    async def _get_library_in_org(session: AsyncSession, org_id: int, library_id: int) -> Library:
        lib = await session.get(Library, library_id)
        if lib is None or lib.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Library not found")
        return lib

    @staticmethod
    async def rebuild_library_index_barcodes(session: AsyncSession, library: Library) -> None:
        """Delete and regenerate library_index BarcodeMap rows from the library's index fields."""
        existing = (
            (
                await session.execute(
                    select(BarcodeMap).where(
                        BarcodeMap.library_id == library.id,
                        BarcodeMap.barcode_type == "library_index",
                    )
                )
            )
            .scalars()
            .all()
        )
        for row in existing:
            await session.delete(row)
        await session.flush()

        # Mapping: i7 -> I1, i5 -> I2 (standard Illumina convention).
        if library.i7_sequence:
            session.add(
                BarcodeMap(
                    organization_id=library.organization_id,
                    library_id=library.id,
                    barcode_type="library_index",
                    sequence=library.i7_sequence,
                    read_position="I1",
                    length=len(library.i7_sequence),
                )
            )
        if library.i5_sequence:
            session.add(
                BarcodeMap(
                    organization_id=library.organization_id,
                    library_id=library.id,
                    barcode_type="library_index",
                    sequence=library.i5_sequence,
                    read_position="I2",
                    length=len(library.i5_sequence),
                )
            )
        await session.flush()

    @staticmethod
    async def create_library(
        session: AsyncSession,
        org_id: int,
        payload: LibraryCreate,
        user_id: int | None = None,
    ) -> Library:
        await LibraryService._assert_sample_in_org(session, org_id, payload.sample_id)

        i5 = _canonicalize(payload.i5_sequence)
        i7 = _canonicalize(payload.i7_sequence)

        lib = Library(
            organization_id=org_id,
            sample_id=payload.sample_id,
            library_id_external=payload.library_id_external,
            prep_kit=payload.prep_kit,
            prep_protocol_version=payload.prep_protocol_version,
            prep_date=payload.prep_date,
            assay_type=payload.assay_type,
            molecule_type=payload.molecule_type,
            strandedness=payload.strandedness,
            read_layout=payload.read_layout,
            target_read_length=payload.target_read_length,
            index_type=payload.index_type,
            i5_sequence=i5,
            i7_sequence=i7,
            i5_orientation_convention=payload.i5_orientation_convention,
            insert_size_mean=payload.insert_size_mean,
            molarity_nm=payload.molarity_nm,
            concentration_ng_ul=payload.concentration_ng_ul,
            qc_status=payload.qc_status,
            qc_notes=payload.qc_notes,
            sequencing_batch_id=payload.sequencing_batch_id,
            notes=payload.notes,
        )
        session.add(lib)
        await session.flush()

        await LibraryService.rebuild_library_index_barcodes(session, lib)

        await log_action(
            session,
            user_id,
            "library",
            lib.id,
            "created",
            details={"sample_id": lib.sample_id, "index_type": lib.index_type},
        )
        asyncio.create_task(
            event_bus.emit(
                event_types.LIBRARY_CREATED,
                {
                    "event_type": event_types.LIBRARY_CREATED,
                    "org_id": org_id,
                    "entity_type": "library",
                    "entity_id": lib.id,
                },
            )
        )
        return lib

    @staticmethod
    async def update_library(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        payload: LibraryUpdate,
        user_id: int | None = None,
    ) -> Library:
        lib = await LibraryService._get_library_in_org(session, org_id, library_id)

        data = payload.model_dump(exclude_unset=True)
        index_changed = False
        for key, value in data.items():
            if key in ("i5_sequence", "i7_sequence"):
                value = _canonicalize(value)
                if getattr(lib, key) != value:
                    index_changed = True
            if key == "index_type" and getattr(lib, key) != value:
                index_changed = True
            setattr(lib, key, value)
        await session.flush()

        if index_changed:
            await LibraryService.rebuild_library_index_barcodes(session, lib)

        await log_action(
            session,
            user_id,
            "library",
            lib.id,
            "updated",
            details={k: v for k, v in data.items()},
        )
        asyncio.create_task(
            event_bus.emit(
                event_types.LIBRARY_UPDATED,
                {
                    "event_type": event_types.LIBRARY_UPDATED,
                    "org_id": org_id,
                    "entity_type": "library",
                    "entity_id": lib.id,
                },
            )
        )
        return lib

    @staticmethod
    async def get_library(session: AsyncSession, org_id: int, library_id: int) -> Library:
        return await LibraryService._get_library_in_org(session, org_id, library_id)

    @staticmethod
    async def list_libraries_for_sample(session: AsyncSession, org_id: int, sample_id: int) -> list[Library]:
        await LibraryService._assert_sample_in_org(session, org_id, sample_id)
        rows = (
            (
                await session.execute(
                    select(Library).where(
                        Library.organization_id == org_id,
                        Library.sample_id == sample_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    @staticmethod
    async def list_libraries_for_experiment(session: AsyncSession, org_id: int, experiment_id: int) -> list[Library]:
        from app.models.experiment import Experiment

        exp = await session.get(Experiment, experiment_id)
        if exp is None or exp.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Experiment not found")
        rows = (
            (
                await session.execute(
                    select(Library)
                    .join(Sample, Library.sample_id == Sample.id)
                    .where(
                        Library.organization_id == org_id,
                        Sample.experiment_id == experiment_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    @staticmethod
    async def attach_file(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        file_id: int,
        user_id: int | None = None,
    ) -> Library:
        lib = await LibraryService._get_library_in_org(session, org_id, library_id)
        f = await session.get(File, file_id)
        if f is None or f.organization_id != org_id:
            raise HTTPException(status_code=404, detail="File not found")

        f.library_id = lib.id

        existing = (
            await session.execute(
                select(sample_files).where(
                    sample_files.c.file_id == f.id,
                    sample_files.c.sample_id == lib.sample_id,
                )
            )
        ).first()
        if existing is None:
            await session.execute(sample_files.insert().values(sample_id=lib.sample_id, file_id=f.id))

        await session.flush()

        await log_action(
            session,
            user_id,
            "library",
            lib.id,
            "file_attached",
            details={"file_id": f.id, "sample_id": lib.sample_id},
        )
        asyncio.create_task(
            event_bus.emit(
                event_types.LIBRARY_FILE_ATTACHED,
                {
                    "event_type": event_types.LIBRARY_FILE_ATTACHED,
                    "org_id": org_id,
                    "entity_type": "library",
                    "entity_id": lib.id,
                    "file_id": f.id,
                },
            )
        )
        return lib
