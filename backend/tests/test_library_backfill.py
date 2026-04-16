"""Tests for library backfill wizard (issue #244 §4.4, backend only)."""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _bootstrap(session):
    from app.models.experiment import Experiment
    from app.models.organization import Organization

    org = Organization(name="Backfill Org", setup_complete=True)
    session.add(org)
    await session.flush()
    exp = Experiment(name="Backfill Exp", organization_id=org.id)
    session.add(exp)
    await session.flush()
    await session.commit()
    return org, exp


async def _sample(session, experiment_id, **kw):
    from app.models.sample import Sample

    s = Sample(experiment_id=experiment_id, **kw)
    session.add(s)
    await session.flush()
    return s


async def _file_on_sample(session, org_id, sample_id, filename):
    from app.models.file import File
    from app.models.sample import sample_files

    f = File(
        organization_id=org_id,
        gcs_uri=f"gs://bf/{filename}",
        filename=filename,
        file_type="fastq",
    )
    session.add(f)
    await session.flush()
    await session.execute(sample_files.insert().values(sample_id=sample_id, file_id=f.id))
    await session.flush()
    return f


async def test_preview_returns_planned_rows_without_writes(session):
    from app.models.library import Library
    from app.services.library_backfill_service import LibraryBackfillService

    org, exp = await _bootstrap(session)
    s1 = await _sample(session, exp.id, library_prep_method="TruSeq", library_layout="paired")
    s2 = await _sample(session, exp.id, library_prep_method="SMART-seq", library_layout="single")
    await _file_on_sample(session, org.id, s1.id, "s1_r1.fastq.gz")
    await _file_on_sample(session, org.id, s2.id, "s2_r1.fastq.gz")
    await session.commit()

    preview = await LibraryBackfillService.preview(session, org.id, exp.id)

    assert preview.libraries_to_create == 2
    assert preview.files_to_attach == 2
    assert preview.samples_skipped == 0
    sample_ids = sorted(entry.sample_id for entry in preview.entries)
    assert sample_ids == sorted([s1.id, s2.id])

    # Preview must not write anything.
    count = (await session.execute(select(Library))).scalars().all()
    assert len(count) == 0


async def test_commit_creates_libraries_and_attaches_files(session):
    from app.models.file import File
    from app.models.library import Library
    from app.services.library_backfill_service import LibraryBackfillService

    org, exp = await _bootstrap(session)
    s1 = await _sample(session, exp.id, library_prep_method="TruSeq", library_layout="paired")
    f1 = await _file_on_sample(session, org.id, s1.id, "s1.fastq.gz")
    await session.commit()

    result = await LibraryBackfillService.commit(session, org.id, exp.id)
    await session.commit()

    libs = (await session.execute(select(Library).where(Library.sample_id == s1.id))).scalars().all()
    assert len(libs) == 1
    lib = libs[0]
    assert lib.prep_kit == "TruSeq"
    assert lib.read_layout == "paired"

    file_row = await session.get(File, f1.id)
    assert file_row.library_id == lib.id
    assert result.libraries_created == 1
    assert result.files_attached == 1


async def test_commit_is_idempotent(session):
    from app.models.library import Library
    from app.services.library_backfill_service import LibraryBackfillService

    org, exp = await _bootstrap(session)
    s1 = await _sample(session, exp.id, library_prep_method="TruSeq")
    await _file_on_sample(session, org.id, s1.id, "s1.fastq.gz")
    await session.commit()

    first = await LibraryBackfillService.commit(session, org.id, exp.id)
    await session.commit()
    second = await LibraryBackfillService.commit(session, org.id, exp.id)
    await session.commit()

    assert first.libraries_created == 1
    assert first.files_attached == 1
    assert second.libraries_created == 0
    assert second.files_attached == 0

    libs = (await session.execute(select(Library).where(Library.sample_id == s1.id))).scalars().all()
    assert len(libs) == 1


