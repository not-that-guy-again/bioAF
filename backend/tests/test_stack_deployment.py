"""Tests for the stack deployment service (Phase 19, tests 3-11).

3. test_deploy_stack_requires_gcp_configured
4. test_deploy_stack_requires_terraform_initialized
5. test_deploy_stack_requires_not_already_deployed
6. test_deploy_stack_deploys_storage_then_compute
7. test_deploy_stack_skips_storage_if_already_deployed
8. test_deploy_stack_stores_cluster_config_on_success
9. test_deploy_stack_preserves_storage_on_compute_failure
10. test_teardown_stack_requires_deployed
11. test_teardown_stack_clears_config
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text


async def _set_config(session, key: str, value: str):
    """Helper to set a platform_config key."""
    await session.execute(
        text(
            "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ).bindparams(k=key, v=value)
    )
    await session.flush()


async def _get_config(session, key: str) -> str | None:
    """Helper to read a platform_config key."""
    row = (
        await session.execute(
            text("SELECT value FROM platform_config WHERE key = :k").bindparams(k=key)
        )
    ).fetchone()
    return row[0] if row else None


def _make_progress_event(event_type="apply_complete", message="done", **kwargs):
    """Create a mock TerraformProgressEvent."""
    from app.services.terraform_executor import TerraformProgressEvent

    return TerraformProgressEvent(event_type=event_type, message=message, **kwargs)


# -----------------------------------------------------------------------
# deploy_stack tests
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deploy_stack_requires_gcp_configured(session):
    """deploy_stack raises when gcp_credentials_configured is not true."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "false")
    await _set_config(session, "terraform_initialized", "true")
    await _set_config(session, "compute_deployed", "false")
    await session.commit()

    with pytest.raises(ValueError, match="GCP credentials"):
        async for _ in deploy_stack(session, "kubernetes", user_id=1):
            pass


@pytest.mark.asyncio
async def test_deploy_stack_requires_terraform_initialized(session):
    """deploy_stack raises when terraform_initialized is not true."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "true")
    await _set_config(session, "terraform_initialized", "false")
    await _set_config(session, "compute_deployed", "false")
    await session.commit()

    with pytest.raises(ValueError, match="[Tt]erraform.*initialized"):
        async for _ in deploy_stack(session, "kubernetes", user_id=1):
            pass


@pytest.mark.asyncio
async def test_deploy_stack_requires_not_already_deployed(session):
    """deploy_stack raises when compute_deployed is already true."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "true")
    await _set_config(session, "terraform_initialized", "true")
    await _set_config(session, "compute_deployed", "true")
    await session.commit()

    with pytest.raises(ValueError, match="already deployed"):
        async for _ in deploy_stack(session, "kubernetes", user_id=1):
            pass


@pytest.mark.asyncio
async def test_deploy_stack_deploys_storage_then_compute(session):
    """deploy_stack runs storage module first, then compute module."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "true")
    await _set_config(session, "terraform_initialized", "true")
    await _set_config(session, "compute_deployed", "false")
    await _set_config(session, "storage_deployed", "false")
    await session.commit()

    modules_run = []

    async def mock_run_module(sess, user_id, module_name):
        modules_run.append(module_name)
        yield _make_progress_event(
            "apply_complete",
            f"{module_name} done",
            extra={"outputs": {
                "cluster_name": {"value": "bioaf-test"},
                "cluster_endpoint": {"value": "https://1.2.3.4"},
                "cluster_ca_cert": {"value": "Y2VydA=="},
            }} if module_name == "compute" else {},
        )

    with patch("app.services.stack_deployment._run_module", side_effect=mock_run_module):
        events = []
        async for event in deploy_stack(session, "kubernetes", user_id=1):
            events.append(event)

    assert modules_run == ["storage", "compute"]
    assert any(e.event_type == "stack_complete" for e in events)


@pytest.mark.asyncio
async def test_deploy_stack_skips_storage_if_already_deployed(session):
    """deploy_stack only runs compute module when storage is already deployed."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "true")
    await _set_config(session, "terraform_initialized", "true")
    await _set_config(session, "compute_deployed", "false")
    await _set_config(session, "storage_deployed", "true")
    await session.commit()

    modules_run = []

    async def mock_run_module(sess, user_id, module_name):
        modules_run.append(module_name)
        yield _make_progress_event(
            "apply_complete",
            f"{module_name} done",
            extra={"outputs": {
                "cluster_name": {"value": "bioaf-test"},
                "cluster_endpoint": {"value": "https://1.2.3.4"},
                "cluster_ca_cert": {"value": "Y2VydA=="},
            }},
        )

    with patch("app.services.stack_deployment._run_module", side_effect=mock_run_module):
        events = []
        async for event in deploy_stack(session, "kubernetes", user_id=1):
            events.append(event)

    assert modules_run == ["compute"]


