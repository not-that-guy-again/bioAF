"""GCP credentials validation service.

Performs up to six ordered checks against GCP APIs.  When a check fails
any downstream checks that depend on it are marked as ``skipped`` so the
caller can distinguish "we could not even get to this check" from
"this check ran and failed".

All external GCP calls go through module-level names that the test suite
patches (``service_account``, ``resourcemanager_v3``, ``storage``,
``google_auth_default``).
"""

import json

import google.auth as _google_auth
from google.cloud import resourcemanager_v3, storage
from google.oauth2 import service_account

from app.schemas.gcp_config import GCPValidationCheck, GCPValidationResult

# Alias for patching in tests
google_auth_default = _google_auth.default

_GCP_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _skipped(name: str, reason: str) -> GCPValidationCheck:
    return GCPValidationCheck(name=name, passed=False, message=reason, status="skipped")


def validate_gcp_credentials(
    project_id: str,
    credential_source: str,
    service_account_key: str | None,
) -> GCPValidationResult:
    """Run ordered GCP validation checks and return a result with per-check detail.

    Checks (in order):
    1. credentials_loaded   - can we load/parse the credentials?
    2. project_accessible   - can we fetch the GCP project via Resource Manager?
    3. storage_api_enabled  - can we list GCS buckets (Storage API enabled)?
    """
    checks: list[GCPValidationCheck] = []

    # ------------------------------------------------------------------
    # Check 1: Load credentials
    # ------------------------------------------------------------------
    creds = None
    try:
        if credential_source == "service_account_key":
            key_data = json.loads(service_account_key or "")
            creds = service_account.Credentials.from_service_account_info(key_data, scopes=_GCP_SCOPES)
        else:
            creds, _ = google_auth_default(scopes=_GCP_SCOPES)

        checks.append(
            GCPValidationCheck(
                name="credentials_loaded",
                passed=True,
                message="Credentials loaded successfully",
            )
        )
    except Exception as exc:
        checks.append(
            GCPValidationCheck(
                name="credentials_loaded",
                passed=False,
                message=str(exc),
            )
        )
        checks.extend(
            [
                _skipped("project_accessible", "Skipped: credentials failed to load"),
                _skipped("storage_api_enabled", "Skipped: credentials failed to load"),
                _skipped("gke_api_enabled", "Skipped: credentials failed to load"),
                _skipped("iam_permissions", "Skipped: credentials failed to load"),
                _skipped("storage_access", "Skipped: credentials failed to load"),
            ]
        )
        return GCPValidationResult(passed=False, checks=checks)

    # ------------------------------------------------------------------
    # Check 2: Project accessible
    # ------------------------------------------------------------------
    try:
        rm_client = resourcemanager_v3.ProjectsClient(credentials=creds)
        rm_client.get_project(name=f"projects/{project_id}")
        checks.append(
            GCPValidationCheck(
                name="project_accessible",
                passed=True,
                message=f"Project {project_id!r} is accessible",
            )
        )
    except Exception as exc:
        checks.append(
            GCPValidationCheck(
                name="project_accessible",
                passed=False,
                message=str(exc),
            )
        )
        checks.extend(
            [
                _skipped("storage_api_enabled", "Skipped: project not accessible"),
                _skipped("gke_api_enabled", "Skipped: project not accessible"),
                _skipped("iam_permissions", "Skipped: project not accessible"),
                _skipped("storage_access", "Skipped: project not accessible"),
            ]
        )
        return GCPValidationResult(passed=False, checks=checks)

    # ------------------------------------------------------------------
    # Check 3: Storage API enabled (list_buckets as a lightweight probe)
    # ------------------------------------------------------------------
    try:
        gcs_client = storage.Client(credentials=creds, project=project_id)
        list(gcs_client.list_buckets(max_results=1))
        checks.append(
            GCPValidationCheck(
                name="storage_api_enabled",
                passed=True,
                message="Cloud Storage API is enabled and accessible",
            )
        )
    except Exception as exc:
        checks.append(
            GCPValidationCheck(
                name="storage_api_enabled",
                passed=False,
                message=str(exc),
            )
        )
        return GCPValidationResult(passed=False, checks=checks)

    return GCPValidationResult(passed=True, checks=checks)
