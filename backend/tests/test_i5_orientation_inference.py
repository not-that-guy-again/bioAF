"""Tests for i5 orientation inference (issue #244 §3.4)."""

import pytest

pytestmark = pytest.mark.asyncio


async def _bootstrap(session, instrument_model: str | None = None):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.models.sequencing_batch import SequencingBatch

    org = Organization(name="I5 Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="I5 Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    batch = None
    if instrument_model is not None:
        batch = SequencingBatch(
            organization_id=org.id,
            code="I5-BATCH",
            status="pending",
            instrument_model=instrument_model,
        )
        session.add(batch)
        await session.flush()
    await session.commit()
    return org, sample, batch


async def test_novaseq_batch_infers_reverse_complement(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NovaSeq 6000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            sequencing_batch_id=batch.id,
            index_type="dual",
            i5_sequence="AAAA",
            i7_sequence="TTTT",
        ),
    )
    await session.commit()
    assert lib.i5_orientation_convention == "reverse_complement"


async def test_miseq_batch_infers_forward(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "MiSeq")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            sequencing_batch_id=batch.id,
            index_type="dual",
            i5_sequence="AAAA",
            i7_sequence="TTTT",
        ),
    )
    await session.commit()
    assert lib.i5_orientation_convention == "forward"


async def test_user_supplied_value_is_never_overridden(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NovaSeq 6000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            sequencing_batch_id=batch.id,
            index_type="dual",
            i5_sequence="AAAA",
            i7_sequence="TTTT",
            i5_orientation_convention="forward",
        ),
    )
    await session.commit()
    assert lib.i5_orientation_convention == "forward"


async def test_no_batch_no_inference(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, _ = await _bootstrap(session, instrument_model=None)
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            index_type="dual",
            i5_sequence="AAAA",
            i7_sequence="TTTT",
        ),
    )
    await session.commit()
    assert lib.i5_orientation_convention is None


async def test_unknown_sequencer_leaves_null(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "MysteryMachine 3000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            sequencing_batch_id=batch.id,
            index_type="dual",
            i5_sequence="AAAA",
            i7_sequence="TTTT",
        ),
    )
    await session.commit()
    assert lib.i5_orientation_convention is None


async def test_nextseq_2000_infers_reverse_complement(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, sample, batch = await _bootstrap(session, "NextSeq 2000")
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=sample.id,
            sequencing_batch_id=batch.id,
            index_type="dual",
            i5_sequence="AAAA",
            i7_sequence="TTTT",
        ),
    )
    await session.commit()
    assert lib.i5_orientation_convention == "reverse_complement"
