"""Tests for sheets_reader_sa_service credential loading and SA hardening.

Covers:
- _load_primary_credentials reads gcp_bootstrap_sa_email first, falls back to
  the legacy gcp_service_account_email.
- create_reader_sa surfaces a clear error when keys.create fails because the
  org policy disables service-account-key creation.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import sheets_reader_sa_service


def test_load_primary_credentials_prefers_bootstrap_sa_email():
    """vm_default + gcp_bootstrap_sa_email targets the new key."""
    config = {
        "gcp_credential_source": "vm_default",
        "gcp_project_id": "my-project",
        "gcp_bootstrap_sa_email": "bioaf-bootstrap@my-project.iam.gserviceaccount.com",
        "gcp_service_account_email": "legacy-sa@my-project.iam.gserviceaccount.com",
    }
    fake_source = MagicMock(name="adc")
    with (
        patch("google.auth.default", return_value=(fake_source, "my-project")),
        patch(
            "google.auth.impersonated_credentials.Credentials"
        ) as imp_cls,
    ):
        sheets_reader_sa_service._load_primary_credentials(config)
        imp_cls.assert_called_once()
        assert (
            imp_cls.call_args.kwargs["target_principal"]
            == "bioaf-bootstrap@my-project.iam.gserviceaccount.com"
        )


def test_load_primary_credentials_falls_back_to_service_account_email():
    """Existing installs without the new key still impersonate via legacy field."""
    config = {
        "gcp_credential_source": "vm_default",
        "gcp_project_id": "my-project",
        "gcp_service_account_email": "legacy-sa@my-project.iam.gserviceaccount.com",
    }
    fake_source = MagicMock(name="adc")
    with (
        patch("google.auth.default", return_value=(fake_source, "my-project")),
        patch(
            "google.auth.impersonated_credentials.Credentials"
        ) as imp_cls,
    ):
        sheets_reader_sa_service._load_primary_credentials(config)
        assert (
            imp_cls.call_args.kwargs["target_principal"]
            == "legacy-sa@my-project.iam.gserviceaccount.com"
        )


def test_load_primary_credentials_raw_adc_when_no_email():
    config = {
        "gcp_credential_source": "vm_default",
        "gcp_project_id": "my-project",
    }
    fake_source = MagicMock(name="adc")
    with (
        patch("google.auth.default", return_value=(fake_source, "my-project")),
        patch(
            "google.auth.impersonated_credentials.Credentials"
        ) as imp_cls,
    ):
        creds, project = sheets_reader_sa_service._load_primary_credentials(config)
        imp_cls.assert_not_called()
        assert creds is fake_source
        assert project == "my-project"


def test_gcp_keys_constant_includes_bootstrap_sa_email():
    """The list of keys SELECTed by sheets reader includes the new bootstrap field."""
    assert "gcp_bootstrap_sa_email" in sheets_reader_sa_service._GCP_KEYS
    assert "gcp_service_account_email" in sheets_reader_sa_service._GCP_KEYS


def test_friendly_error_for_org_policy_key_creation_block():
    """When keys.create fails with the org-policy precondition, surface a clear message."""

    sample_error = (
        "FailedPrecondition: 400 Key creation is not allowed on this service "
        "account. constraints/iam.disableServiceAccountKeyCreation"
    )
    msg = sheets_reader_sa_service._format_keys_create_error(Exception(sample_error))
    assert "Sheets integration is not available" in msg
    assert "iam.disableServiceAccountKeyCreation" in msg


def test_format_keys_create_error_passthrough_for_unrelated():
    """Unrelated key-creation errors propagate their original message."""

    err = Exception("boom: something else broke")
    msg = sheets_reader_sa_service._format_keys_create_error(err)
    assert "boom: something else broke" in msg
