"""Sample swap detection service.

Stores per-library attribute mismatches surfaced by post-ingest QC. The
pipeline step that produces these rows is out of scope; this service
owns the data-model and API surface.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sample_swap_check import SampleSwapCheck
from app.schemas.sample_swap_check import (
    SampleSwapCheckCreate,
    SampleSwapCheckResolve,
)
from app.services.library_service import LibraryService


class SampleSwapService:
    @staticmethod
    async def list_checks(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        unresolved_only: bool = False,
    ) -> list[SampleSwapCheck]:
        await LibraryService._get_library_in_org(session, org_id, library_id)
        stmt = select(SampleSwapCheck).where(
            SampleSwapCheck.organization_id == org_id,
            SampleSwapCheck.library_id == library_id,
        )
        if unresolved_only:
            stmt = stmt.where(SampleSwapCheck.resolved_at.is_(None))
        stmt = stmt.order_by(SampleSwapCheck.created_at.desc())
        return list((await session.execute(stmt)).scalars().all())

    @staticmethod
    async def create_check(
        session: AsyncSession,
        org_id: int,
        library_id: int,
        payload: SampleSwapCheckCreate,
    ) -> SampleSwapCheck:
        await LibraryService._get_library_in_org(session, org_id, library_id)
        row = SampleSwapCheck(
            organization_id=org_id,
            library_id=library_id,
            run_id=payload.run_id,
            expected_attribute=payload.expected_attribute,
            observed_attribute=payload.observed_attribute,
            status=payload.status,
            evidence_json=payload.evidence_json,
        )
        session.add(row)
        await session.flush()
        return row

    @staticmethod
    async def resolve_check(
        session: AsyncSession,
        org_id: int,
        check_id: int,
        payload: SampleSwapCheckResolve,
        user_id: int | None = None,
    ) -> SampleSwapCheck:
        row = await session.get(SampleSwapCheck, check_id)
        if row is None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Swap check not found")
        row.resolved_at = datetime.now(UTC)
        row.resolved_by_user_id = user_id
        row.resolution_notes = payload.resolution_notes
        await session.flush()
        return row
