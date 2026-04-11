"""Logging configuration with automatic GCE Cloud Logging detection.

On GCE instances, attaches a Google Cloud Logging handler so logs
appear in the Cloud Console alongside the standard stdout handler.
Non-GCE environments get stdout only -- no configuration required.
"""

import logging
import sys
import urllib.request

try:
    import google.cloud.logging as cloud_logging
except ImportError:  # pragma: no cover
    cloud_logging = None  # type: ignore[assignment]

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_GCE_METADATA_URL = "http://169.254.169.254/computeMetadata/v1/project/project-id"
_METADATA_HEADERS = {"Metadata-Flavor": "Google"}


def is_running_on_gce() -> bool:
    """Return True if the process is running on a GCE instance."""
    try:
        req = urllib.request.Request(_GCE_METADATA_URL, headers=_METADATA_HEADERS)
        with urllib.request.urlopen(req, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_gce_project_id() -> str:
    """Fetch the GCP project ID from the GCE metadata server."""
    req = urllib.request.Request(_GCE_METADATA_URL, headers=_METADATA_HEADERS)
    with urllib.request.urlopen(req, timeout=2) as resp:
        return resp.read().decode().strip()


def configure_logging(*, debug: bool) -> None:
    """Set up the ``bioaf`` logger with stdout and optional Cloud Logging.

    Cloud Logging is enabled automatically when running on GCE.
    """
    bioaf_logger = logging.getLogger("bioaf")
    bioaf_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    bioaf_logger.handlers.clear()

    # Stdout -- always present so ./bioaf logs keeps working
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    bioaf_logger.addHandler(stdout_handler)

    # Cloud Logging -- auto-enabled on GCE
    if is_running_on_gce() and cloud_logging is not None:
        try:
            project_id = get_gce_project_id()
            client = cloud_logging.Client(project=project_id)
            cloud_handler = client.get_default_handler()
            cloud_handler.setLevel(logging.DEBUG if debug else logging.INFO)
            bioaf_logger.addHandler(cloud_handler)
            bioaf_logger.info("Cloud Logging enabled (project=%s)", project_id)
        except Exception as exc:
            bioaf_logger.warning("Cloud Logging unavailable, stdout only: %s", exc)
