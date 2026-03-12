"""Tests for session persistence service (GCS home directory sync)."""

import pytest
from unittest.mock import MagicMock, patch


def test_generate_sync_in_command():
    """Sync-in command includes correct GCS prefix and local directory."""
    from app.services.session_persistence import generate_sync_in_command

    cmd = generate_sync_in_command(
        gcs_prefix="gs://bioaf-working/notebooks/42/",
        local_dir="/home/jovyan",
    )
    assert isinstance(cmd, list)
    joined = " ".join(cmd)
    assert "gsutil" in joined
    assert "rsync" in joined
    assert "gs://bioaf-working/notebooks/42/" in joined
    assert "/home/jovyan" in joined


def test_generate_sync_out_command():
    """Sync-out command includes correct local dir and GCS prefix."""
    from app.services.session_persistence import generate_sync_out_command

    cmd = generate_sync_out_command(
        local_dir="/home/jovyan",
        gcs_prefix="gs://bioaf-working/notebooks/42/",
    )
    assert isinstance(cmd, list)
    joined = " ".join(cmd)
    assert "gsutil" in joined
    assert "rsync" in joined
    assert "/home/jovyan" in joined
    assert "gs://bioaf-working/notebooks/42/" in joined


@pytest.mark.asyncio
async def test_sync_session_executes_in_pod():
    """Sync command is executed in the correct pod via K8s exec."""
    from app.services.session_persistence import sync_session_to_gcs

    mock_core_client = MagicMock()
    mock_stream = MagicMock(return_value="sync complete")

    with (
        patch(
            "app.services.session_persistence._get_k8s_core_client",
            return_value=mock_core_client,
        ),
        patch(
            "kubernetes.stream.stream",
            mock_stream,
        ),
    ):
        await sync_session_to_gcs(
            pod_name="bioaf-notebook-99",
            namespace="bioaf-notebooks",
            gcs_prefix="gs://bioaf-working/notebooks/42/",
            local_dir="/home/jovyan",
        )

    mock_stream.assert_called_once()
    call_args_str = str(mock_stream.call_args)
    assert "bioaf-notebook-99" in call_args_str
    assert "bioaf-notebooks" in call_args_str
