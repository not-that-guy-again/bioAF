import io
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def configured_ingest_bucket(session, admin_user):
    """Insert ingest_bucket_name into platform_config for this org's deployment."""
    from app.models.component import PlatformConfig

    cfg = PlatformConfig(key="ingest_bucket_name", value="bioaf-ingest-test-abc123")
    session.add(cfg)
    await session.flush()
    await session.commit()
    return "bioaf-ingest-test-abc123"


@pytest.mark.asyncio
async def test_initiate_upload_requires_bucket_config(client, admin_token):
    """Upload initiate must return 400 when ingest_bucket_name is not configured."""
    resp = await client.post(
        "/api/files/upload/initiate",
        json={"filename": "sample.fastq.gz", "expected_size_bytes": 1_000_000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "bucket" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_initiate_upload_uses_configured_bucket(client, admin_token, configured_ingest_bucket):
    """Upload initiate must use the bucket name stored in platform_config."""
    resp = await client.post(
        "/api/files/upload/initiate",
        json={"filename": "sample.fastq.gz", "expected_size_bytes": 1_000_000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert configured_ingest_bucket in data["gcs_uri"]


@pytest.mark.asyncio
async def test_initiate_upload_rejects_null_bucket(client, admin_token, session):
    """platform_config row with value 'null' is treated as not configured."""
    from app.models.component import PlatformConfig

    cfg = PlatformConfig(key="ingest_bucket_name", value="null")
    session.add(cfg)
    await session.flush()
    await session.commit()

    resp = await client.post(
        "/api/files/upload/initiate",
        json={"filename": "sample.fastq.gz", "expected_size_bytes": 1_000_000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# simple_upload: experiment_id linkage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simple_upload_links_experiment_id(client, admin_token, configured_ingest_bucket, session):
    """Files uploaded with ?experiment_id=N must have experiment_id set on the DB record."""
    from app.models.experiment import Experiment
    from app.models.user import User
    from sqlalchemy import select

    user = (await session.execute(select(User).limit(1))).scalar_one()
    exp = Experiment(
        organization_id=user.organization_id,
        name="Upload Link Test",
        owner_user_id=user.id,
        status="registered",
    )
    session.add(exp)
    await session.flush()
    await session.commit()

    with patch("app.services.upload_service.UploadService._upload_to_gcs", new_callable=AsyncMock):
        resp = await client.post(
            f"/api/files/upload/simple?experiment_id={exp.id}",
            files={"file": ("sample.fastq.gz", io.BytesIO(b"data"), "application/gzip")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200

    from app.models.file import File

    file_row = (await session.execute(select(File).where(File.filename == "sample.fastq.gz"))).scalar_one_or_none()
    assert file_row is not None
    assert file_row.experiment_id == exp.id


@pytest.mark.asyncio
async def test_simple_upload_without_experiment_id(client, admin_token, configured_ingest_bucket, session):
    """Files uploaded without ?experiment_id must have experiment_id=None."""
    from app.models.file import File
    from sqlalchemy import select

    with patch("app.services.upload_service.UploadService._upload_to_gcs", new_callable=AsyncMock):
        resp = await client.post(
            "/api/files/upload/simple",
            files={"file": ("noexp.fastq.gz", io.BytesIO(b"data"), "application/gzip")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    file_row = (await session.execute(select(File).where(File.filename == "noexp.fastq.gz"))).scalar_one_or_none()
    assert file_row is not None
    assert file_row.experiment_id is None


# ---------------------------------------------------------------------------
# simple_upload: GCS errors surface as 500
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_simple_upload_returns_500_on_gcs_failure(client, admin_token, configured_ingest_bucket):
    """GCS upload failure must return 500, not silently create a dangling file record."""
    from app.services.upload_service import UploadService

    async def fake_upload_to_gcs(*args, **kwargs):
        raise Exception("403 Provided scope(s) are not authorized")

    with patch.object(UploadService, "_upload_to_gcs", side_effect=fake_upload_to_gcs):
        resp = await client.post(
            "/api/files/upload/simple",
            files={"file": ("fail.fastq.gz", io.BytesIO(b"data"), "application/gzip")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 500
    assert "Upload failed" in resp.json()["detail"]
