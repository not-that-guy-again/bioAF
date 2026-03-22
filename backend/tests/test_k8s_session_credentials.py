"""Tests for K8s adapter session credential integration.

Verifies that RStudio pods use PAM auth with session credentials
instead of --auth-none=1.
"""

import time

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.adapters.notebooks.kubernetes import KubernetesNotebookProvider


@pytest.fixture
def adapter():
    provider = KubernetesNotebookProvider()
    provider._mode = "k8s"
    provider._namespace_ready = False
    provider._api_client = MagicMock()
    provider._client_created_at = time.monotonic()
    return provider


@pytest.fixture
def mock_k8s_clients():
    mock_core = MagicMock()
    mock_rbac = MagicMock()
    mock_core.read_namespace.return_value = MagicMock()
    mock_pod = MagicMock()
    mock_pod.status.phase = "Running"
    mock_pod.status.conditions = [MagicMock(type="Ready", status="True")]
    mock_core.read_namespaced_pod.return_value = mock_pod
    mock_core.create_namespaced_service.return_value = MagicMock()
    mock_core.create_namespaced_pod.return_value = MagicMock()
    return mock_core, mock_rbac


def _session_spec(session_type="rstudio", session_id=42, user_id=7):
    return {
        "session_type": session_type,
        "session_id": session_id,
        "user_id": user_id,
        "resource_profile": "small",
        "cpu_cores": 2,
        "memory_gb": 4,
        "experiment_id": None,
    }


class TestRStudioSessionCredentials:
    @pytest.mark.asyncio
    async def test_rstudio_no_auth_none(self, adapter, mock_k8s_clients):
        """RStudio pods must NOT use --auth-none=1."""
        mock_core, mock_rbac = mock_k8s_clients
        adapter._get_k8s_core_client = MagicMock(return_value=mock_core)
        adapter._get_k8s_rbac_client = MagicMock(return_value=mock_rbac)
        adapter._poll_session_ready = AsyncMock()

        spec = _session_spec()
        spec["session_credentials"] = {"username": "bmills", "password": "secret123"}
        await adapter._k8s_launch_session(spec)

        pod_body = mock_core.create_namespaced_pod.call_args[1]["body"]
        containers = pod_body["spec"]["containers"]
        cmd_str = " ".join(containers[0].get("command", []))
        assert "--auth-none" not in cmd_str
        assert "--auth-minimum-user-id=0" not in cmd_str

    @pytest.mark.asyncio
    async def test_rstudio_has_user_setup_init_container(self, adapter, mock_k8s_clients):
        """RStudio pods must have an init container that creates the Unix user."""
        mock_core, mock_rbac = mock_k8s_clients
        adapter._get_k8s_core_client = MagicMock(return_value=mock_core)
        adapter._get_k8s_rbac_client = MagicMock(return_value=mock_rbac)
        adapter._poll_session_ready = AsyncMock()

        spec = _session_spec()
        spec["session_credentials"] = {"username": "bmills", "password": "secret123"}
        await adapter._k8s_launch_session(spec)

        pod_body = mock_core.create_namespaced_pod.call_args[1]["body"]
        init_containers = pod_body["spec"].get("initContainers", [])

        # Should have at least 2 init containers: GCS sync + user setup
        assert len(init_containers) >= 2

        # Find the user-setup init container
        user_setup = None
        for ic in init_containers:
            cmd_str = " ".join(ic.get("command", []))
            if "useradd" in cmd_str or "chpasswd" in cmd_str:
                user_setup = ic
                break

        assert user_setup is not None, "No user-setup init container found"
        cmd_str = " ".join(user_setup.get("command", []))
        assert "bmills" in cmd_str
        assert "chpasswd" in cmd_str

    @pytest.mark.asyncio
    async def test_rstudio_user_setup_forces_home_jovyan(self, adapter, mock_k8s_clients):
        """User setup init container should set home to /home/jovyan."""
        mock_core, mock_rbac = mock_k8s_clients
        adapter._get_k8s_core_client = MagicMock(return_value=mock_core)
        adapter._get_k8s_rbac_client = MagicMock(return_value=mock_rbac)
        adapter._poll_session_ready = AsyncMock()

        spec = _session_spec()
        spec["session_credentials"] = {"username": "bmills", "password": "secret123"}
        await adapter._k8s_launch_session(spec)

        pod_body = mock_core.create_namespaced_pod.call_args[1]["body"]
        init_containers = pod_body["spec"].get("initContainers", [])

        user_setup = None
        for ic in init_containers:
            cmd_str = " ".join(ic.get("command", []))
            if "useradd" in cmd_str:
                user_setup = ic
                break

        assert user_setup is not None
        cmd_str = " ".join(user_setup.get("command", []))
        assert "/home/jovyan" in cmd_str

    @pytest.mark.asyncio
    async def test_rstudio_without_credentials_raises(self, adapter, mock_k8s_clients):
        """RStudio launch fails if session_credentials not provided."""
        mock_core, mock_rbac = mock_k8s_clients
        adapter._get_k8s_core_client = MagicMock(return_value=mock_core)
        adapter._get_k8s_rbac_client = MagicMock(return_value=mock_rbac)
        adapter._poll_session_ready = AsyncMock()

        spec = _session_spec()
        # No session_credentials key
        with pytest.raises(ValueError, match="[Ss]ession credentials"):
            await adapter._k8s_launch_session(spec)

    @pytest.mark.asyncio
    async def test_rstudio_no_secure_cookie_key_env(self, adapter, mock_k8s_clients):
        """RStudio pods should not set RSTUDIO_SECURE_COOKIE_KEY when using PAM auth."""
        mock_core, mock_rbac = mock_k8s_clients
        adapter._get_k8s_core_client = MagicMock(return_value=mock_core)
        adapter._get_k8s_rbac_client = MagicMock(return_value=mock_rbac)
        adapter._poll_session_ready = AsyncMock()

        spec = _session_spec()
        spec["session_credentials"] = {"username": "bmills", "password": "secret123"}
        await adapter._k8s_launch_session(spec)

        pod_body = mock_core.create_namespaced_pod.call_args[1]["body"]
        containers = pod_body["spec"]["containers"]
        env_vars = containers[0].get("env", [])
        env_names = [e["name"] for e in env_vars]
        assert "RSTUDIO_SECURE_COOKIE_KEY" not in env_names
