"""Tests for the Kubernetes cellxgene adapter.

Covers local mode (deploy/teardown/status) and K8s namespace setup.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.cellxgene.kubernetes import (
    KubernetesCellxgeneProvider,
    _local_instances,
)


@pytest.fixture(autouse=True)
def set_local_mode(monkeypatch):
    monkeypatch.setenv("BIOAF_COMPUTE_MODE", "local")


@pytest.fixture(autouse=True)
def clear_instances():
    _local_instances.clear()
    yield
    _local_instances.clear()


@pytest.fixture
def adapter():
    return KubernetesCellxgeneProvider()


class TestCellxgeneDeploy:
    @pytest.mark.asyncio
    async def test_deploy_returns_publication_id(self, adapter):
        result = await adapter.deploy(42, "gs://bucket/data.h5ad", "My Dataset")
        assert result["publication_id"] == 42

    @pytest.mark.asyncio
    async def test_deploy_returns_running_status(self, adapter):
        result = await adapter.deploy(1, "gs://bucket/data.h5ad", "Dataset")
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_deploy_stores_in_local_instances(self, adapter):
        await adapter.deploy(7, "gs://bucket/data.h5ad", "Dataset")
        assert 7 in _local_instances

    @pytest.mark.asyncio
    async def test_deploy_sets_pod_name(self, adapter):
        result = await adapter.deploy(5, "gs://bucket/data.h5ad", "Dataset")
        assert result["pod_name"] == "cellxgene-5"


class TestCellxgeneTeardown:
    @pytest.mark.asyncio
    async def test_teardown_returns_stopped(self, adapter):
        await adapter.deploy(1, "gs://bucket/data.h5ad", "Dataset")
        result = await adapter.teardown(1)
        assert result["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_teardown_updates_local_store(self, adapter):
        await adapter.deploy(1, "gs://bucket/data.h5ad", "Dataset")
        await adapter.teardown(1)
        assert _local_instances[1]["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_teardown_nonexistent_returns_stopped(self, adapter):
        result = await adapter.teardown(999)
        assert result["status"] == "stopped"


class TestCellxgeneGetStatus:
    @pytest.mark.asyncio
    async def test_status_of_running_instance(self, adapter):
        await adapter.deploy(1, "gs://bucket/data.h5ad", "Dataset")
        result = await adapter.get_status(1)
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_status_of_unknown_instance(self, adapter):
        result = await adapter.get_status(999)
        assert result["status"] == "unknown"


class TestCellxgeneNamespaceSetup:
    @pytest.fixture
    def k8s_adapter(self, monkeypatch):
        monkeypatch.setenv("BIOAF_COMPUTE_MODE", "k8s")
        return KubernetesCellxgeneProvider()

    @pytest.mark.asyncio
    async def test_creates_namespace_sa_and_rolebinding(self, k8s_adapter):
        mock_core_v1 = MagicMock()
        mock_rbac_v1 = MagicMock()

        from kubernetes.client.rest import ApiException

        mock_core_v1.read_namespace.side_effect = ApiException(status=404)
        mock_core_v1.create_namespace.return_value = MagicMock()
        mock_core_v1.create_namespaced_service_account.return_value = MagicMock()
        mock_rbac_v1.create_namespaced_role_binding.return_value = MagicMock()

        with patch.object(k8s_adapter, "_get_k8s_core_client", return_value=mock_core_v1):
            with patch.object(k8s_adapter, "_get_k8s_rbac_client", return_value=mock_rbac_v1):
                await k8s_adapter.ensure_cellxgene_namespace()

        mock_core_v1.create_namespace.assert_called_once()
        mock_core_v1.create_namespaced_service_account.assert_called_once()
        mock_rbac_v1.create_namespaced_role_binding.assert_called_once()

        ns_body = mock_core_v1.create_namespace.call_args[1]["body"]
        assert ns_body.metadata.name == "bioaf-cellxgene"

        sa_call = mock_core_v1.create_namespaced_service_account.call_args
        assert sa_call[1]["namespace"] == "bioaf-cellxgene"
        assert sa_call[1]["body"].metadata.name == "bioaf-cellxgene-runner"

    @pytest.mark.asyncio
    async def test_skips_creation_if_namespace_exists(self, k8s_adapter):
        mock_core_v1 = MagicMock()
        mock_rbac_v1 = MagicMock()

        mock_core_v1.read_namespace.return_value = MagicMock()

        with patch.object(k8s_adapter, "_get_k8s_core_client", return_value=mock_core_v1):
            with patch.object(k8s_adapter, "_get_k8s_rbac_client", return_value=mock_rbac_v1):
                await k8s_adapter.ensure_cellxgene_namespace()

        mock_core_v1.create_namespace.assert_not_called()
        mock_core_v1.create_namespaced_service_account.assert_not_called()
        mock_rbac_v1.create_namespaced_role_binding.assert_not_called()
