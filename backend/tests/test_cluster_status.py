"""Tests for cluster status (Phase 19, tests 12-13).

12. test_get_cluster_status_when_not_deployed
13. test_get_cluster_status_returns_pool_info
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text


async def _set_config(session, key: str, value: str):
    await session.execute(
        text(
            "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ).bindparams(k=key, v=value)
    )
    await session.flush()


@pytest.mark.asyncio
async def test_get_cluster_status_when_not_deployed(session):
    """get_cluster_status returns None cluster when not deployed."""
    from app.services.stack_deployment import get_cluster_status

    await _set_config(session, "compute_deployed", "false")
    await session.commit()

    result = await get_cluster_status(session)
    assert result is not None
    assert result.compute_deployed is False
    assert result.cluster is None


@pytest.mark.asyncio
async def test_get_cluster_status_returns_pool_info(session):
    """get_cluster_status returns pool info when deployed with mocked GKE API."""
    from app.services.stack_deployment import get_cluster_status

    await _set_config(session, "compute_deployed", "true")
    await _set_config(session, "compute_stack", "kubernetes")
    await _set_config(session, "storage_deployed", "true")
    await _set_config(session, "gke_cluster_name", "bioaf-test")
    await _set_config(session, "gke_cluster_endpoint", "https://10.0.0.1")
    await _set_config(session, "gke_cluster_ca_cert", "dGVzdA==")
    await _set_config(session, "gcp_project_id", "my-project")
    await _set_config(session, "gcp_zone", "us-central1-a")
    await session.commit()

    # Mock the GKE API client
    mock_cluster = MagicMock()
    mock_cluster.name = "bioaf-test"
    mock_cluster.status = 2  # RUNNING
    mock_cluster.current_node_count = 0

    mock_pipeline_pool = MagicMock()
    mock_pipeline_pool.name = "bioaf-pipelines"
    mock_pipeline_pool.config.machine_type = "n2-highmem-8"
    mock_pipeline_pool.autoscaling.min_node_count = 0
    mock_pipeline_pool.autoscaling.max_node_count = 20
    mock_pipeline_pool.initial_node_count = 0
    mock_pipeline_pool.config.spot = True
    mock_pipeline_pool.status = 2  # RUNNING

    mock_interactive_pool = MagicMock()
    mock_interactive_pool.name = "bioaf-interactive"
    mock_interactive_pool.config.machine_type = "n2-standard-4"
    mock_interactive_pool.autoscaling.min_node_count = 0
    mock_interactive_pool.autoscaling.max_node_count = 5
    mock_interactive_pool.initial_node_count = 0
    mock_interactive_pool.config.spot = False
    mock_interactive_pool.status = 2  # RUNNING

    mock_cluster.node_pools = [mock_pipeline_pool, mock_interactive_pool]

    mock_client = MagicMock()
    mock_client.get_cluster.return_value = mock_cluster

    with patch("app.services.stack_deployment._get_gke_client", return_value=mock_client):
        result = await get_cluster_status(session)

    assert result.compute_deployed is True
    assert result.compute_stack == "kubernetes"
    assert result.cluster is not None
    assert result.cluster.cluster_name == "bioaf-test"
    assert result.cluster.status == "RUNNING"
    assert result.cluster.pipeline_pool.name == "bioaf-pipelines"
    assert result.cluster.pipeline_pool.machine_type == "n2-highmem-8"
    assert result.cluster.pipeline_pool.max_nodes == 20
    assert result.cluster.pipeline_pool.spot is True
    assert result.cluster.interactive_pool.name == "bioaf-interactive"
    assert result.cluster.interactive_pool.machine_type == "n2-standard-4"
    assert result.cluster.interactive_pool.max_nodes == 5
    assert result.cluster.interactive_pool.spot is False
