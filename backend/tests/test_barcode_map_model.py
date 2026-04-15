"""Tests for the BarcodeMap model (issue #233)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.asyncio


async def _create_library(session):
    from app.models.experiment import Experiment
    from app.models.library import Library
    from app.models.organization import Organization
    from app.models.sample import Sample

    org = Organization(name="BC Test Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="BC Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = Library(organization_id=org.id, sample_id=sample.id)
    session.add(lib)
    await session.flush()
    return org, lib


async def test_barcode_map_model_is_registered():
    from app.models import BarcodeMap

    assert BarcodeMap.__tablename__ == "barcode_maps"


async def test_create_barcode_map_with_sequence(session):
    from app.models import BarcodeMap

    org, lib = await _create_library(session)
    bm = BarcodeMap(
        organization_id=org.id,
        library_id=lib.id,
        barcode_type="library_index",
        sequence="AAGTCCGT",
        read_position="I1",
        length=8,
    )
    session.add(bm)
    await session.flush()

    assert bm.id is not None
    assert bm.allowed_mismatches == 1  # server default per §3.2


async def test_barcode_map_whitelist_reference_without_sequence(session):
    """A row may omit sequence and reference an external whitelist."""
    from app.models import BarcodeMap

    org, lib = await _create_library(session)
    bm = BarcodeMap(
        organization_id=org.id,
        library_id=lib.id,
        barcode_type="cell_barcode",
        whitelist_reference="10x:737K-august-2016",
        read_position="R1",
    )
    session.add(bm)
    await session.flush()

    fetched = (await session.execute(select(BarcodeMap).where(BarcodeMap.id == bm.id))).scalar_one()
    assert fetched.sequence is None
    assert fetched.whitelist_reference == "10x:737K-august-2016"


async def test_barcode_map_unique_per_library_type_seq_pos(session):
    from app.models import BarcodeMap

    org, lib = await _create_library(session)
    session.add(
        BarcodeMap(
            organization_id=org.id,
            library_id=lib.id,
            barcode_type="library_index",
            sequence="AAGTCCGT",
            read_position="I1",
        )
    )
    await session.flush()

    session.add(
        BarcodeMap(
            organization_id=org.id,
            library_id=lib.id,
            barcode_type="library_index",
            sequence="AAGTCCGT",
            read_position="I1",
        )
    )
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_library_cascades_to_barcode_maps(session):
    """Per §3.1 cascade='all, delete-orphan': deleting a Library removes its BarcodeMaps."""
    from app.models import BarcodeMap, Library

    org, lib = await _create_library(session)
    session.add(
        BarcodeMap(
            organization_id=org.id,
            library_id=lib.id,
            barcode_type="library_index",
            sequence="GGGG",
            read_position="I1",
        )
    )
    await session.flush()

    await session.delete(await session.get(Library, lib.id))
    await session.flush()

    remaining = (
        await session.execute(select(BarcodeMap).where(BarcodeMap.library_id == lib.id))
    ).scalars().all()
    assert remaining == []
