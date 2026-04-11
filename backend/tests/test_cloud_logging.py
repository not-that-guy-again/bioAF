"""Tests for Google Cloud Logging auto-configuration.

Verifies that the logging configuration module detects GCE, attaches
a Cloud Logging handler when running on GCE, and falls back to
stdout-only when off GCE or when credentials are unavailable.
"""

import logging
from unittest.mock import MagicMock, patch


class TestGceDetection:
    """Test GCE metadata server detection."""

    def test_detects_gce_when_metadata_responds(self):
        from app.logging_config import is_running_on_gce

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"test-project"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.logging_config.urllib.request.urlopen", return_value=mock_response):
            assert is_running_on_gce() is True

    def test_not_gce_when_metadata_unavailable(self):
        from app.logging_config import is_running_on_gce

        with patch(
            "app.logging_config.urllib.request.urlopen",
            side_effect=Exception("Connection refused"),
        ):
            assert is_running_on_gce() is False


class TestGetGceProjectId:
    """Test GCE project ID retrieval from metadata."""

    def test_returns_project_id(self):
        from app.logging_config import get_gce_project_id

        mock_response = MagicMock()
        mock_response.read.return_value = b"my-gcp-project"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.logging_config.urllib.request.urlopen", return_value=mock_response):
            assert get_gce_project_id() == "my-gcp-project"

    def test_strips_whitespace(self):
        from app.logging_config import get_gce_project_id

        mock_response = MagicMock()
        mock_response.read.return_value = b"  my-project \n"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("app.logging_config.urllib.request.urlopen", return_value=mock_response):
            assert get_gce_project_id() == "my-project"


class TestConfigureLogging:
    """Test configure_logging()."""

    def setup_method(self):
        """Clear bioaf logger handlers before each test."""
        logging.getLogger("bioaf").handlers.clear()

    def test_stdout_handler_always_present(self):
        from app.logging_config import configure_logging

        with patch("app.logging_config.is_running_on_gce", return_value=False):
            configure_logging(debug=False)

        bioaf_logger = logging.getLogger("bioaf")
        stream_handlers = [h for h in bioaf_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    def test_cloud_handler_attached_on_gce(self):
        from app.logging_config import configure_logging

        mock_client = MagicMock()
        mock_handler = MagicMock(spec=logging.Handler)
        mock_handler.level = logging.NOTSET
        mock_client.get_default_handler.return_value = mock_handler

        with (
            patch("app.logging_config.is_running_on_gce", return_value=True),
            patch("app.logging_config.get_gce_project_id", return_value="test-project"),
            patch("app.logging_config.cloud_logging") as mock_module,
        ):
            mock_module.Client.return_value = mock_client
            configure_logging(debug=False)

        bioaf_logger = logging.getLogger("bioaf")
        assert mock_handler in bioaf_logger.handlers
        bioaf_logger.removeHandler(mock_handler)

    def test_no_cloud_handler_off_gce(self):
        from app.logging_config import configure_logging

        with patch("app.logging_config.is_running_on_gce", return_value=False):
            configure_logging(debug=False)

        bioaf_logger = logging.getLogger("bioaf")
        handler_types = [type(h).__name__ for h in bioaf_logger.handlers]
        assert "CloudLoggingHandler" not in handler_types

    def test_graceful_fallback_on_credential_error(self):
        from app.logging_config import configure_logging

        with (
            patch("app.logging_config.is_running_on_gce", return_value=True),
            patch("app.logging_config.get_gce_project_id", return_value="test-project"),
            patch("app.logging_config.cloud_logging") as mock_module,
        ):
            mock_module.Client.side_effect = Exception("No credentials")
            configure_logging(debug=False)

        bioaf_logger = logging.getLogger("bioaf")
        stream_handlers = [h for h in bioaf_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) >= 1

    def test_debug_mode_sets_debug_level(self):
        from app.logging_config import configure_logging

        with patch("app.logging_config.is_running_on_gce", return_value=False):
            configure_logging(debug=True)

        assert logging.getLogger("bioaf").level == logging.DEBUG

    def test_production_mode_sets_info_level(self):
        from app.logging_config import configure_logging

        with patch("app.logging_config.is_running_on_gce", return_value=False):
            configure_logging(debug=False)

        assert logging.getLogger("bioaf").level == logging.INFO

    def test_cloud_logging_skipped_when_library_missing(self):
        from app.logging_config import configure_logging

        with (
            patch("app.logging_config.is_running_on_gce", return_value=True),
            patch("app.logging_config.cloud_logging", None),
        ):
            configure_logging(debug=False)

        bioaf_logger = logging.getLogger("bioaf")
        handler_types = [type(h).__name__ for h in bioaf_logger.handlers]
        assert "CloudLoggingHandler" not in handler_types
