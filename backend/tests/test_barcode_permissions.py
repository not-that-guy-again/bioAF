"""Tests for barcodes:* permission granularity (issue #244 §4.7) and
bulk-insert guardrail (§4.8)."""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _create_library(client, token) -> int:
    exp = await client.post(
        "/api/experiments",
        json={"name": "Perm Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    exp_id = exp.json()["id"]
    smp = await client.post(
        f"/api/experiments/{exp_id}/samples",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    sid = smp.json()["id"]
    lib = await client.post(
        "/api/libraries",
        json={"sample_id": sid},
        headers={"Authorization": f"Bearer {token}"},
    )
    return lib.json()["id"]


async def test_bench_user_can_view_and_create_barcodes(
    client, admin_token, session
):
    from app.models.user import User
    from app.services.auth_service import AuthService

    admin = (await session.execute(select(User).limit(1))).scalar_one()
    role_map = {
        r.name: r.id
        for r in (
            await session.execute(
                select(__import__("app.models", fromlist=["Role"]).Role).where(
                    __import__("app.models", fromlist=["Role"]).Role.organization_id
                    == admin.organization_id
                )
            )
        ).scalars()
    }
    password_hash = AuthService.hash_password("benchpass123")
    bench = User(
        email="bench@test.com",
        password_hash=password_hash,
        role_id=role_map["bench"],
        organization_id=admin.organization_id,
        status="active",
    )
    session.add(bench)
    await session.flush()
    await session.commit()
    bench_token = AuthService.create_token(
        bench.id, bench.email, bench.role_id, bench.organization_id, role_name="bench"
    )

    lib_id = await _create_library(client, admin_token)

    # Bench can read barcodes.
    r = await client.get(
        f"/api/libraries/{lib_id}/barcodes",
        headers={"Authorization": f"Bearer {bench_token}"},
    )
    assert r.status_code == 200

    # Bench can create a library_index-style barcode.
    r = await client.post(
        f"/api/libraries/{lib_id}/barcodes",
        json={
            "barcode_type": "other",
            "sequence": "ACGTACGT",
            "read_position": "R1",
        },
        headers={"Authorization": f"Bearer {bench_token}"},
    )
    assert r.status_code == 200, r.text


async def test_viewer_cannot_create_barcode(client, admin_token, viewer_token):
    lib_id = await _create_library(client, admin_token)
    r = await client.post(
        f"/api/libraries/{lib_id}/barcodes",
        json={
            "barcode_type": "other",
            "sequence": "ACGT",
            "read_position": "R1",
        },
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403


async def test_viewer_can_list_barcodes(client, admin_token, viewer_token):
    lib_id = await _create_library(client, admin_token)
    r = await client.get(
        f"/api/libraries/{lib_id}/barcodes",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 200


async def test_library_index_barcodes_auto_created_without_barcode_permission(
    session,
):
    """Service layer creates library_index rows from Library fields; no barcodes
    permission is required because the call bypasses the API layer entirely."""
    from app.models.barcode_map import BarcodeMap
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org = Organization(name="No Barcode Perm", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Auto", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()

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

    rows = (
        (
            await session.execute(
                select(BarcodeMap).where(
                    BarcodeMap.library_id == lib.id,
                    BarcodeMap.barcode_type == "library_index",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2


async def test_bulk_guardrail_rejects_above_limit(session):
    """§4.8: bulk create rejects once the library would exceed the cap."""
    from fastapi import HTTPException

    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.barcode_map import BarcodeMapBulkCreate, BarcodeMapCreate
    from app.schemas.library import LibraryCreate
    from app.services.barcode_service import (
        MAX_BARCODES_PER_LIBRARY,
        BarcodeService,
    )
    from app.services.library_service import LibraryService

    org = Organization(name="Guardrail", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="GR", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = await LibraryService.create_library(
        session, org.id, LibraryCreate(sample_id=sample.id)
    )
    await session.commit()

    # Build a payload just over the cap. Use distinct sequences per entry so the
    # uniqueness constraint doesn't fire first.
    def _seq(i: int) -> str:
        letters = "ACGT"
        s = ""
        n = i
        for _ in range(8):
            s = letters[n % 4] + s
            n //= 4
        return s

    entries = [
        BarcodeMapCreate(
            barcode_type="sgrna",
            sequence=_seq(i),
            name=f"g{i}",
            read_position="R1",
        )
        for i in range(MAX_BARCODES_PER_LIBRARY + 1)
    ]
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.bulk_create_barcode_maps(
            session, org.id, lib.id, BarcodeMapBulkCreate(entries=entries)
        )
    assert exc.value.status_code == 422
    assert "whitelist_reference" in exc.value.detail
