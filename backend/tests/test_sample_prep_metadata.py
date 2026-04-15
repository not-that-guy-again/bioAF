"""Tests for SampleService.get_prep_metadata (issue #244 §3.3)."""

import logging

import pytest

pytestmark = pytest.mark.asyncio


async def _setup(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization

    org = Organization(name="Prep Meta Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Prep Meta Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    return org, exp


async def test_prep_metadata_falls_back_to_sample_columns_when_no_library(session):
    from app.models.sample import Sample
    from app.services.sample_service import SampleService

    org, exp = await _setup(session)
    s = Sample(
        experiment_id=exp.id,
        library_prep_method="TruSeq",
        library_layout="paired",
    )
    session.add(s)
    await session.flush()
    await session.commit()

    meta = await SampleService.get_prep_metadata(session, org.id, s.id)
    assert meta["source"] == "sample"
    assert meta["prep_kit"] == "TruSeq"
    assert meta["read_layout"] == "paired"


async def test_prep_metadata_returns_library_when_present(session):
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService
    from app.services.sample_service import SampleService

    org, exp = await _setup(session)
    s = Sample(
        experiment_id=exp.id,
        library_prep_method="legacy-TruSeq",
        library_layout="single",
    )
    session.add(s)
    await session.flush()
    await session.commit()

    await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=s.id,
            prep_kit="TruSeq-v2",
            read_layout="paired",
        ),
    )
    await session.commit()

    meta = await SampleService.get_prep_metadata(session, org.id, s.id)
    assert meta["source"] == "library"
    assert meta["prep_kit"] == "TruSeq-v2"
    assert meta["read_layout"] == "paired"


async def test_prep_metadata_missing_sample_raises(session):
    from fastapi import HTTPException

    from app.services.sample_service import SampleService

    org, _ = await _setup(session)
    with pytest.raises(HTTPException) as exc:
        await SampleService.get_prep_metadata(session, org.id, 999_999)
    assert exc.value.status_code == 404


async def test_writing_sample_prep_columns_emits_deprecation_warning(
    session, caplog
):
    from app.models.sample import Sample
    from app.schemas.sample import SampleUpdate
    from app.services.sample_service import SampleService

    _, exp = await _setup(session)
    s = Sample(experiment_id=exp.id)
    session.add(s)
    await session.flush()
    await session.commit()

    with caplog.at_level(logging.WARNING, logger="bioaf.sample_deprecation"):
        await SampleService.update_sample(
            session,
            s.id,
            user_id=None,
            data=SampleUpdate(library_prep_method="NewKit"),
        )
    await session.commit()

    deprecation = [
        r
        for r in caplog.records
        if r.name == "bioaf.sample_deprecation"
        and "library_prep_method" in r.getMessage()
    ]
    assert deprecation, "expected a deprecation warning log for Sample.library_prep_method"


async def test_writing_non_deprecated_field_does_not_emit_warning(
    session, caplog
):
    from app.models.sample import Sample
    from app.schemas.sample import SampleUpdate
    from app.services.sample_service import SampleService

    _, exp = await _setup(session)
    s = Sample(experiment_id=exp.id)
    session.add(s)
    await session.flush()
    await session.commit()

    with caplog.at_level(logging.WARNING, logger="bioaf.sample_deprecation"):
        await SampleService.update_sample(
            session,
            s.id,
            user_id=None,
            data=SampleUpdate(organism="Homo sapiens"),
        )
    await session.commit()

    deprecation = [
        r for r in caplog.records if r.name == "bioaf.sample_deprecation"
    ]
    assert deprecation == []
