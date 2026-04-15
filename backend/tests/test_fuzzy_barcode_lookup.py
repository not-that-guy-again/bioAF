"""Tests for fuzzy (Hamming-distance) barcode lookup (issue #244 §4.1)."""

import pytest

pytestmark = pytest.mark.asyncio


async def _setup_lib(session, org_name="Fuzzy Org"):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org = Organization(name=org_name, setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Fuzzy Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, index_type="single", i7_sequence="AAAACCCC"),
    )
    await session.commit()
    return org, lib


async def test_fuzzy_lookup_hamming_zero(session):
    from app.services.barcode_service import BarcodeService

    org, lib = await _setup_lib(session)
    matches = await BarcodeService.fuzzy_lookup(
        session, org.id, "AAAACCCC", max_mismatches=1
    )
    assert any(m.sequence == "AAAACCCC" and d == 0 for m, d in matches)


async def test_fuzzy_lookup_hamming_one(session):
    from app.services.barcode_service import BarcodeService

    org, _ = await _setup_lib(session)
    # Query one base off: expect distance 1 match.
    matches = await BarcodeService.fuzzy_lookup(
        session, org.id, "AAAACCCG", max_mismatches=1
    )
    distances = [d for m, d in matches if m.sequence == "AAAACCCC"]
    assert 1 in distances


async def test_fuzzy_lookup_rejects_beyond_budget(session):
    from app.services.barcode_service import BarcodeService

    org, _ = await _setup_lib(session)
    # Two bases off with max=1 should return no match.
    matches = await BarcodeService.fuzzy_lookup(
        session, org.id, "AAAAGGGG", max_mismatches=1
    )
    assert [(m, d) for m, d in matches if m.sequence == "AAAACCCC"] == []


async def test_fuzzy_lookup_hamming_two(session):
    from app.services.barcode_service import BarcodeService

    org, _ = await _setup_lib(session)
    # Two bases off with max=2 returns distance 2 match.
    matches = await BarcodeService.fuzzy_lookup(
        session, org.id, "AAAACCGG", max_mismatches=2
    )
    distances = [d for m, d in matches if m.sequence == "AAAACCCC"]
    assert 2 in distances


async def test_fuzzy_lookup_is_org_scoped(session):
    from app.services.barcode_service import BarcodeService

    _, lib_a = await _setup_lib(session, org_name="Fuzzy A")
    org_b, lib_b = await _setup_lib(session, org_name="Fuzzy B")

    matches = await BarcodeService.fuzzy_lookup(
        session, org_b.id, "AAAACCCC", max_mismatches=1
    )
    for m, _d in matches:
        assert m.library_id == lib_b.id


async def test_fuzzy_lookup_rejects_invalid_sequence(session):
    from fastapi import HTTPException

    from app.services.barcode_service import BarcodeService

    org, _ = await _setup_lib(session)
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.fuzzy_lookup(session, org.id, "BAD!", max_mismatches=1)
    assert exc.value.status_code == 422


async def test_fuzzy_lookup_rejects_long_sequence_with_mismatches(session):
    from fastapi import HTTPException

    from app.services.barcode_service import BarcodeService

    org, _ = await _setup_lib(session)
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.fuzzy_lookup(
            session, org.id, "A" * 24, max_mismatches=1
        )
    assert exc.value.status_code == 422


async def test_fuzzy_lookup_long_sequence_exact_match_ok(session):
    """Length > 16 is permitted at max_mismatches=0 (degrades to exact match)."""
    from app.models.library import Library
    from app.models.barcode_map import BarcodeMap
    from app.services.barcode_service import BarcodeService

    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample

    org = Organization(name="Long Fuzzy", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="LF", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = Library(organization_id=org.id, sample_id=sample.id)
    session.add(lib)
    await session.flush()
    long_seq = "A" * 24
    session.add(
        BarcodeMap(
            organization_id=org.id,
            library_id=lib.id,
            barcode_type="cell_barcode",
            sequence=long_seq,
            read_position="R1",
        )
    )
    await session.commit()

    matches = await BarcodeService.fuzzy_lookup(session, org.id, long_seq, max_mismatches=0)
    assert any(m.sequence == long_seq and d == 0 for m, d in matches)


async def test_fuzzy_lookup_api_endpoint(client, admin_token, session):
    from sqlalchemy import select

    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()

    exp = await client.post(
        "/api/experiments",
        json={"name": "FZ API"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    exp_id = exp.json()["id"]
    smp = await client.post(
        f"/api/experiments/{exp_id}/samples",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sid = smp.json()["id"]
    await client.post(
        "/api/libraries",
        json={
            "sample_id": sid,
            "index_type": "single",
            "i7_sequence": "AAAACCCC",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    r = await client.get(
        "/api/barcodes/fuzzy-lookup?sequence=AAAACCCG&max_mismatches=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(entry["sequence"] == "AAAACCCC" and entry["distance"] == 1 for entry in body)
    # Ensure org_id is the admin's.
    for entry in body:
        assert entry["organization_id"] == admin.organization_id
