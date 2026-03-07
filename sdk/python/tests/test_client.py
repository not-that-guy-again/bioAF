"""Tests for bioaf client module."""

import os
from unittest.mock import patch

from bioaf.client import _get_config, connect


class TestConnect:
    def test_connect_with_explicit_args(self):
        connect(api_url="https://bioaf.example.com", token="mytoken123")
        cfg = _get_config()
        assert cfg["api_url"] == "https://bioaf.example.com"
        assert cfg["token"] == "mytoken123"

    def test_connect_reads_env_vars(self):
        env = {
            "BIOAF_API_URL": "https://env.example.com",
            "BIOAF_TOKEN": "envtoken",
            "BIOAF_EXPERIMENT_ID": "42",
            "BIOAF_PROJECT_ID": "7",
            "BIOAF_SESSION_ID": "99",
        }
        with patch.dict(os.environ, env, clear=False):
            connect()
            cfg = _get_config()
            assert cfg["api_url"] == "https://env.example.com"
            assert cfg["token"] == "envtoken"
            assert cfg["experiment_id"] == "42"
            assert cfg["project_id"] == "7"
            assert cfg["session_id"] == "99"

    def test_connect_explicit_overrides_env(self):
        env = {
            "BIOAF_API_URL": "https://env.example.com",
            "BIOAF_TOKEN": "envtoken",
        }
        with patch.dict(os.environ, env, clear=False):
            connect(api_url="https://explicit.com", token="explicittoken")
            cfg = _get_config()
            assert cfg["api_url"] == "https://explicit.com"
            assert cfg["token"] == "explicittoken"

    def test_post_includes_auth_header(self):
        from unittest.mock import MagicMock

        connect(api_url="https://test.com", token="testtoken")

        with patch("bioaf.client.requests") as mock_requests:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"id": 1}
            mock_resp.raise_for_status = MagicMock()
            mock_requests.post.return_value = mock_resp

            from bioaf.client import _post

            _post("/api/snapshots", json={"label": "test"})

            call_kwargs = mock_requests.post.call_args
            assert "Authorization" in call_kwargs.kwargs["headers"]
            assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer testtoken"
