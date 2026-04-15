"""API tests for Library and BarcodeMap endpoints (issue #233 §8).

Covers the three mandatory scenarios from the issue:
  1. Creation via API (RBAC + org scoping).
  2. Lookup by barcode.
  3. Lineage traversal (upstream: File -> Library -> Sample -> Experiment;
     downstream: Sample -> Libraries -> Files).
"""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _create_experiment(client, token) -> int:
    r = await client.post(
        "/api/experiments",
        json={"name": "Lib API Exp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def _create_sample(client, token, experiment_id: int) -> int:
    r = await client.post(
        f"/api/experiments/{experiment_id}/samples",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


# --- 1. Creation ---


async def test_create_library_via_api(client, admin_token, session):

    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)

    r = await client.post(
        "/api/libraries",
        json={
            "sample_id": sample_id,
            "library_id_external": "LIB-API-001",
            "index_type": "dual",
            "i5_sequence": "aagtccgt",
            "i7_sequence": "GCATACGA",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["library_id_external"] == "LIB-API-001"
    assert data["i5_sequence"] == "AAGTCCGT"
    assert data["i7_sequence"] == "GCATACGA"
    assert data["status"] == "planned"

    # library_index BarcodeMaps auto-created.
    list_r = await client.get(
        f"/api/libraries/{data['id']}/barcodes?barcode_type=library_index",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_r.status_code == 200
    positions = {b["read_position"]: b["sequence"] for b in list_r.json()}
    assert positions == {"I1": "GCATACGA", "I2": "AAGTCCGT"}


async def test_viewer_cannot_create_library(client, admin_token, viewer_token):
    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)
    r = await client.post(
        "/api/libraries",
        json={"sample_id": sample_id},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert r.status_code == 403


async def test_viewer_can_read_library(client, admin_token, viewer_token):
    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)
    create_r = await client.post(
        "/api/libraries",
        json={"sample_id": sample_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_r.status_code == 200
    lib_id = create_r.json()["id"]

    get_r = await client.get(
        f"/api/libraries/{lib_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert get_r.status_code == 200


async def test_create_library_rejects_invalid_sequence(client, admin_token):
    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)
    r = await client.post(
        "/api/libraries",
        json={
            "sample_id": sample_id,
            "index_type": "single",
            "i7_sequence": "BADSEQ!",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 422


async def test_create_barcode_via_api(client, admin_token):
    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)
    lib = (
        await client.post(
            "/api/libraries",
            json={"sample_id": sample_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    r = await client.post(
        f"/api/libraries/{lib['id']}/barcodes",
        json={
            "barcode_type": "sgrna",
            "sequence": "ATCGATCG",
            "name": "guide-1",
            "read_position": "R1",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["sequence"] == "ATCGATCG"


# --- 2. Lookup by barcode ---


async def test_lookup_barcode_by_sequence(client, admin_token):
    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)
    lib = (
        await client.post(
            "/api/libraries",
            json={
                "sample_id": sample_id,
                "index_type": "dual",
                "i5_sequence": "AAAA",
                "i7_sequence": "TTTT",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    r = await client.get(
        "/api/barcodes/lookup?sequence=tttt",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    matches = r.json()
    assert any(m["library_id"] == lib["id"] and m["sequence"] == "TTTT" for m in matches)


async def test_lookup_org_scoped(client, admin_token, session):
    """A sequence registered in another org must not surface."""
    from app.models import BarcodeMap
    from app.models.experiment import Experiment
    from app.models.library import Library
    from app.models.organization import Organization
    from app.models.sample import Sample

    other_org = Organization(name="Other Tenant", setup_complete=True)
    session.add(other_org)
    await session.flush()
    exp = Experiment(name="other", organization_id=other_org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    lib = Library(
        organization_id=other_org.id,
        sample_id=sample.id,
        i7_sequence="GGGGCCCC",
    )
    session.add(lib)
    await session.flush()
    session.add(
        BarcodeMap(
            organization_id=other_org.id,
            library_id=lib.id,
            barcode_type="library_index",
            sequence="GGGGCCCC",
            read_position="I1",
        )
    )
    await session.commit()

    r = await client.get(
        "/api/barcodes/lookup?sequence=GGGGCCCC",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


async def test_batch_collision_endpoint(client, admin_token, session):
    from app.models.sequencing_batch import SequencingBatch

    # Seed batch within the admin's org.
    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()
    batch = SequencingBatch(organization_id=admin.organization_id, code="COL-1", status="pending")
    session.add(batch)
    await session.flush()
    await session.commit()

    exp_id = await _create_experiment(client, admin_token)
    sample_a = await _create_sample(client, admin_token, exp_id)
    sample_b = await _create_sample(client, admin_token, exp_id)

    for sid in (sample_a, sample_b):
        r = await client.post(
            "/api/libraries",
            json={
                "sample_id": sid,
                "index_type": "dual",
                "i5_sequence": "AAAA",
                "i7_sequence": "CCCC",
                "sequencing_batch_id": batch.id,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text

    r = await client.get(
        f"/api/sequencing-batches/{batch.id}/barcode-collisions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    collisions = r.json()
    assert len(collisions) == 1
    assert collisions[0]["i5_sequence"] == "AAAA"
    assert collisions[0]["i7_sequence"] == "CCCC"


# --- 3. Lineage traversal ---


async def test_upstream_lineage_file_to_library_to_sample_to_experiment(client, admin_token, session):
    from app.models import File

    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)
    lib = (
        await client.post(
            "/api/libraries",
            json={"sample_id": sample_id},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()
    f = File(
        organization_id=admin.organization_id,
        gcs_uri="gs://test/lineage.fq.gz",
        filename="lineage.fq.gz",
        file_type="fastq",
    )
    session.add(f)
    await session.flush()
    await session.commit()

    attach_r = await client.post(
        f"/api/libraries/{lib['id']}/files/{f.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert attach_r.status_code == 200

    # Re-read File fresh from DB to traverse up to Experiment.
    from app.models.experiment import Experiment
    from app.models.library import Library
    from app.models.sample import Sample

    file_row = await session.get(File, f.id)
    await session.refresh(file_row)
    assert file_row.library_id == lib["id"]

    lib_row = await session.get(Library, file_row.library_id)
    sample_row = await session.get(Sample, lib_row.sample_id)
    exp_row = await session.get(Experiment, sample_row.experiment_id)
    assert sample_row.id == sample_id
    assert exp_row.id == exp_id


async def test_downstream_lineage_sample_to_libraries_to_files(client, admin_token, session):
    from app.models import File
    from sqlalchemy.orm import selectinload

    exp_id = await _create_experiment(client, admin_token)
    sample_id = await _create_sample(client, admin_token, exp_id)

    lib_a = (
        await client.post(
            "/api/libraries",
            json={
                "sample_id": sample_id,
                "library_id_external": "DS-A",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()
    lib_b = (
        await client.post(
            "/api/libraries",
            json={
                "sample_id": sample_id,
                "library_id_external": "DS-B",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    ).json()

    list_r = await client.get(
        f"/api/samples/{sample_id}/libraries",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_r.status_code == 200
    ids = {lib["id"] for lib in list_r.json()}
    assert ids == {lib_a["id"], lib_b["id"]}

    # Attach a file to lib_a.
    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()
    f = File(
        organization_id=admin.organization_id,
        gcs_uri="gs://test/ds.fq.gz",
        filename="ds.fq.gz",
        file_type="fastq",
    )
    session.add(f)
    await session.flush()
    await session.commit()

    attach_r = await client.post(
        f"/api/libraries/{lib_a['id']}/files/{f.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert attach_r.status_code == 200

    # Sample -> Library.files traversal.
    from app.models.library import Library

    lib_row = (
        await session.execute(select(Library).options(selectinload(Library.files)).where(Library.id == lib_a["id"]))
    ).scalar_one()
    assert [lf.id for lf in lib_row.files] == [f.id]


async def test_experiment_libraries_endpoint(client, admin_token):
    exp_id = await _create_experiment(client, admin_token)
    s1 = await _create_sample(client, admin_token, exp_id)
    s2 = await _create_sample(client, admin_token, exp_id)
    await client.post(
        "/api/libraries",
        json={"sample_id": s1, "library_id_external": "EX-A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/libraries",
        json={"sample_id": s2, "library_id_external": "EX-B"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    r = await client.get(
        f"/api/experiments/{exp_id}/libraries",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200
    externals = sorted(lib["library_id_external"] for lib in r.json())
    assert externals == ["EX-A", "EX-B"]
