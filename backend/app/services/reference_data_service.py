"""Reference data service — CRUD, governance, and impact assessment for reference datasets."""

import asyncio
import logging

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.experiment import Experiment
from app.models.pipeline_run import PipelineRun
from app.models.pipeline_run_review import PipelineRunReview
from app.models.reference_dataset import (
    ReferenceDataset,
    ReferenceDatasetFile,
    pipeline_run_references,
)
from app.schemas.reference_dataset import (
    ImpactPipelineRun,
    ImpactSummary,
    ReferenceDatasetCreate,
    ReferenceDeprecateRequest,
)
from app.services.audit_service import log_action
from app.services.event_bus import event_bus
from app.services.event_types import REFERENCE_DEPRECATED

logger = logging.getLogger("bioaf.reference_data")


class ReferenceDataService:
    """Static methods for reference dataset management."""

    @staticmethod
    async def list_references(
        session: AsyncSession,
        org_id: int,
        *,
        category: str | None = None,
        scope: str | None = None,
        status: str | None = None,
        name_search: str | None = None,
    ) -> tuple[list[ReferenceDataset], int]:
        """List reference datasets with optional filters."""
        query: Select = (
            select(ReferenceDataset)
            .where(ReferenceDataset.organization_id == org_id)
            .order_by(ReferenceDataset.created_at.desc())
        )
        count_query = (
            select(func.count()).select_from(ReferenceDataset).where(ReferenceDataset.organization_id == org_id)
        )

        if category:
            query = query.where(ReferenceDataset.category == category)
            count_query = count_query.where(ReferenceDataset.category == category)
        if scope:
            query = query.where(ReferenceDataset.scope == scope)
            count_query = count_query.where(ReferenceDataset.scope == scope)
        if status:
            query = query.where(ReferenceDataset.status == status)
            count_query = count_query.where(ReferenceDataset.status == status)
        if name_search:
            query = query.where(ReferenceDataset.name.ilike(f"%{name_search}%"))
            count_query = count_query.where(ReferenceDataset.name.ilike(f"%{name_search}%"))

        total = (await session.execute(count_query)).scalar() or 0
        result = await session.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def get_reference(
        session: AsyncSession,
        reference_id: int,
        org_id: int,
    ) -> ReferenceDataset | None:
        """Get reference dataset detail with files and user relationships."""
        result = await session.execute(
            select(ReferenceDataset)
            .options(
                selectinload(ReferenceDataset.files),
                selectinload(ReferenceDataset.uploaded_by),
                selectinload(ReferenceDataset.approved_by),
            )
            .where(
                ReferenceDataset.id == reference_id,
                ReferenceDataset.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_reference(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        data: ReferenceDatasetCreate,
    ) -> ReferenceDataset:
        """Create a reference dataset with files in one transaction."""
        dataset = ReferenceDataset(
            organization_id=org_id,
            name=data.name,
            category=data.category,
            scope=data.scope,
            version=data.version,
            source_url=data.source_url,
            gcs_prefix=data.gcs_prefix,
            total_size_bytes=data.total_size_bytes,
            file_count=len(data.files),
            md5_manifest_json=data.md5_manifest_json,
            uploaded_by_user_id=user_id,
            status="active",
        )
        session.add(dataset)
        await session.flush()

        for f in data.files:
            file_record = ReferenceDatasetFile(
                reference_dataset_id=dataset.id,
                filename=f.filename,
                gcs_uri=f.gcs_uri,
                size_bytes=f.size_bytes,
                md5_checksum=f.md5_checksum,
                file_type=f.file_type,
            )
            session.add(file_record)

        await log_action(
            session,
            user_id=user_id,
            entity_type="reference_dataset",
            entity_id=dataset.id,
            action="created",
            details={
                "name": data.name,
                "version": data.version,
                "category": data.category,
                "scope": data.scope,
                "file_count": len(data.files),
            },
        )

        return dataset

    @staticmethod
    async def deprecate_reference(
        session: AsyncSession,
        reference_id: int,
        org_id: int,
        user_id: int,
        request: ReferenceDeprecateRequest,
    ) -> ReferenceDataset:
        """Deprecate a reference dataset. Public scope requires admin approval."""
        dataset = await ReferenceDataService.get_reference(session, reference_id, org_id)
        if not dataset:
            raise ValueError("Reference dataset not found")
        if dataset.status != "active":
            raise ValueError(f"Cannot deprecate a dataset with status '{dataset.status}'")

        if request.superseded_by_id:
            successor = await ReferenceDataService.get_reference(session, request.superseded_by_id, org_id)
            if not successor:
                raise ValueError("Superseding reference dataset not found")

        previous = {"status": dataset.status}

        if dataset.scope == "internal":
            # Internal: immediate deprecation
            dataset.status = "deprecated"
            dataset.deprecation_note = request.deprecation_note
            dataset.superseded_by_id = request.superseded_by_id
            await session.flush()

            await log_action(
                session,
                user_id=user_id,
                entity_type="reference_dataset",
                entity_id=dataset.id,
                action="deprecated",
                details={
                    "deprecation_note": request.deprecation_note,
                    "superseded_by_id": request.superseded_by_id,
                },
                previous_value=previous,
            )

            # Fire-and-forget notification
            asyncio.create_task(
                event_bus.emit(
                    REFERENCE_DEPRECATED,
                    {
                        "event_type": REFERENCE_DEPRECATED,
                        "org_id": org_id,
                        "user_id": user_id,
                        "entity_type": "reference_dataset",
                        "entity_id": dataset.id,
                        "title": f"Reference deprecated: {dataset.name} {dataset.version}",
                        "message": request.deprecation_note,
                        "metadata": {
                            "reference_id": dataset.id,
                            "name": dataset.name,
                            "version": dataset.version,
                            "scope": dataset.scope,
                        },
                    },
                )
            )
        else:
            # Public: requires admin approval
            dataset.status = "pending_approval"
            dataset.deprecation_note = request.deprecation_note
            dataset.superseded_by_id = request.superseded_by_id
            await session.flush()

            await log_action(
                session,
                user_id=user_id,
                entity_type="reference_dataset",
                entity_id=dataset.id,
                action="deprecation_requested",
                details={
                    "deprecation_note": request.deprecation_note,
                    "superseded_by_id": request.superseded_by_id,
                },
                previous_value=previous,
            )

        return dataset

    @staticmethod
    async def approve_deprecation(
        session: AsyncSession,
        reference_id: int,
        org_id: int,
        user_id: int,
    ) -> ReferenceDataset:
        """Admin approves a pending public deprecation."""
        dataset = await ReferenceDataService.get_reference(session, reference_id, org_id)
        if not dataset:
            raise ValueError("Reference dataset not found")
        if dataset.status != "pending_approval":
            raise ValueError(f"Cannot approve deprecation: status is '{dataset.status}', expected 'pending_approval'")

        previous = {"status": dataset.status}
        dataset.status = "deprecated"
        dataset.approved_by_user_id = user_id
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="reference_dataset",
            entity_id=dataset.id,
            action="deprecation_approved",
            details={"approved_by_user_id": user_id},
            previous_value=previous,
        )

        asyncio.create_task(
            event_bus.emit(
                REFERENCE_DEPRECATED,
                {
                    "event_type": REFERENCE_DEPRECATED,
                    "org_id": org_id,
                    "user_id": user_id,
                    "entity_type": "reference_dataset",
                    "entity_id": dataset.id,
                    "title": f"Reference deprecation approved: {dataset.name} {dataset.version}",
                    "message": dataset.deprecation_note or "",
                    "metadata": {
                        "reference_id": dataset.id,
                        "name": dataset.name,
                        "version": dataset.version,
                        "scope": dataset.scope,
                    },
                },
            )
        )

        return dataset

    @staticmethod
    async def get_impact(
        session: AsyncSession,
        reference_id: int,
        org_id: int,
    ) -> ImpactSummary:
        """Compute impact assessment: which pipeline runs and experiments used this reference.

        Single query with JOINs — no N+1.
        """
        # Verify reference exists
        ref_exists = await session.execute(
            select(ReferenceDataset.id).where(
                ReferenceDataset.id == reference_id,
                ReferenceDataset.organization_id == org_id,
            )
        )
        if not ref_exists.scalar_one_or_none():
            raise ValueError("Reference dataset not found")

        # Single query joining pipeline_run_references -> pipeline_runs -> experiments + reviews
        active_review_subq = (
            select(
                PipelineRunReview.pipeline_run_id,
                PipelineRunReview.verdict,
            )
            .where(PipelineRunReview.superseded_by_id.is_(None))
            .distinct(PipelineRunReview.pipeline_run_id)
            .subquery()
        )

        query = (
            select(
                PipelineRun.id.label("pipeline_run_id"),
                PipelineRun.pipeline_name,
                PipelineRun.pipeline_version,
                PipelineRun.experiment_id,
                Experiment.name.label("experiment_name"),
                PipelineRun.status,
                active_review_subq.c.verdict.label("review_verdict"),
                PipelineRun.completed_at,
            )
            .select_from(pipeline_run_references)
            .join(PipelineRun, PipelineRun.id == pipeline_run_references.c.pipeline_run_id)
            .outerjoin(Experiment, Experiment.id == PipelineRun.experiment_id)
            .outerjoin(
                active_review_subq,
                active_review_subq.c.pipeline_run_id == PipelineRun.id,
            )
            .where(pipeline_run_references.c.reference_dataset_id == reference_id)
            .order_by(PipelineRun.created_at.desc())
        )

        result = await session.execute(query)
        rows = result.all()

        runs = []
        experiment_ids: set[int] = set()
        for row in rows:
            runs.append(
                ImpactPipelineRun(
                    pipeline_run_id=row.pipeline_run_id,
                    pipeline_name=row.pipeline_name,
                    pipeline_version=row.pipeline_version,
                    experiment_id=row.experiment_id,
                    experiment_name=row.experiment_name,
                    status=row.status,
                    review_verdict=row.review_verdict,
                    completed_at=row.completed_at,
                )
            )
            if row.experiment_id:
                experiment_ids.add(row.experiment_id)

        return ImpactSummary(
            reference_dataset_id=reference_id,
            total_pipeline_runs=len(runs),
            total_experiments=len(experiment_ids),
            pipeline_runs=runs,
        )

    @staticmethod
    async def get_pipeline_run_references(
        session: AsyncSession,
        pipeline_run_id: int,
    ) -> list[ReferenceDataset]:
        """Return reference datasets used by a specific pipeline run."""
        result = await session.execute(
            select(ReferenceDataset)
            .join(
                pipeline_run_references,
                pipeline_run_references.c.reference_dataset_id == ReferenceDataset.id,
            )
            .where(pipeline_run_references.c.pipeline_run_id == pipeline_run_id)
            .order_by(ReferenceDataset.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def link_pipeline_run_to_references(
        session: AsyncSession,
        pipeline_run_id: int,
        reference_ids: list[int],
    ) -> None:
        """Create linkage records between a pipeline run and reference datasets."""
        for ref_id in reference_ids:
            await session.execute(
                pipeline_run_references.insert().values(
                    pipeline_run_id=pipeline_run_id,
                    reference_dataset_id=ref_id,
                )
            )
