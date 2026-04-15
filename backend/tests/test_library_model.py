"""Tests for the Library model (issue #233)."""

from decimal import Decimal

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _create_org_and_experiment(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization

    org = Organization(name="Lib Test Org", setup_complete=True)
    session.add(org)
    await session.flush()

    exp = Experiment(name="Lib Test Experiment", organization_id=org.id)
    session.add(exp)
    await session.flush()
    return org, exp


async def _create_sample(session, experiment_id):
    from app.models.sample import Sample

    sample = Sample(experiment_id=experiment_id)
    session.add(sample)
    await session.flush()
    return sample


async def test_library_model_is_registered():
    """Library must be importable from app.models."""
    from app.models import Library

    assert Library.__tablename__ == "libraries"


async def test_create_library_with_required_fields(session):
    from app.models import Library

    org, exp = await _create_org_and_experiment(session)
    sample = await _create_sample(session, exp.id)

    lib = Library(organization_id=org.id, sample_id=sample.id)
    session.add(lib)
    await session.flush()

    assert lib.id is not None
    # Defaults per spec §3.1
    assert lib.status == "planned"
    assert lib.index_type == "none"


async def test_library_stores_prep_and_index_metadata(session):
    from app.models import Library

    org, exp = await _create_org_and_experiment(session)
    sample = await _create_sample(session, exp.id)

    lib = Library(
        organization_id=org.id,
        sample_id=sample.id,
        library_id_external="LIB-001",
        prep_kit="TruSeq RNA v2",
        assay_type="rna-seq",
        read_layout="paired",
        target_read_length=150,
        index_type="dual",
        i5_sequence="AAGTCCGT",
        i7_sequence="GCATACGA",
        i5_orientation_convention="reverse_complement",
        insert_size_mean=350,
        molarity_nm=Decimal("4.500"),
        qc_status="pass",
    )
    session.add(lib)
    await session.flush()

    fetched = (await session.execute(select(Library).where(Library.id == lib.id))).scalar_one()
    assert fetched.library_id_external == "LIB-001"
    assert fetched.prep_kit == "TruSeq RNA v2"
    assert fetched.i5_sequence == "AAGTCCGT"
    assert fetched.i7_sequence == "GCATACGA"
    assert fetched.i5_orientation_convention == "reverse_complement"
    assert fetched.index_type == "dual"


async def test_library_external_id_unique_per_org(session):
    """Per §3.1: UniqueConstraint on (organization_id, library_id_external)."""
    from sqlalchemy.exc import IntegrityError

    from app.models import Library

    org, exp = await _create_org_and_experiment(session)
    sample = await _create_sample(session, exp.id)

    session.add(Library(organization_id=org.id, sample_id=sample.id, library_id_external="DUP"))
    await session.flush()

    session.add(Library(organization_id=org.id, sample_id=sample.id, library_id_external="DUP"))
    with pytest.raises(IntegrityError):
        await session.flush()
