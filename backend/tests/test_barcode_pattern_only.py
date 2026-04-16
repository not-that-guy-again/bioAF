"""Tests for BarcodeMap.is_pattern_only validation (issue #244 §4.5)."""

import pytest

pytestmark = pytest.mark.asyncio


async def _make_library(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org = Organization(name="Pattern Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Pattern Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = await LibraryService.create_library(
        session, org.id, LibraryCreate(sample_id=sample.id)
    )
    await session.commit()
    return org, lib


async def test_pattern_only_umi_row_passes(session):
    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, lib = await _make_library(session)
    bm = await BarcodeService.create_barcode_map(
        session,
        org.id,
        lib.id,
        BarcodeMapCreate(
            barcode_type="umi",
            is_pattern_only=True,
            read_position="R1",
            offset_in_read=16,
            length=12,
        ),
    )
    await session.commit()
    assert bm.is_pattern_only is True
    assert bm.sequence is None


async def test_pattern_only_row_with_sequence_fails(session):
    from fastapi import HTTPException

    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, lib = await _make_library(session)
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.create_barcode_map(
            session,
            org.id,
            lib.id,
            BarcodeMapCreate(
                barcode_type="umi",
                is_pattern_only=True,
                sequence="AAAA",
                read_position="R1",
                offset_in_read=16,
                length=12,
            ),
        )
    assert exc.value.status_code == 422


async def test_pattern_only_missing_position_fails(session):
    from fastapi import HTTPException

    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, lib = await _make_library(session)
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.create_barcode_map(
            session,
            org.id,
            lib.id,
            BarcodeMapCreate(
                barcode_type="umi",
                is_pattern_only=True,
                offset_in_read=16,
                length=12,
            ),
        )
    assert exc.value.status_code == 422


async def test_explicit_row_without_sequence_fails(session):
    from fastapi import HTTPException

    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, lib = await _make_library(session)
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.create_barcode_map(
            session,
            org.id,
            lib.id,
            BarcodeMapCreate(
                barcode_type="cell_barcode",
                is_pattern_only=False,
                read_position="R1",
            ),
        )
    assert exc.value.status_code == 422


async def test_explicit_row_with_sequence_passes(session):
    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, lib = await _make_library(session)
    bm = await BarcodeService.create_barcode_map(
        session,
        org.id,
        lib.id,
        BarcodeMapCreate(
            barcode_type="cell_barcode",
            is_pattern_only=False,
            sequence="AAAAAAAAAAAAAAAA",
            read_position="R1",
            length=16,
        ),
    )
    await session.commit()
    assert bm.is_pattern_only is False
    assert bm.sequence == "AAAAAAAAAAAAAAAA"


async def test_whitelist_reference_bypasses_sequence_requirement(session):
    """is_pattern_only=False + whitelist_reference is still a valid config."""
    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, lib = await _make_library(session)
    bm = await BarcodeService.create_barcode_map(
        session,
        org.id,
        lib.id,
        BarcodeMapCreate(
            barcode_type="cell_barcode",
            is_pattern_only=False,
            whitelist_reference="10x:737K-august-2016",
            read_position="R1",
        ),
    )
    await session.commit()
    assert bm.sequence is None
    assert bm.whitelist_reference == "10x:737K-august-2016"
