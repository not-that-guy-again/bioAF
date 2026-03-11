"""Tests for the GCP credential injection helper (Step 4 - Phase 17).

Tests 8-9 from the spec:
- Test 8: VM default credentials - sets only TF_VAR_project_id/region/zone, no key file
- Test 9: Service account key credentials - writes key to temp file, sets
  GOOGLE_APPLICATION_CREDENTIALS, returns cleanup function
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.services.credential_injector import GCPCredentialInjector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vm_default_config() -> dict:
    return {
        "gcp_credential_source": "vm_default",
        "gcp_project_id": "my-project",
        "gcp_region": "us-central1",
        "gcp_zone": "us-central1-a",
    }


def _sa_key_config(key_json: str) -> dict:
    return {
        "gcp_credential_source": "service_account_key",
        "gcp_project_id": "my-project",
        "gcp_region": "us-central1",
        "gcp_zone": "us-central1-a",
        "gcp_service_account_key": key_json,
    }


FAKE_SA_KEY = json.dumps({
    "type": "service_account",
    "project_id": "my-project",
    "private_key_id": "abc123",
    "client_email": "bioaf@my-project.iam.gserviceaccount.com",
})


# ---------------------------------------------------------------------------
# Test 8: VM default credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vm_default_credential_env_vars():
    """VM default source sets TF_VAR_* env vars, no GOOGLE_APPLICATION_CREDENTIALS."""
    env, cleanup = await GCPCredentialInjector.build_env(config=_vm_default_config())

    assert env.get("TF_VAR_project_id") == "my-project"
    assert env.get("TF_VAR_region") == "us-central1"
    assert env.get("TF_VAR_zone") == "us-central1-a"
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in env


@pytest.mark.asyncio
async def test_vm_default_cleanup_is_noop():
    """VM default source cleanup function does nothing and does not raise."""
    _env, cleanup = await GCPCredentialInjector.build_env(config=_vm_default_config())
    # Should not raise
    await cleanup()


# ---------------------------------------------------------------------------
# Test 9: Service account key credentials
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sa_key_writes_temp_file_and_sets_env():
    """SA key source writes key JSON to a temp file and sets GOOGLE_APPLICATION_CREDENTIALS."""
    env, cleanup = await GCPCredentialInjector.build_env(config=_sa_key_config(FAKE_SA_KEY))

    assert "GOOGLE_APPLICATION_CREDENTIALS" in env
    key_path = Path(env["GOOGLE_APPLICATION_CREDENTIALS"])
    assert key_path.exists()
    assert key_path.read_text() == FAKE_SA_KEY

    # Also sets TF_VAR_ variables
    assert env.get("TF_VAR_project_id") == "my-project"

    # Cleanup removes the file
    await cleanup()
    assert not key_path.exists()


@pytest.mark.asyncio
async def test_sa_key_cleanup_removes_temp_file():
    """Cleanup callable deletes the temp credentials file."""
    env, cleanup = await GCPCredentialInjector.build_env(config=_sa_key_config(FAKE_SA_KEY))
    key_path = Path(env["GOOGLE_APPLICATION_CREDENTIALS"])
    assert key_path.exists()
    await cleanup()
    assert not key_path.exists()


@pytest.mark.asyncio
async def test_missing_sa_key_raises_value_error():
    """Service account source without a key in config raises ValueError."""
    config = _sa_key_config(FAKE_SA_KEY)
    del config["gcp_service_account_key"]

    with pytest.raises(ValueError, match="service_account_key"):
        await GCPCredentialInjector.build_env(config=config)
