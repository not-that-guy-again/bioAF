"""Tests for plot archive bug fixes (#151 and related).

Covers:
- platform_config unique constraint enforcement (issue #151)
- Scanner uses app SA credentials, not bare ADC
- File content endpoint returns correct content-type for SVG and PDF
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import text


@pytest_asyncio.fixture
async def sample_svg_file(session, admin_user):
    from app.models.file import File

    f = File(
        organization_id=admin_user.organization_id,
        gcs_uri="gs://test-bucket/plots/heatmap.svg",
        filename="heatmap.svg",
        size_bytes=8000,
        file_type="svg",
        uploader_user_id=admin_user.id,
    )
    session.add(f)
    await session.flush()
    await session.commit()
    return f


@pytest_asyncio.fixture
async def sample_pdf_file(session, admin_user):
    from app.models.file import File

    f = File(
        organization_id=admin_user.organization_id,
        gcs_uri="gs://test-bucket/plots/stats_table.pdf",
        filename="stats_table.pdf",
        size_bytes=15000,
        file_type="pdf",
        uploader_user_id=admin_user.id,
    )
    session.add(f)
    await session.flush()
    await session.commit()
    return f


# -- Issue #151: platform_config unique constraint --


@pytest.mark.asyncio
async def test_platform_config_rejects_duplicate_keys(session):
    """After migration 065, inserting a duplicate key into platform_config
    must raise an IntegrityError."""
    from sqlalchemy.exc import IntegrityError

    await session.execute(
        text("INSERT INTO platform_config (key, value) VALUES ('_test_unique_key', 'first') ON CONFLICT DO NOTHING")
    )
    await session.commit()

    with pytest.raises(IntegrityError):
        await session.execute(text("INSERT INTO platform_config (key, value) VALUES ('_test_unique_key', 'second')"))
        await session.commit()

    await session.rollback()

    # Cleanup
    await session.execute(text("DELETE FROM platform_config WHERE key = '_test_unique_key'"))
    await session.commit()


# -- Scanner uses app SA credentials --


@pytest.mark.asyncio
async def test_scan_and_index_uses_app_credentials(session):
    """scan_and_index must use GcsStorageService.get_credentials, not bare
    ADC, to authenticate with GCS."""
    from app.services.plot_archive_service import PlotArchiveService

    mock_creds = MagicMock()
    mock_get_creds = AsyncMock(return_value=mock_creds)
    mock_client_cls = MagicMock()
    mock_bucket = mock_client_cls.return_value.bucket.return_value
    mock_bucket.list_blobs.return_value = []

    # Insert results_bucket_name so the scanner doesn't bail early
    await session.execute(
        text(
            "INSERT INTO platform_config (key, value) "
            "VALUES ('results_bucket_name', 'test-results-bucket') "
            "ON CONFLICT (key) DO UPDATE SET value = 'test-results-bucket'"
        )
    )
    await session.commit()

    with (
        patch("google.cloud.storage.Client", mock_client_cls),
        patch(
            "app.services.gcs_storage.GcsStorageService.get_credentials",
            mock_get_creds,
        ),
    ):
        await PlotArchiveService.scan_and_index(session)

    # Verify get_credentials was called
    mock_get_creds.assert_called_once()

    # Verify Client was instantiated with those credentials
    mock_client_cls.assert_called_once_with(credentials=mock_creds)


# -- File content endpoint: SVG content type --


@pytest.mark.asyncio
async def test_content_endpoint_returns_svg_content_type(client, admin_token, sample_svg_file):
    """GET /api/files/{id}/content for an SVG file must return
    Content-Type: image/svg+xml."""
    mock_client_cls = MagicMock()
    mock_blob = mock_client_cls.return_value.bucket.return_value.blob.return_value
    mock_blob.download_as_bytes.return_value = b"<svg></svg>"

    with (
        patch("google.cloud.storage.Client", mock_client_cls),
        patch(
            "app.services.gcs_storage.GcsStorageService.get_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        resp = await client.get(
            f"/api/files/{sample_svg_file.id}/content",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/svg+xml"


# -- File content endpoint: PDF content type --


@pytest.mark.asyncio
async def test_content_endpoint_returns_pdf_content_type(client, admin_token, sample_pdf_file):
    """GET /api/files/{id}/content for a PDF file must return
    Content-Type: application/pdf."""
    mock_client_cls = MagicMock()
    mock_blob = mock_client_cls.return_value.bucket.return_value.blob.return_value
    mock_blob.download_as_bytes.return_value = b"%PDF-1.4 fake"

    with (
        patch("google.cloud.storage.Client", mock_client_cls),
        patch(
            "app.services.gcs_storage.GcsStorageService.get_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        resp = await client.get(
            f"/api/files/{sample_pdf_file.id}/content",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
