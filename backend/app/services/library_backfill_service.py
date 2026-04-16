"""Library backfill: one-shot Library creation for legacy Sample -> File data.

Generates one Library per sample that doesn't already have one, carrying
prep metadata forward from the legacy Sample columns and attaching any
existing sample_files rows to the new Library. Preview-then-commit, so
admins can see what will change before any writes land.
"""

import asyncio

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.file import File
from app.models.library import Library
from app.models.sample import Sample, sample_files
from app.services import event_types
from app.services.audit_service import log_action
from app.services.event_bus import event_bus


class BackfillEntry(BaseModel):
    sample_id: int
    prep_kit: str | None = None
    read_layout: str | None = None
    file_ids: list[int] = []


class BackfillPreview(BaseModel):
    experiment_id: int
    libraries_to_create: int = 0
    files_to_attach: int = 0
    samples_skipped: int = 0
    entries: list[BackfillEntry] = []


class BackfillResult(BaseModel):
    experiment_id: int
    libraries_created: int = 0
    files_attached: int = 0
    samples_skipped: int = 0


async def _plan(
    session: AsyncSession, org_id: int, experiment_id: int
) -> tuple[BackfillPreview, list[Sample], dict[int, list[File]]]:
    exp = await session.get(Experiment, experiment_id)
    if exp is None or exp.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Experiment not found")

    samples = list((await session.execute(select(Sample).where(Sample.experiment_id == experiment_id))).scalars().all())

    existing_library_sample_ids = set(
        (
            await session.execute(
                select(Library.sample_id).where(
                    Library.organization_id == org_id,
                    Library.sample_id.in_([s.id for s in samples]) if samples else select(Library.sample_id),
                )
            )
        )
        .scalars()
        .all()
    )

    preview = BackfillPreview(experiment_id=experiment_id)
    candidates: list[Sample] = []
    files_by_sample: dict[int, list[File]] = {}

    for s in samples:
        if s.id in existing_library_sample_ids:
            preview.samples_skipped += 1
            continue
        linked_files = list(
            (
                await session.execute(
                    select(File)
                    .join(sample_files, sample_files.c.file_id == File.id)
                    .where(sample_files.c.sample_id == s.id, File.library_id.is_(None))
                )
            )
            .scalars()
            .all()
        )
        candidates.append(s)
        files_by_sample[s.id] = linked_files
        preview.libraries_to_create += 1
        preview.files_to_attach += len(linked_files)
        preview.entries.append(
            BackfillEntry(
                sample_id=s.id,
                prep_kit=s.library_prep_method,
                read_layout=s.library_layout,
                file_ids=[f.id for f in linked_files],
            )
        )

    return preview, candidates, files_by_sample


class LibraryBackfillService:
    @staticmethod
    async def preview(session: AsyncSession, org_id: int, experiment_id: int) -> BackfillPreview:
        preview, _, _ = await _plan(session, org_id, experiment_id)
        return preview

    @staticmethod
    async def commit(
        session: AsyncSession,
        org_id: int,
        experiment_id: int,
        user_id: int | None = None,
    ) -> BackfillResult:
        preview, candidates, files_by_sample = await _plan(session, org_id, experiment_id)
        result = BackfillResult(
            experiment_id=experiment_id,
            samples_skipped=preview.samples_skipped,
        )

        for s in candidates:
            lib = Library(
                organization_id=org_id,
                sample_id=s.id,
                prep_kit=s.library_prep_method,
                read_layout=s.library_layout,
                status="planned",
            )
            session.add(lib)
            await session.flush()
            result.libraries_created += 1

            for f in files_by_sample.get(s.id, []):
                f.library_id = lib.id
                result.files_attached += 1
            await session.flush()

            await log_action(
                session,
                user_id,
                "library",
                lib.id,
                "backfilled",
                details={"sample_id": s.id, "files_attached": len(files_by_sample.get(s.id, []))},
            )
            asyncio.create_task(
                event_bus.emit(
                    event_types.LIBRARY_BACKFILLED,
                    {
                        "event_type": event_types.LIBRARY_BACKFILLED,
                        "org_id": org_id,
                        "entity_type": "library",
                        "entity_id": lib.id,
                        "sample_id": s.id,
                    },
                )
            )

        return result
