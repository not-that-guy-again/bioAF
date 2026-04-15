"""Tests for BarcodeService (issue #233 §6)."""

import pytest

pytestmark = pytest.mark.asyncio


async def _make_library(session, org=None, sample=None, **kwargs):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    if org is None:
        org = Organization(name=kwargs.pop("org_name", "BC Svc Org"), setup_complete=True)
        session.add(org)
        await session.flush()
    if sample is None:
        exp = Experiment(name="BC Svc Exp", organization_id=org.id)
        session.add(exp)
        await session.flush()
        sample = Sample(experiment_id=exp.id)
        session.add(sample)
        await session.flush()
    lib = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(sample_id=sample.id, **kwargs),
    )
    await session.commit()
    return org, sample, lib


async def test_create_barcode_map_canonicalises_sequence(session):
    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, _, lib = await _make_library(session)
    bm = await BarcodeService.create_barcode_map(
        session,
        org.id,
        lib.id,
        BarcodeMapCreate(
            barcode_type="hashtag",
            sequence=" acgtn ",
            name="HT-1",
            read_position="R2",
            length=5,
        ),
    )
    await session.commit()
    assert bm.sequence == "ACGTN"


async def test_create_barcode_map_rejects_invalid_chars(session):
    from fastapi import HTTPException

    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, _, lib = await _make_library(session)
    with pytest.raises(HTTPException) as exc:
        await BarcodeService.create_barcode_map(
            session,
            org.id,
            lib.id,
            BarcodeMapCreate(barcode_type="hashtag", sequence="AXCZ"),
        )
    assert exc.value.status_code == 422


async def test_lookup_by_sequence_returns_matches(session):
    from app.schemas.barcode_map import BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, _, lib = await _make_library(
        session, index_type="dual", i5_sequence="TTTT", i7_sequence="AAAA"
    )
    await BarcodeService.create_barcode_map(
        session,
        org.id,
        lib.id,
        BarcodeMapCreate(barcode_type="hashtag", sequence="GGGG", name="HT-A"),
    )
    await session.commit()

    # library_index row was auto-created with i7 = AAAA on I1
    matches = await BarcodeService.lookup_by_sequence(session, org.id, "aaaa")
    assert any(m.sequence == "AAAA" and m.barcode_type == "library_index" for m in matches)

    filtered = await BarcodeService.lookup_by_sequence(
        session, org.id, "GGGG", barcode_type="hashtag"
    )
    assert len(filtered) == 1
    assert filtered[0].name == "HT-A"


async def test_lookup_is_org_scoped(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.services.barcode_service import BarcodeService

    org_a, _, lib_a = await _make_library(
        session, index_type="single", i7_sequence="AAAA"
    )
    # Other org with colliding sequence.
    org_b = Organization(name="Other BC Org", setup_complete=True)
    session.add(org_b)
    await session.flush()
    exp_b = Experiment(name="E", organization_id=org_b.id)
    session.add(exp_b)
    await session.flush()
    sample_b = Sample(experiment_id=exp_b.id)
    session.add(sample_b)
    await session.flush()
    await _make_library(
        session, org=org_b, sample=sample_b, index_type="single", i7_sequence="AAAA"
    )

    matches_a = await BarcodeService.lookup_by_sequence(session, org_a.id, "AAAA")
    for m in matches_a:
        assert m.organization_id == org_a.id
        assert m.library_id == lib_a.id


async def test_detect_collisions_in_batch(session):
    """Per §8: two libraries in same batch with same (i5, i7) flagged; diff batches not."""
    from app.models.sample import Sample
    from app.models.sequencing_batch import SequencingBatch
    from app.schemas.library import LibraryCreate
    from app.services.barcode_service import BarcodeService
    from app.services.library_service import LibraryService

    org, seed_sample, _ = await _make_library(
        session, index_type="dual", i5_sequence="TTTT", i7_sequence="AAAA"
    )

    batch = SequencingBatch(organization_id=org.id, code="BC-1", status="pending")
    session.add(batch)
    await session.flush()
    batch2 = SequencingBatch(organization_id=org.id, code="BC-2", status="pending")
    session.add(batch2)
    await session.flush()

    # Two libraries with same indices, both in batch 1 -> collision.
    s1 = Sample(experiment_id=seed_sample.experiment_id)
    s2 = Sample(experiment_id=seed_sample.experiment_id)
    s3 = Sample(experiment_id=seed_sample.experiment_id)
    session.add_all([s1, s2, s3])
    await session.flush()

    lib1 = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=s1.id,
            index_type="dual",
            i5_sequence="CCCC",
            i7_sequence="GGGG",
            sequencing_batch_id=batch.id,
        ),
    )
    lib2 = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=s2.id,
            index_type="dual",
            i5_sequence="CCCC",
            i7_sequence="GGGG",
            sequencing_batch_id=batch.id,
        ),
    )
    # Same indices, different batch -> no collision.
    lib3 = await LibraryService.create_library(
        session,
        org.id,
        LibraryCreate(
            sample_id=s3.id,
            index_type="dual",
            i5_sequence="CCCC",
            i7_sequence="GGGG",
            sequencing_batch_id=batch2.id,
        ),
    )
    await session.commit()

    collisions = await BarcodeService.detect_collisions_in_batch(session, org.id, batch.id)
    collided_pairs = {tuple(sorted([c.library_a_id, c.library_b_id])) for c in collisions}
    assert (min(lib1.id, lib2.id), max(lib1.id, lib2.id)) in collided_pairs

    collisions_b2 = await BarcodeService.detect_collisions_in_batch(session, org.id, batch2.id)
    assert collisions_b2 == []
    # And lib3 is not in batch1 collisions.
    for c in collisions:
        assert lib3.id not in (c.library_a_id, c.library_b_id)


async def test_bulk_create_barcode_maps(session):
    from app.schemas.barcode_map import BarcodeMapBulkCreate, BarcodeMapCreate
    from app.services.barcode_service import BarcodeService

    org, _, lib = await _make_library(session)
    payload = BarcodeMapBulkCreate(
        entries=[
            BarcodeMapCreate(
                barcode_type="sgrna", sequence="AAAAAA", name="g1", read_position="R1"
            ),
            BarcodeMapCreate(
                barcode_type="sgrna", sequence="CCCCCC", name="g2", read_position="R1"
            ),
        ]
    )
    rows = await BarcodeService.bulk_create_barcode_maps(session, org.id, lib.id, payload)
    await session.commit()
    assert len(rows) == 2
    assert {r.name for r in rows} == {"g1", "g2"}
