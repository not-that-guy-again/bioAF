"""Tests for Library.expected_contamination_pct (issue #244 §4.2)."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.asyncio


async def _bootstrap(session, instrument_model: str | None = None):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.models.sequencing_batch import SequencingBatch

    org = Organization(name="Hop Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Hop Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    batch = None
    if instrument_model is not None:
        batch = SequencingBatch(
            organization_id=org.id,
            code="HP-BATCH",
            status="pending",
            instrument_model=instrument_model,
        )
        session.add(batch)
        await session.flush()
    await session.commit()
    return org, sample, batch


async def test_novaseq_default_contamination(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NovaSeq 6000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, sequencing_batch_id=batch.id),
    )
    await session.commit()
    assert lib.expected_contamination_pct == Decimal("0.500")


async def test_nextseq_2000_default_contamination(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NextSeq 2000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, sequencing_batch_id=batch.id),
    )
    await session.commit()
    assert lib.expected_contamination_pct == Decimal("1.000")


async def test_miseq_default_contamination(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "MiSeq")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, sequencing_batch_id=batch.id),
    )
    await session.commit()
    assert lib.expected_contamination_pct == Decimal("0.050")


async def test_user_supplied_contamination_wins(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NovaSeq 6000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            sequencing_batch_id=batch.id,
            expected_contamination_pct=Decimal("2.500"),
        ),
    )
    await session.commit()
    assert lib.expected_contamination_pct == Decimal("2.500")


async def test_no_batch_no_contamination_inference(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, _ = await _bootstrap(session, instrument_model=None)
    lib = await LibraryService.create_library(
        session, org.id, LibraryCreate(sample_id=sample.id)
    )
    await session.commit()
    assert lib.expected_contamination_pct is None


async def test_unknown_instrument_no_contamination_inference(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "Unknown-X")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, sequencing_batch_id=batch.id),
    )
    await session.commit()
    assert lib.expected_contamination_pct is None


async def test_contamination_pct_in_library_response(session):
    from app.schemas.library import LibraryCreate, LibraryResponse
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NovaSeq 6000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, sequencing_batch_id=batch.id),
    )
    await session.commit()
    out = LibraryResponse.model_validate(lib)
    assert out.expected_contamination_pct == Decimal("0.500")
