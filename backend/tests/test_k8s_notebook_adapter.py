"""Tests for the Kubernetes notebook adapter in local mode."""

import pytest

from app.adapters.notebooks.kubernetes import KubernetesNotebookProvider, _local_sessions


@pytest.fixture(autouse=True)
def set_local_mode(monkeypatch):
    monkeypatch.setenv("BIOAF_COMPUTE_MODE", "local")


@pytest.fixture(autouse=True)
def clear_sessions():
    _local_sessions.clear()
    yield
    _local_sessions.clear()


@pytest.fixture
def adapter():
    return KubernetesNotebookProvider()


class TestNotebookLaunchSession:
    @pytest.mark.asyncio
    async def test_launch_returns_session_id(self, adapter):
        result = await adapter.launch_session({"session_type": "jupyter", "resource_profile": "small"})
        assert "session_id" in result
        assert result["session_id"].startswith("local-")

    @pytest.mark.asyncio
    async def test_launch_returns_running_status(self, adapter):
        result = await adapter.launch_session({"session_type": "jupyter"})
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_launch_returns_url(self, adapter):
        result = await adapter.launch_session({"session_type": "jupyter"})
        assert "url" in result
        assert "8888" in result["url"]

    @pytest.mark.asyncio
    async def test_launch_rstudio_url(self, adapter):
        result = await adapter.launch_session({"session_type": "rstudio"})
        assert "8787" in result["url"]

    @pytest.mark.asyncio
    async def test_launch_stores_in_local_sessions(self, adapter):
        result = await adapter.launch_session({"session_type": "jupyter"})
        assert result["session_id"] in _local_sessions


class TestNotebookTerminateSession:
    @pytest.mark.asyncio
    async def test_terminate_updates_status(self, adapter):
        launched = await adapter.launch_session({"session_type": "jupyter"})
        result = await adapter.terminate_session(launched["session_id"])
        assert result["status"] == "stopped"
        assert "stopped_at" in result

    @pytest.mark.asyncio
    async def test_terminate_updates_local_store(self, adapter):
        launched = await adapter.launch_session({"session_type": "jupyter"})
        await adapter.terminate_session(launched["session_id"])
        assert _local_sessions[launched["session_id"]]["status"] == "stopped"


class TestNotebookSessionStatus:
    @pytest.mark.asyncio
    async def test_status_of_running_session(self, adapter):
        launched = await adapter.launch_session({"session_type": "jupyter"})
        result = await adapter.get_session_status(launched["session_id"])
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_status_of_unknown_session(self, adapter):
        result = await adapter.get_session_status("nonexistent-id")
        assert result["status"] == "unknown"


class TestNotebookListSessions:
    @pytest.mark.asyncio
    async def test_list_empty(self, adapter):
        result = await adapter.list_sessions()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_after_launch(self, adapter):
        await adapter.launch_session({"session_type": "jupyter"})
        await adapter.launch_session({"session_type": "rstudio"})
        result = await adapter.list_sessions()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_with_type_filter(self, adapter):
        await adapter.launch_session({"session_type": "jupyter"})
        await adapter.launch_session({"session_type": "rstudio"})
        result = await adapter.list_sessions({"session_type": "jupyter"})
        assert len(result) == 1
        assert result[0]["session_type"] == "jupyter"


class TestNotebookConnectionCommand:
    @pytest.mark.asyncio
    async def test_connection_command_format(self, adapter):
        cmd = await adapter.get_connection_command("abc123")
        assert "kubectl exec" in cmd
        assert "bioaf-interactive" in cmd
        assert "notebook-abc123" in cmd
