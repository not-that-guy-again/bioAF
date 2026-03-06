from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch
from app.models.sample import Sample
from app.schemas.batch import BatchCreate, BatchUpdate
from app.services.audit_service import log_action
from app.services.vocabulary_validator import VocabularyValidator, _derive_instrument_platform


class BatchService:
    @staticmethod
    async def create_batch(session: AsyncSession, experiment_id: int, user_id: int, data: BatchCreate) -> Batch:
        # Validate controlled vocabulary fields
        await VocabularyValidator.validate_batch_fields(
            session,
            {
                "instrument_model": data.instrument_model,
                "instrument_platform": data.instrument_platform,
                "quality_score_encoding": data.quality_score_encoding,
            },
        )

        # Auto-derive instrument_platform from instrument_model
        instrument_platform = data.instrument_platform
        if data.instrument_model and not instrument_platform:
            instrument_platform = _derive_instrument_platform(data.instrument_model)

        batch = Batch(
            experiment_id=experiment_id,
            name=data.name,
            prep_date=data.prep_date,
            operator_user_id=data.operator_user_id,
            sequencer_run_id=data.sequencer_run_id,
            instrument_model=data.instrument_model,
            instrument_platform=instrument_platform,
            quality_score_encoding=data.quality_score_encoding,
            notes=data.notes,
        )
        session.add(batch)
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="batch",
            entity_id=batch.id,
            action="create",
            details={"experiment_id": experiment_id, "name": data.name},
        )
        return batch

    @staticmethod
    async def update_batch(session: AsyncSession, batch_id: int, user_id: int, data: BatchUpdate) -> Batch | None:
        result = await session.execute(select(Batch).where(Batch.id == batch_id))
        batch = result.scalar_one_or_none()
        if not batch:
            return None

        # Validate controlled vocabulary fields
        await VocabularyValidator.validate_batch_fields(
            session,
            {
                "instrument_model": data.instrument_model,
                "instrument_platform": data.instrument_platform,
                "quality_score_encoding": data.quality_score_encoding,
            },
        )

        # Auto-derive instrument_platform from instrument_model
        if data.instrument_model and not data.instrument_platform:
            data.instrument_platform = _derive_instrument_platform(data.instrument_model)

        previous = {}
        updates = {}
        for field in [
            "name",
            "prep_date",
            "operator_user_id",
            "sequencer_run_id",
            "instrument_model",
            "instrument_platform",
            "quality_score_encoding",
            "notes",
        ]:
            new_val = getattr(data, field, None)
            if new_val is not None:
                old_val = getattr(batch, field)
                previous[field] = str(old_val) if old_val is not None else None
                setattr(batch, field, new_val)
                updates[field] = str(new_val) if new_val is not None else None

        if updates:
            await session.flush()
            await log_action(
                session,
                user_id=user_id,
                entity_type="batch",
                entity_id=batch.id,
                action="update",
                details=updates,
                previous_value=previous,
            )
        return batch

    @staticmethod
    async def list_batches(session: AsyncSession, experiment_id: int) -> list[Batch]:
        result = await session.execute(
            select(Batch)
            .options(selectinload(Batch.samples), selectinload(Batch.operator))
            .where(Batch.experiment_id == experiment_id)
            .order_by(Batch.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_batch(session: AsyncSession, batch_id: int) -> Batch | None:
        result = await session.execute(
            select(Batch).options(selectinload(Batch.samples), selectinload(Batch.operator)).where(Batch.id == batch_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def assign_samples_to_batch(
        session: AsyncSession, batch_id: int, sample_ids: list[int], user_id: int
    ) -> None:
        result = await session.execute(select(Batch).where(Batch.id == batch_id))
        batch = result.scalar_one_or_none()
        if not batch:
            return

        for sample_id in sample_ids:
            sample_result = await session.execute(select(Sample).where(Sample.id == sample_id))
            sample = sample_result.scalar_one_or_none()
            if sample and sample.experiment_id == batch.experiment_id:
                old_batch_id = sample.batch_id
                sample.batch_id = batch_id
                await session.flush()

                await log_action(
                    session,
                    user_id=user_id,
                    entity_type="sample",
                    entity_id=sample.id,
                    action="batch_assignment",
                    details={"batch_id": batch_id, "batch_name": batch.name},
                    previous_value={"batch_id": old_batch_id},
                )
