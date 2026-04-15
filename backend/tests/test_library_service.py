"""Tests for LibraryService (issue #233 §6)."""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _setup(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample

    org = Organization(name="Svc Test Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Svc Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    await session.commit()
    return org, exp, sample


async def test_create_library_populates_library_index_barcodes(session):
    """Per §8: dual-index library auto-creates two library_index BarcodeMap rows."""
    from app.models import BarcodeMap
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, _, sample = await _setup(session)
    payload = LibraryCreate(
        sample_id=sample.id,
        index_type="dual",
        i5_sequence="aagtccgt",
        i7_sequence="gcatacga",
    )
    lib = await LibraryService.create_library(session, org.id, payload)
    await session.commit()

    # Sequences canonicalised to uppercase.
    assert lib.i5_sequence == "AAGTCCGT"
    assert lib.i7_sequence == "GCATACGA"

    rows = (
        await session.execute(
            select(BarcodeMap).where(
                BarcodeMap.library_id == lib.id,
                BarcodeMap.barcode_type == "library_index",
            )
        )
    ).scalars().all()
    by_position = {r.read_position: r.sequence for r in rows}
    assert by_position == {"I1": "GCATACGA", "I2": "AAGTCCGT"}


async def test_create_library_single_index_only_i7(session):
    from app.models import BarcodeMap
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, _, sample = await _setup(session)
    payload = LibraryCreate(
        sample_id=sample.id,
        index_type="single",
        i7_sequence="GCATACGA",
    )
    lib = await LibraryService.create_library(session, org.id, payload)
    await session.commit()

    rows = (
        await session.execute(
            select(BarcodeMap).where(BarcodeMap.library_id == lib.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].read_position == "I1"
    assert rows[0].sequence == "GCATACGA"


async def test_create_library_rejects_invalid_sequence(session):
    from fastapi import HTTPException

    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, _, sample = await _setup(session)
    payload = LibraryCreate(
        sample_id=sample.id,
        index_type="single",
        i7_sequence="GCATxxACGA",
    )
    with pytest.raises(HTTPException) as exc:
        await LibraryService.create_library(session, org.id, payload)
    assert exc.value.status_code == 422


async def test_update_library_rebuilds_library_index_rows(session):
    """Per §8: updating index sequences rebuilds library_index rows idempotently."""
    from app.models import BarcodeMap
    from app.schemas.library import LibraryCreate, LibraryUpdate
    from app.services.library_service import LibraryService

    org, _, sample = await _setup(session)
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, index_type="single", i7_sequence="AAAA"),
    )
    await session.commit()

    await LibraryService.update_library(
        session,
        org.id,
        lib.id,
        LibraryUpdate(index_type="dual", i5_sequence="TTTT", i7_sequence="CCCC"),
    )
    await session.commit()

    rows = (
        await session.execute(
            select(BarcodeMap).where(
                BarcodeMap.library_id == lib.id,
                BarcodeMap.barcode_type == "library_index",
            )
        )
    ).scalars().all()
    by_position = {r.read_position: r.sequence for r in rows}
    assert by_position == {"I1": "CCCC", "I2": "TTTT"}


async def test_create_library_rejects_cross_org_sample(session):
    from fastapi import HTTPException

    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org_a, _, _ = await _setup(session)

    org_b = Organization(name="Other Org", setup_complete=True)
    session.add(org_b)
    await session.flush()
    exp_b = Experiment(name="Other Exp", organization_id=org_b.id)
    session.add(exp_b)
    await session.flush()
    sample_b = Sample(experiment_id=exp_b.id)
    session.add(sample_b)
    await session.flush()
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await LibraryService.create_library(
            session,
            org_a.id,
            LibraryCreate(sample_id=sample_b.id),
        )
    assert exc.value.status_code in (403, 404)


async def test_attach_file_sets_library_and_sample_link(session):
    """attach_file sets File.library_id and ensures sample_files link exists."""
    from app.models import File
    from app.models.sample import sample_files
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org, _, sample = await _setup(session)
    lib = await LibraryService.create_library(
        session, org.id, LibraryCreate(sample_id=sample.id)
    )
    f = File(
        organization_id=org.id,
        gcs_uri="gs://x/a.fq.gz",
        filename="a.fq.gz",
        file_type="fastq",
    )
    session.add(f)
    await session.flush()
    await session.commit()

    await LibraryService.attach_file(session, org.id, lib.id, f.id)
    await session.commit()

    updated = await session.get(File, f.id)
    assert updated.library_id == lib.id

    links = (
        await session.execute(
            select(sample_files).where(
                sample_files.c.file_id == f.id,
                sample_files.c.sample_id == sample.id,
            )
        )
    ).all()
    assert len(links) == 1