@pytest.mark.asyncio
async def test_deploy_stack_stores_cluster_config_on_success(session):
    """deploy_stack stores GKE config in platform_config after success."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "true")
    await _set_config(session, "terraform_initialized", "true")
    await _set_config(session, "compute_deployed", "false")
    await _set_config(session, "storage_deployed", "true")
    await session.commit()

    async def mock_run_module(sess, user_id, module_name):
        yield _make_progress_event(
            "apply_complete",
            "done",
            extra={"outputs": {
                "cluster_name": {"value": "bioaf-myorg"},
                "cluster_endpoint": {"value": "https://10.0.0.1"},
                "cluster_ca_cert": {"value": "dGVzdC1jZXJ0"},
            }},
        )

    with patch("app.services.stack_deployment._run_module", side_effect=mock_run_module):
        async for _ in deploy_stack(session, "kubernetes", user_id=1):
            pass

    await session.commit()

    assert await _get_config(session, "compute_stack") == "kubernetes"
    assert await _get_config(session, "compute_deployed") == "true"
    assert await _get_config(session, "gke_cluster_name") == "bioaf-myorg"
    assert await _get_config(session, "gke_cluster_endpoint") == "https://10.0.0.1"
    assert await _get_config(session, "gke_cluster_ca_cert") == "dGVzdC1jZXJ0"


@pytest.mark.asyncio
async def test_deploy_stack_preserves_storage_on_compute_failure(session):
    """Storage remains deployed even if compute module fails."""
    from app.services.stack_deployment import deploy_stack

    await _set_config(session, "gcp_credentials_configured", "true")
    await _set_config(session, "terraform_initialized", "true")
    await _set_config(session, "compute_deployed", "false")
    await _set_config(session, "storage_deployed", "false")
    await session.commit()

    call_count = 0

    async def mock_run_module(sess, user_id, module_name):
        nonlocal call_count
        call_count += 1
        if module_name == "storage":
            yield _make_progress_event("apply_complete", "storage done")
        else:
            yield _make_progress_event("apply_error", "compute failed")

    with patch("app.services.stack_deployment._run_module", side_effect=mock_run_module):
        events = []
        async for event in deploy_stack(session, "kubernetes", user_id=1):
            events.append(event)

    await session.commit()

    # Storage should still be marked as deployed (the hook ran for storage)
    assert await _get_config(session, "storage_deployed") == "true"
    assert await _get_config(session, "compute_deployed") == "false"
    assert any(e.event_type == "stack_error" for e in events)


# -----------------------------------------------------------------------
# teardown_stack tests
# -----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_teardown_stack_requires_deployed(session):
    """teardown_stack raises when compute_deployed is false."""
    from app.services.stack_deployment import teardown_stack

    await _set_config(session, "compute_deployed", "false")
    await session.commit()

    with pytest.raises(ValueError, match="not deployed"):
        async for _ in teardown_stack(session, user_id=1):
            pass


@pytest.mark.asyncio
async def test_teardown_stack_clears_config(session):
    """teardown_stack clears GKE config and sets compute_deployed to false."""
    from app.services.stack_deployment import teardown_stack

    await _set_config(session, "compute_deployed", "true")
    await _set_config(session, "compute_stack", "kubernetes")
    await _set_config(session, "gke_cluster_name", "bioaf-myorg")
    await _set_config(session, "gke_cluster_endpoint", "https://10.0.0.1")
    await _set_config(session, "gke_cluster_ca_cert", "dGVzdC1jZXJ0")
    # Insert kubernetes_cluster component_state
    await session.execute(
        text("""
        INSERT INTO component_states (component_key, enabled, status, config_json)
        VALUES ('kubernetes_cluster', true, 'running', '{}')
        ON CONFLICT (component_key) DO UPDATE SET enabled = true, status = 'running'
        """)
    )
    await session.commit()

    async def mock_run_destroy(sess, user_id, module_name):
        yield _make_progress_event("apply_complete", "destroy done")

    with patch("app.services.stack_deployment._run_destroy", side_effect=mock_run_destroy):
        events = []
        async for event in teardown_stack(session, user_id=1):
            events.append(event)

    await session.commit()

    assert await _get_config(session, "compute_deployed") == "false"
    assert await _get_config(session, "gke_cluster_name") == "null"
    assert await _get_config(session, "gke_cluster_endpoint") == "null"
    assert await _get_config(session, "gke_cluster_ca_cert") == "null"

    # kubernetes_cluster component_state should be disabled
    row = (
        await session.execute(
            text("SELECT enabled, status FROM component_states WHERE component_key = 'kubernetes_cluster'")
        )
    ).fetchone()
    assert row is not None
    assert row[0] is False
    assert row[1] == "disabled"
