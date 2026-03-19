"""Tests for QC dashboard plot generation, GCS upload, and metrics extraction."""

import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_run(output_files: list[str], experiment_id: int = 10, run_id: int = 5):
    """Build a mock PipelineRun with output_files_json."""
    run = MagicMock()
    run.id = run_id
    run.experiment_id = experiment_id
    run.output_files_json = {"files": output_files}
    return run


@pytest.mark.asyncio
async def test_extract_metrics_reads_cached_json():
    """When qc_metrics.json exists in GCS, use it instead of downloading h5ad."""
    cached = {
        "cell_count": 3000,
        "median_genes_per_cell": 1500.0,
        "median_umi_per_cell": 8000.0,
        "mito_pct_median": 3.2,
        "doublet_score_median": None,
        "saturation": None,
        "median_reads_per_cell": None,
    }

    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_blob.download_as_text.return_value = json.dumps(cached)

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob

    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    mock_session = AsyncMock()

    run = _make_run(["filtered.h5ad"])

    with (
        patch("google.cloud.storage.Client", return_value=mock_client),
        patch.object(
            QCDashboardService,
            "_get_results_bucket",
            return_value="my-results-bucket",
        ),
        patch(
            "app.services.qc_dashboard_service.GcsStorageService.get_credentials",
            return_value=None,
        ),
    ):
        metrics = await QCDashboardService._extract_metrics(mock_session, run)

    assert metrics["cell_count"] == 3000
    assert metrics["median_genes_per_cell"] == 1500.0
    assert metrics["mito_pct_median"] == 3.2
    # Should NOT have tried to download h5ad
    mock_blob.download_to_filename.assert_not_called()


@pytest.mark.asyncio
async def test_extract_metrics_downloads_h5ad_when_no_cache():
    """When no cached JSON exists, download h5ad and extract metrics."""
    mock_cache_blob = MagicMock()
    mock_cache_blob.exists.return_value = False

    mock_upload_blob = MagicMock()

    mock_h5ad_blob = MagicMock()
    mock_h5ad_blob.name = "experiments/10/pipeline-runs/5/filtered.h5ad"

    mock_bucket = MagicMock()

    def blob_side_effect(path):
        if path.endswith("qc_metrics.json"):
            return mock_cache_blob
        if path.endswith("qc_metrics_cache.json"):
            return mock_upload_blob
        return mock_h5ad_blob

    mock_bucket.blob.side_effect = blob_side_effect
    mock_bucket.list_blobs.return_value = [mock_h5ad_blob]

    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket

    mock_session = AsyncMock()
    run = _make_run(["filtered.h5ad"])

    # Mock anndata to avoid needing the real library
    mock_obs = MagicMock()
    mock_obs.columns = ["n_genes", "total_counts", "pct_counts_mt"]
    mock_obs.__getitem__ = lambda self, key: [1500, 2000, 1800]

    mock_adata = MagicMock()
    mock_adata.n_obs = 3000
    mock_adata.obs = mock_obs

    with (
        patch("google.cloud.storage.Client", return_value=mock_client),
        patch.object(
            QCDashboardService,
            "_get_results_bucket",
            return_value="my-results-bucket",
        ),
        patch(
            "app.services.qc_dashboard_service.GcsStorageService.get_credentials",
            return_value=None,
        ),
        patch.dict("sys.modules", {"anndata": MagicMock(), "numpy": MagicMock()}),
        patch(
            "app.services.qc_dashboard_service.QCDashboardService._read_h5ad_metrics",
            return_value={
                "cell_count": 3000,
                "median_genes_per_cell": 1500.0,
                "median_umi_per_cell": 8000.0,
                "mito_pct_median": 3.2,
                "doublet_score_median": None,
                "median_reads_per_cell": None,
                "saturation": None,
            },
        ),
    ):
        metrics = await QCDashboardService._extract_metrics(mock_session, run)

    assert metrics["cell_count"] == 3000
    # Should have downloaded the h5ad
    mock_h5ad_blob.download_to_filename.assert_called_once()
    # Should have uploaded the cache
    mock_upload_blob.upload_from_string.assert_called_once()


@pytest.mark.asyncio
async def test_extract_metrics_returns_empty_when_no_results_bucket():
    """Returns empty metrics when results bucket is not configured."""
    mock_session = AsyncMock()
    run = _make_run(["filtered.h5ad"])

    with (
        patch.object(
            QCDashboardService,
            "_get_results_bucket",
            return_value=None,
        ),
        patch(
            "app.services.qc_dashboard_service.GcsStorageService.get_credentials",
            return_value=None,
        ),
    ):
        metrics = await QCDashboardService._extract_metrics(mock_session, run)

    assert metrics["cell_count"] is None
    assert metrics["median_genes_per_cell"] is None