async def test_commit_skips_samples_with_existing_library(session):
    from app.schemas.library import LibraryCreate
    from app.services.library_backfill_service import LibraryBackfillService
    from app.services.library_service import LibraryService

    org, exp = await _bootstrap(session)
    s1 = await _sample(session, exp.id)
    await LibraryService.create_library(
        session, org.id, LibraryCreate(sample_id=s1.id, library_id_external="PRE-EXISTING")
    )
    await _file_on_sample(session, org.id, s1.id, "existing.fastq.gz")
    await session.commit()

    result = await LibraryBackfillService.commit(session, org.id, exp.id)
    await session.commit()
    assert result.libraries_created == 0
    assert result.samples_skipped == 1


async def test_commit_leaves_already_linked_files_untouched(session):
    from app.models.file import File
    from app.services.library_backfill_service import LibraryBackfillService

    org, exp = await _bootstrap(session)
    s1 = await _sample(session, exp.id, library_prep_method="TruSeq")
    # File already has a library_id set elsewhere; don't overwrite it.
    from app.schemas.library import LibraryCreate
    from app.services.library_service import LibraryService

    s_other = await _sample(session, exp.id)
    existing_lib = await LibraryService.create_library(session, org.id, LibraryCreate(sample_id=s_other.id))
    await session.commit()

    f = await _file_on_sample(session, org.id, s1.id, "linked.fastq.gz")
    f.library_id = existing_lib.id
    await session.flush()
    await session.commit()

    await LibraryBackfillService.commit(session, org.id, exp.id)
    await session.commit()

    refreshed = await session.get(File, f.id)
    assert refreshed.library_id == existing_lib.id


async def test_preview_is_org_scoped(session):
    from fastapi import HTTPException

    from app.models.organization import Organization
    from app.services.library_backfill_service import LibraryBackfillService

    _, exp = await _bootstrap(session)
    other_org = Organization(name="Other BF Org", setup_complete=True)
    session.add(other_org)
    await session.flush()
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await LibraryBackfillService.preview(session, other_org.id, exp.id)
    assert exc.value.status_code == 404


async def test_backfill_api_preview_and_commit(client, admin_token, session):
    from app.models.user import User

    admin = (await session.execute(select(User).limit(1))).scalar_one()

    exp = await client.post(
        "/api/experiments",
        json={"name": "BF API Exp"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    exp_id = exp.json()["id"]

    smp = await client.post(
        f"/api/experiments/{exp_id}/samples",
        json={"library_prep_method": "TruSeq", "library_layout": "paired"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    sample_id = smp.json()["id"]

    # Upload a file and link it to the sample via the ORM (upload flow is
    # out of scope here).
    from app.models.file import File
    from app.models.sample import sample_files

    f = File(
        organization_id=admin.organization_id,
        gcs_uri="gs://bf/api.fq.gz",
        filename="api.fq.gz",
        file_type="fastq",
    )
    session.add(f)
    await session.flush()
    await session.execute(sample_files.insert().values(sample_id=sample_id, file_id=f.id))
    await session.commit()

    preview_r = await client.post(
        f"/api/experiments/{exp_id}/backfill-libraries/preview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert preview_r.status_code == 200, preview_r.text
    assert preview_r.json()["libraries_to_create"] == 1
    assert preview_r.json()["files_to_attach"] == 1

    commit_r = await client.post(
        f"/api/experiments/{exp_id}/backfill-libraries/commit",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert commit_r.status_code == 200
    assert commit_r.json()["libraries_created"] == 1
    assert commit_r.json()["files_attached"] == 1


async def test_backfill_api_requires_admin_level_permission(client, admin_token, viewer_token):
    exp = await client.post(
        "/api/experiments",
        json={"name": "BF RBAC Exp"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    exp_id = exp.json()["id"]

    preview_r = await client.post(
        f"/api/experiments/{exp_id}/backfill-libraries/preview",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert preview_r.status_code == 403
