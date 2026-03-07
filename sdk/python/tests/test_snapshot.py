"""Tests for snapshot function."""

from unittest.mock import patch

import numpy as np
import pandas as pd
import anndata

from bioaf.client import connect
from bioaf.snapshot import snapshot


def _make_test_adata():
    return anndata.AnnData(
        X=np.random.rand(100, 50),
        obs=pd.DataFrame(
            {
                "leiden": pd.Categorical(["0"] * 40 + ["1"] * 35 + ["2"] * 25),
                "batch": pd.Categorical(["A"] * 50 + ["B"] * 50),
            }
        ),
        obsm={"X_pca": np.random.rand(100, 50), "X_umap": np.random.rand(100, 2)},
        uns={"neighbors": {"params": {"n_neighbors": 15, "method": "umap"}}},
        layers={"raw_counts": np.random.randint(0, 100, (100, 50))},
    )


class TestSnapshot:
    def test_snapshot_with_anndata(self):
        connect(api_url="https://test.com", token="tok")
        adata = _make_test_adata()

        with patch("bioaf.snapshot._post") as mock_post:
            mock_post.return_value = {"id": 1, "label": "test"}
            snapshot(adata, label="test_snap", experiment_id=42)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["label"] == "test_snap"
        assert payload["experiment_id"] == 42
        assert payload["object_type"] == "anndata"
        assert payload["cell_count"] == 100
        assert "embeddings_json" in payload
        assert "clusterings_json" in payload

    def test_snapshot_with_notes(self):
        connect(api_url="https://test.com", token="tok")
        adata = _make_test_adata()

        with patch("bioaf.snapshot._post") as mock_post:
            mock_post.return_value = {"id": 1}
            snapshot(adata, label="snap", notes="Over-clustered", experiment_id=1)

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["notes"] == "Over-clustered"

    def test_snapshot_with_figure(self):
        connect(api_url="https://test.com", token="tok")
        adata = _make_test_adata()

        with patch("bioaf.snapshot._post") as mock_post:
            # First call: figure upload, second call: snapshot create
            mock_post.side_effect = [{"id": 99}, {"id": 1}]
            snapshot(adata, label="snap", figure=b"fake_png_bytes", experiment_id=1)

        # Should have been called twice (figure upload + snapshot create)
        assert mock_post.call_count == 2
        # Snapshot payload should include figure_file_id
        snap_call = mock_post.call_args_list[1]
        payload = snap_call.kwargs.get("json") or snap_call[1].get("json")
        assert payload["figure_file_id"] == 99

    def test_snapshot_api_failure_raises(self):
        connect(api_url="https://test.com", token="tok")
        adata = _make_test_adata()

        with patch("bioaf.snapshot._post") as mock_post:
            import requests

            mock_post.side_effect = requests.HTTPError("500 Server Error")
            try:
                snapshot(adata, label="snap", experiment_id=1)
                assert False, "Should have raised"
            except requests.HTTPError:
                pass

    def test_snapshot_uses_config_experiment_id(self):
        import os

        env = {"BIOAF_EXPERIMENT_ID": "77"}
        with patch.dict(os.environ, env, clear=False):
            connect(api_url="https://test.com", token="tok")

        with patch("bioaf.snapshot._post") as mock_post:
            mock_post.return_value = {"id": 1}
            snapshot(_make_test_adata(), label="snap")

        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["experiment_id"] == 77
