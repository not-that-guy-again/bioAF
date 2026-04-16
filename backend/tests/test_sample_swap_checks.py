"""Tests for sample swap check model and API (issue #244 §4.6)."""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _setup_lib(session, org_name="Swap Org"):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    org = Organization(name=org_name, setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Swap Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = await LibraryService.create_library(session, org.id, LibraryCreate(sample_id=sample.id))
    await session.commit()
    return org, lib


async def test_swap_check_model_is_registered():
    from app.models import SampleSwapCheck

    assert SampleSwapCheck.__tablename__ == "sample_swap_checks"


async def test_swap_check_create_and_list_via_api(client, admin_token, session):
    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()
    exp = await client.post(
        "/api/experiments",
        json={"name": "Swap API"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    eid = exp.json()["id"]
    smp = await client.post(
        f"/api/experiments/{eid}/samples",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sid = smp.json()["id"]
    lib = await client.post(
        "/api/libraries",
        json={"sample_id": sid},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    lib_id = lib.json()["id"]

    r = await client.post(
        f"/api/libraries/{lib_id}/swap-checks",
        json={
            "expected_attribute": "species:Homo sapiens",
            "observed_attribute": "species:Mus musculus",
            "status": "mismatch",
            "evidence_json": {"method": "kraken2", "confidence": 0.98},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    check = r.json()
    assert check["status"] == "mismatch"
    assert check["library_id"] == lib_id
    assert check["organization_id"] == admin.organization_id
    assert check["resolved_at"] is None

    # List unresolved mismatches for the library.
    list_r = await client.get(
        f"/api/libraries/{lib_id}/swap-checks?unresolved_only=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_r.status_code == 200
    rows = list_r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == check["id"]


async def test_swap_check_list_returns_empty_when_none(client, admin_token):
    exp = await client.post(
        "/api/experiments",
        json={"name": "Swap Empty"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    eid = exp.json()["id"]
    smp = await client.post(
        f"/api/experiments/{eid}/samples",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sid = smp.json()["id"]
    lib = await client.post(
        "/api/libraries",
        json={"sample_id": sid},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    lib_id = lib.json()["id"]

    r = await client.get(
        f"/api/libraries/{lib_id}/swap-checks",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_swap_check_resolve(client, admin_token):
    exp = await client.post(
        "/api/experiments",
        json={"name": "Swap Resolve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    eid = exp.json()["id"]
    smp = await client.post(
        f"/api/experiments/{eid}/samples",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sid = smp.json()["id"]
    lib = await client.post(
        "/api/libraries",
        json={"sample_id": sid},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    lib_id = lib.json()["id"]

    create_r = await client.post(
        f"/api/libraries/{lib_id}/swap-checks",
        json={
            "expected_attribute": "sex:female",
            "observed_attribute": "sex:male",
            "status": "mismatch",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    check_id = create_r.json()["id"]

    resolve_r = await client.patch(
        f"/api/swap-checks/{check_id}/resolve",
        json={"resolution_notes": "investigated, was correct"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resolve_r.status_code == 200
    assert resolve_r.json()["resolved_at"] is not None

    list_r = await client.get(
        f"/api/libraries/{lib_id}/swap-checks?unresolved_only=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_r.json() == []

    # Without unresolved_only, the resolved row is visible.
    all_r = await client.get(
        f"/api/libraries/{lib_id}/swap-checks",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert len(all_r.json()) == 1


async def test_swap_check_is_org_scoped(session):
    from fastapi import HTTPException

    from app.services.sample_swap_service import SampleSwapService

    _, lib_a = await _setup_lib(session, "Swap A")
    org_b, _ = await _setup_lib(session, "Swap B")

    with pytest.raises(HTTPException) as exc:
        await SampleSwapService.list_checks(session, org_b.id, lib_a.id)
    assert exc.value.status_code == 404
