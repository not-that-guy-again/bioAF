"""Tests for Sample.libraries and File.library relationships (issue #233 §3.3, §3.4)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

pytestmark = pytest.mark.asyncio


async def _setup(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample

    org = Organization(name="Rel Test Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Rel Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    return org, sample


async def test_sample_has_libraries_relationship(session):
    from app.models import Library, Sample

    org, sample = await _setup(session)
    session.add(Library(organization_id=org.id, sample_id=sample.id, library_id_external="A"))
    session.add(Library(organization_id=org.id, sample_id=sample.id, library_id_external="B"))
    await session.flush()

    fetched = (
        await session.execute(select(Sample).options(selectinload(Sample.libraries)).where(Sample.id == sample.id))
    ).scalar_one()
    external_ids = sorted(lib.library_id_external for lib in fetched.libraries)
    assert external_ids == ["A", "B"]


async def test_file_library_id_nullable_and_relationship(session):
    from app.models import File, Library

    org, sample = await _setup(session)
    lib = Library(organization_id=org.id, sample_id=sample.id, library_id_external="L1")
    session.add(lib)
    await session.flush()

    f_linked = File(
        organization_id=org.id,
        gcs_uri="gs://test/a.fastq.gz",
        filename="a.fastq.gz",
        file_type="fastq",
        library_id=lib.id,
    )
    f_unlinked = File(
        organization_id=org.id,
        gcs_uri="gs://test/b.fastq.gz",
        filename="b.fastq.gz",
        file_type="fastq",
    )
    session.add_all([f_linked, f_unlinked])
    await session.flush()

    fetched_linked = (
        await session.execute(select(File).options(selectinload(File.library)).where(File.id == f_linked.id))
    ).scalar_one()
    fetched_unlinked = (await session.execute(select(File).where(File.id == f_unlinked.id))).scalar_one()

    assert fetched_linked.library_id == lib.id
    assert fetched_linked.library.id == lib.id
    assert fetched_unlinked.library_id is None


async def test_library_files_backref(session):
    from app.models import File, Library

    org, sample = await _setup(session)
    lib = Library(organization_id=org.id, sample_id=sample.id, library_id_external="L2")
    session.add(lib)
    await session.flush()

    session.add(
        File(
            organization_id=org.id,
            gcs_uri="gs://test/c.fastq.gz",
            filename="c.fastq.gz",
            file_type="fastq",
            library_id=lib.id,
        )
    )
    await session.flush()

    fetched = (
        await session.execute(select(Library).options(selectinload(Library.files)).where(Library.id == lib.id))
    ).scalar_one()
    assert len(fetched.files) == 1
    assert fetched.files[0].filename == "c.fastq.gz"


async def test_sample_deletion_cascades_to_libraries_but_not_files(session):
    """Per §8: Sample -> Libraries cascades; Files outlive their libraries."""
    from app.models import File, Library, Sample

    org, sample = await _setup(session)
    lib = Library(organization_id=org.id, sample_id=sample.id, library_id_external="LX")
    session.add(lib)
    await session.flush()
    f = File(
        organization_id=org.id,
        gcs_uri="gs://test/d.fastq.gz",
        filename="d.fastq.gz",
        file_type="fastq",
        library_id=lib.id,
    )
    session.add(f)
    await session.flush()
    file_id = f.id
    lib_id = lib.id

    await session.delete(await session.get(Sample, sample.id))
    await session.flush()

    assert await session.get(Library, lib_id) is None
    surviving_file = await session.get(File, file_id)
    assert surviving_file is not None
