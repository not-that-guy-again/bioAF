"""Tests for QC dashboard plot generation and GCS upload."""

import io
from unittest.mock import MagicMock, patch

import pytest

from app.services.qc_dashboard_service import QCDashboardService


def test_has_plottable_metrics_with_data():
    """Returns True when at least one plottable metric is present."""
    metrics = {"cell_count": 5000, "median_genes_per_cell": 2000}
    assert QCDashboardService._has_plottable_metrics(metrics) is True


def test_has_plottable_metrics_all_none():
    """Returns False when all plottable metrics are None."""
    metrics = {
        "cell_count": None,
        "median_genes_per_cell": None,
        "median_umi_per_cell": None,
        "mito_pct_median": None,
    }
    assert QCDashboardService._has_plottable_metrics(metrics) is False


def test_has_plottable_metrics_empty():
    """Returns False for an empty metrics dict."""
    assert QCDashboardService._has_plottable_metrics({}) is False


@pytest.mark.asyncio
async def test_upload_plot_to_gcs_sends_bytes():
    """_upload_plot_to_gcs must upload a buffer to the correct GCS path."""
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    buf = io.BytesIO(b"fake-png-data")

    with patch("google.cloud.storage.Client", return_value=mock_client):
        await QCDashboardService._upload_plot_to_gcs(
            "bioaf-results-test",
            "qc_plots/qc_dashboard_1_genes_per_cell_hist.png",
            buf,
            credentials=None,
        )

    mock_client.bucket.assert_called_once_with("bioaf-results-test")
    mock_bucket.blob.assert_called_once_with("qc_plots/qc_dashboard_1_genes_per_cell_hist.png")
    mock_blob.upload_from_file.assert_called_once()
    call_kwargs = mock_blob.upload_from_file.call_args
    assert call_kwargs.kwargs.get("content_type") == "image/png"


@pytest.mark.asyncio
async def test_upload_plot_uses_credentials():
    """_upload_plot_to_gcs should pass credentials to the storage client."""
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    fake_creds = MagicMock()
    buf = io.BytesIO(b"fake-png-data")

    with patch("google.cloud.storage.Client", return_value=mock_client) as mock_cls:
        await QCDashboardService._upload_plot_to_gcs(
            "bioaf-results-test",
            "qc_plots/test.png",
            buf,
            credentials=fake_creds,
        )

    mock_cls.assert_called_once_with(credentials=fake_creds)
