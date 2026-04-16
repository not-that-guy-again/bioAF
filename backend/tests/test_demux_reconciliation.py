"""Tests for DemuxReconciliationService (issue #244 §4.3)."""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _bootstrap(session):
    """Create an org, experiment, sample, and a sequencing batch."""
    from app.models.experiment import Experiment
    from app.models.organization import Organization
    from app.models.sample import Sample
    from app.models.sequencing_batch import SequencingBatch

    org = Organization(name="Reconcile Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Reconcile Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    sample = Sample(experiment_id=exp.id)
    session.add(sample)
    await session.flush()
    batch = SequencingBatch(organization_id=org.id, code="RC-1", status="pending")
    session.add(batch)
    await session.flush()
    await session.commit()
    return org, exp, sample, batch


async def _library(session, org_id, sample_id, batch_id, **kw):
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    lib = await LibraryService.create_library(
        session,
        org_id,
        LibraryCreate(sample_id=sample_id, sequencing_batch_id=batch_id, **kw),
    )
    await session.commit()
    return lib


async def _file(session, org_id, batch_id, filename: str):
    from app.models.file import File

    f = File(
        organization_id=org_id,
        gcs_uri=f"gs://rc/{filename}",
        filename=filename,
        file_type="fastq",
        sequencing_batch_id=batch_id,
    )
    session.add(f)
    await session.flush()
    await session.commit()
    return f


async def test_reconcile_unambiguous_external_id_match(session):
    from app.models.file import File
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, _, sample, batch = await _bootstrap(session)
    lib = await _library(
        session,
        org.id,
        sample.id,
        batch.id,
        library_id_external="LIB-001",
        index_type="dual",
        i5_sequence="AAAA",
        i7_sequence="TTTT",
    )
    f = await _file(session, org.id, batch.id, "LIB-001_S1_L001_R1_001.fastq.gz")

    report = await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()

    fetched = await session.get(File, f.id)
    assert fetched.library_id == lib.id
    assert report.matched == 1
    assert report.ambiguous == 0
    assert report.unmatched == 0


async def test_reconcile_unambiguous_index_pair_match(session):
    from app.models.file import File
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, _, sample, batch = await _bootstrap(session)
    lib = await _library(
        session,
        org.id,
        sample.id,
        batch.id,
        index_type="dual",
        i5_sequence="CCCC",
        i7_sequence="GGGG",
    )
    f = await _file(session, org.id, batch.id, "sample_GGGG+CCCC_L001_R1_001.fastq.gz")

    report = await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()

    fetched = await session.get(File, f.id)
    assert fetched.library_id == lib.id
    assert report.matched == 1


async def test_reconcile_ambiguous_leaves_file_unlinked(session):
    from app.models.file import File
    from app.models.sample import Sample
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, exp, sample, batch = await _bootstrap(session)
    # Two libraries share the same indices in the same batch (collision).
    s2 = Sample(experiment_id=exp.id)
    session.add(s2)
    await session.flush()
    await session.commit()

    await _library(
        session,
        org.id,
        sample.id,
        batch.id,
        index_type="dual",
        i5_sequence="AAAA",
        i7_sequence="TTTT",
    )
    await _library(
        session,
        org.id,
        s2.id,
        batch.id,
        index_type="dual",
        i5_sequence="AAAA",
        i7_sequence="TTTT",
    )
    f = await _file(session, org.id, batch.id, "x_TTTT+AAAA_L001_R1_001.fastq.gz")

    report = await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()

    fetched = await session.get(File, f.id)
    assert fetched.library_id is None
    assert report.ambiguous == 1
    assert report.matched == 0


async def test_reconcile_no_match_leaves_file_unlinked(session):
    from app.models.file import File
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, _, sample, batch = await _bootstrap(session)
    await _library(
        session,
        org.id,
        sample.id,
        batch.id,
        library_id_external="LIB-042",
        index_type="dual",
        i5_sequence="AAAA",
        i7_sequence="TTTT",
    )
    f = await _file(session, org.id, batch.id, "LIB-999_S1_L001_R1_001.fastq.gz")

    report = await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()

    fetched = await session.get(File, f.id)
    assert fetched.library_id is None
    assert report.unmatched == 1


async def test_reconcile_is_idempotent(session):
    from app.models.file import File
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, _, sample, batch = await _bootstrap(session)
    lib = await _library(
        session,
        org.id,
        sample.id,
        batch.id,
        library_id_external="LIB-IDEM",
        index_type="dual",
        i5_sequence="AAAA",
        i7_sequence="TTTT",
    )
    f = await _file(session, org.id, batch.id, "LIB-IDEM_S1_L001_R1_001.fastq.gz")

    await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()
    first = (await session.get(File, f.id)).library_id
    assert first == lib.id

    # Second run: no change, and the file count linked to the batch stays 1.
    second_report = await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()
    second = (await session.get(File, f.id)).library_id
    assert second == lib.id
    # Already-linked files are excluded from the reconciliation pool.
    assert second_report.matched == 0
    assert second_report.ambiguous == 0
    assert second_report.unmatched == 0


async def test_reconcile_skips_already_linked_files(session):
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, _, sample, batch = await _bootstrap(session)
    lib = await _library(session, org.id, sample.id, batch.id, library_id_external="LIB-PRE")

    # Pre-linked file; filename matches a different lib pattern but should not be touched.
    from app.models.file import File

    f = File(
        organization_id=org.id,
        gcs_uri="gs://rc/pre.fq.gz",
        filename="LIB-OTHER_S1_L001_R1_001.fastq.gz",
        file_type="fastq",
        sequencing_batch_id=batch.id,
        library_id=lib.id,
    )
    session.add(f)
    await session.flush()
    await session.commit()

    report = await DemuxReconciliationService.reconcile_batch(session, org.id, batch.id)
    await session.commit()
    assert report.matched + report.ambiguous + report.unmatched == 0


async def test_reconcile_is_org_scoped(session):
    from fastapi import HTTPException

    from app.models.organization import Organization
    from app.services.demux_reconciliation_service import (
        DemuxReconciliationService,
    )

    org, _, _, batch = await _bootstrap(session)
    other_org = Organization(name="Other Reconcile", setup_complete=True)
    session.add(other_org)
    await session.flush()
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await DemuxReconciliationService.reconcile_batch(session, other_org.id, batch.id)
    assert exc.value.status_code == 404


async def test_reconcile_api_endpoint(client, admin_token, session):
    from app.models.file import File
    from app.models.sequencing_batch import SequencingBatch
    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()

    batch = SequencingBatch(organization_id=admin.organization_id, code="RC-API", status="pending")
    session.add(batch)
    await session.flush()
    await session.commit()

    exp = await client.post(
        "/api/experiments",
        json={"name": "RC API Exp"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    exp_id = exp.json()["id"]
    smp = await client.post(
        f"/api/experiments/{exp_id}/samples",
        json={},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sample_id = smp.json()["id"]

    await client.post(
        "/api/libraries",
        json={
            "sample_id": sample_id,
            "library_id_external": "API-LIB",
            "index_type": "dual",
            "i5_sequence": "AAAA",
            "i7_sequence": "TTTT",
            "sequencing_batch_id": batch.id,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    f = File(
        organization_id=admin.organization_id,
        gcs_uri="gs://rc/api.fq.gz",
        filename="API-LIB_S1_L001_R1_001.fastq.gz",
        file_type="fastq",
        sequencing_batch_id=batch.id,
    )
    session.add(f)
    await session.flush()
    await session.commit()

    r = await client.post(
        f"/api/sequencing-batches/{batch.id}/reconcile",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["matched"] == 1
    assert body["unmatched"] == 0
    assert body["ambiguous"] == 0
