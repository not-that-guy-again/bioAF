"""Unit tests for the GCP credentials validation service.

All GCP API calls are mocked - no real GCP calls are made.
"""

import json
from unittest.mock import MagicMock, patch


from app.services.gcp_config import validate_gcp_credentials


VALID_SA_KEY = json.dumps(
    {
        "type": "service_account",
        "project_id": "my-project",
        "private_key_id": "key123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "bioaf@my-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
)


# ---------------------------------------------------------------------------
# Test 1: All checks skipped when credentials cannot be loaded
# ---------------------------------------------------------------------------
def test_invalid_credentials_skips_all_downstream_checks():
    """When credentials fail to load, all downstream checks are skipped."""
    result = validate_gcp_credentials(
        project_id="my-project",
        credential_source="service_account_key",
        service_account_key="not-valid-json",
    )

    assert result.passed is False
    names = [c.name for c in result.checks]
    assert "credentials_loaded" in names

    cred_check = next(c for c in result.checks if c.name == "credentials_loaded")
    assert cred_check.passed is False

    skipped = [c for c in result.checks if c.status == "skipped"]
    assert len(skipped) >= 4, "Downstream checks must be skipped when creds fail"


# ---------------------------------------------------------------------------
# Test 2: Credential load fails for malformed JSON
# ---------------------------------------------------------------------------
def test_malformed_service_account_key_fails_credential_check():
    """Malformed JSON in the service account key returns a failed credential check."""
    result = validate_gcp_credentials(
        project_id="my-project",
        credential_source="service_account_key",
        service_account_key="{bad json",
    )
    cred_check = next(c for c in result.checks if c.name == "credentials_loaded")
    assert cred_check.passed is False
    assert result.passed is False


# ---------------------------------------------------------------------------
# Test 3: Project not accessible marks downstream checks as skipped
# ---------------------------------------------------------------------------
@patch("app.services.gcp_config.resourcemanager_v3")
@patch("app.services.gcp_config.service_account")
def test_project_not_accessible_skips_downstream(mock_sa, mock_rm):
    """When project access check fails, subsequent checks are skipped."""
    mock_creds = MagicMock()
    mock_sa.Credentials.from_service_account_info.return_value = mock_creds

    mock_rm.ProjectsClient.return_value.get_project.side_effect = Exception("403 Permission denied")

    result = validate_gcp_credentials(
        project_id="my-project",
        credential_source="service_account_key",
        service_account_key=VALID_SA_KEY,
    )

    project_check = next(c for c in result.checks if c.name == "project_accessible")
    assert project_check.passed is False

    skipped = [c for c in result.checks if c.status == "skipped"]
    assert len(skipped) >= 3, "Downstream checks skipped after project failure"
    assert result.passed is False


# ---------------------------------------------------------------------------
# Test 4: Storage API disabled returns failed check, GKE check skipped
# ---------------------------------------------------------------------------
@patch("app.services.gcp_config.storage")
@patch("app.services.gcp_config.resourcemanager_v3")
@patch("app.services.gcp_config.service_account")
def test_storage_api_disabled_marks_check_failed(mock_sa, mock_rm, mock_storage):
    """When Cloud Storage API is not enabled the check fails."""
    mock_creds = MagicMock()
    mock_sa.Credentials.from_service_account_info.return_value = mock_creds
    mock_rm.ProjectsClient.return_value.get_project.return_value = MagicMock()
    # Simulate Storage API disabled by raising an exception on bucket list
    mock_storage.Client.return_value.list_buckets.side_effect = Exception("Cloud Storage API has not been used")

    result = validate_gcp_credentials(
        project_id="my-project",
        credential_source="service_account_key",
        service_account_key=VALID_SA_KEY,
    )

    storage_check = next((c for c in result.checks if c.name == "storage_api_enabled"), None)
    assert storage_check is not None
    assert storage_check.passed is False


# ---------------------------------------------------------------------------
# Test 5: vm_default credential source uses google.auth.default
# ---------------------------------------------------------------------------
@patch("app.services.gcp_config.storage")
@patch("app.services.gcp_config.resourcemanager_v3")
@patch("app.services.gcp_config.google_auth_default")
def test_vm_default_uses_google_auth_default(mock_auth_default, mock_rm, mock_storage):
    """When credential_source is 'vm_default', google.auth.default() is called."""
    mock_creds = MagicMock()
    mock_auth_default.return_value = (mock_creds, "my-project")
    mock_rm.ProjectsClient.return_value.get_project.return_value = MagicMock()
    mock_storage.Client.return_value.list_buckets.return_value = []

    validate_gcp_credentials(
        project_id="my-project",
        credential_source="vm_default",
        service_account_key=None,
    )

    mock_auth_default.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: All checks pass when GCP APIs respond correctly
# ---------------------------------------------------------------------------
@patch("app.services.gcp_config.storage")
@patch("app.services.gcp_config.resourcemanager_v3")
@patch("app.services.gcp_config.service_account")
def test_all_checks_pass_with_valid_credentials(mock_sa, mock_rm, mock_storage):
    """When all GCP API calls succeed, all checks pass and result.passed is True."""
    mock_creds = MagicMock()
    mock_sa.Credentials.from_service_account_info.return_value = mock_creds
    mock_rm.ProjectsClient.return_value.get_project.return_value = MagicMock()
    mock_storage.Client.return_value.list_buckets.return_value = []

    result = validate_gcp_credentials(
        project_id="my-project",
        credential_source="service_account_key",
        service_account_key=VALID_SA_KEY,
    )

    assert result.passed is True
    for check in result.checks:
        assert check.passed is True, f"Check {check.name!r} should have passed"
        assert check.status != "skipped"
