"""Tests for K8s namespace setup (spec tests 10-11).

Tests that the compute adapter creates namespace, service account, and role binding,
and skips creation if they already exist.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.compute.kubernetes import KubernetesComputeProvider


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("BIOAF_COMPUTE_MODE", "k8s")
    return KubernetesComputeProvider()


class TestNamespaceSetupCreatesResources:
    @pytest.mark.asyncio
    async def test_creates_namespace_sa_and_rolebinding(self, adapter):
        """Test 10: namespace setup creates namespace, service account, and role binding."""
        mock_core_v1 = MagicMock()
        mock_rbac_v1 = MagicMock()

        # Simulate namespace not found (404)
        from kubernetes.client.rest import ApiException

        mock_core_v1.read_namespace.side_effect = ApiException(status=404)
        mock_core_v1.create_namespace.return_value = MagicMock()
        mock_core_v1.create_namespaced_service_account.return_value = MagicMock()
        mock_rbac_v1.create_namespaced_role_binding.return_value = MagicMock()

        with patch.object(adapter, "_get_k8s_core_client", return_value=mock_core_v1):
            with patch.object(adapter, "_get_k8s_rbac_client", return_value=mock_rbac_v1):
                await adapter.ensure_pipeline_namespace("bioaf-pipelines")

        mock_core_v1.create_namespace.assert_called_once()
        mock_core_v1.create_namespaced_service_account.assert_called_once()
        mock_rbac_v1.create_namespaced_role_binding.assert_called_once()

        # Verify namespace name
        ns_body = mock_core_v1.create_namespace.call_args[1]["body"]
        assert ns_body.metadata.name == "bioaf-pipelines"

        # Verify service account name and namespace
        sa_call = mock_core_v1.create_namespaced_service_account.call_args
        assert sa_call[1]["namespace"] == "bioaf-pipelines"
        assert sa_call[1]["body"].metadata.name == "bioaf-pipeline-runner"


class TestNamespaceSetupSkipsIfExists:
    @pytest.mark.asyncio
    async def test_skips_creation_if_namespace_exists(self, adapter):
        """Test 11: namespace setup skips if resources already exist."""
        mock_core_v1 = MagicMock()
        mock_rbac_v1 = MagicMock()

        # Simulate namespace already exists
        mock_core_v1.read_namespace.return_value = MagicMock()

        with patch.object(adapter, "_get_k8s_core_client", return_value=mock_core_v1):
            with patch.object(adapter, "_get_k8s_rbac_client", return_value=mock_rbac_v1):
                await adapter.ensure_pipeline_namespace("bioaf-pipelines")

        mock_core_v1.create_namespace.assert_not_called()
        mock_core_v1.create_namespaced_service_account.assert_not_called()
        mock_rbac_v1.create_namespaced_role_binding.assert_not_called()
