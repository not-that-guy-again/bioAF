"""Tests for the BioAF Adapter Layer (BAL) - base classes, stubs, and registry."""

import pytest

from app.adapters.base import ComputeProvider, NotebookProvider, StorageProvider
from app.adapters.compute.slurm import SlurmComputeProvider
from app.adapters.notebooks.slurm import SlurmNotebookProvider
from app.adapters.storage.nfs import NfsStorageProvider
from app.adapters import registry


# -- Abstract base class tests --


class TestAbstractBaseClasses:
    def test_compute_provider_cannot_be_instantiated(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ComputeProvider()  # type: ignore[abstract]

    def test_storage_provider_cannot_be_instantiated(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            StorageProvider()  # type: ignore[abstract]

    def test_notebook_provider_cannot_be_instantiated(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            NotebookProvider()  # type: ignore[abstract]


# -- SLURM/NFS stub tests --


class TestSlurmStubs:
    @pytest.fixture
    def slurm_compute(self):
        return SlurmComputeProvider()

    @pytest.fixture
    def slurm_notebook(self):
        return SlurmNotebookProvider()

    @pytest.mark.asyncio
    async def test_submit_job_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.submit_job({})

    @pytest.mark.asyncio
    async def test_cancel_job_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.cancel_job("123")

    @pytest.mark.asyncio
    async def test_get_job_status_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.get_job_status("123")

    @pytest.mark.asyncio
    async def test_list_jobs_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.list_jobs()

    @pytest.mark.asyncio
    async def test_get_job_logs_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.get_job_logs("123")

    @pytest.mark.asyncio
    async def test_get_cluster_status_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.get_cluster_status()

    @pytest.mark.asyncio
    async def test_get_cluster_metrics_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.get_cluster_metrics()

    @pytest.mark.asyncio
    async def test_get_cost_estimate_raises(self, slurm_compute):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_compute.get_cost_estimate({})

    @pytest.mark.asyncio
    async def test_notebook_launch_raises(self, slurm_notebook):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_notebook.launch_session({})

    @pytest.mark.asyncio
    async def test_notebook_terminate_raises(self, slurm_notebook):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_notebook.terminate_session("123")

    @pytest.mark.asyncio
    async def test_notebook_status_raises(self, slurm_notebook):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_notebook.get_session_status("123")

    @pytest.mark.asyncio
    async def test_notebook_list_raises(self, slurm_notebook):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_notebook.list_sessions()

    @pytest.mark.asyncio
    async def test_notebook_connection_raises(self, slurm_notebook):
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await slurm_notebook.get_connection_command("123")


class TestNfsStubs:
    @pytest.fixture
    def nfs_storage(self):
        return NfsStorageProvider()

    @pytest.mark.asyncio
    async def test_resolve_input_path_raises(self, nfs_storage):
        with pytest.raises(NotImplementedError, match="NFS storage backend coming soon"):
            await nfs_storage.resolve_input_path({})

    @pytest.mark.asyncio
    async def test_resolve_output_path_raises(self, nfs_storage):
        with pytest.raises(NotImplementedError, match="NFS storage backend coming soon"):
            await nfs_storage.resolve_output_path({}, "file.h5ad")

    @pytest.mark.asyncio
    async def test_stage_inputs_raises(self, nfs_storage):
        with pytest.raises(NotImplementedError, match="NFS storage backend coming soon"):
            await nfs_storage.stage_inputs([], "/tmp/work")

    @pytest.mark.asyncio
    async def test_collect_outputs_raises(self, nfs_storage):
        with pytest.raises(NotImplementedError, match="NFS storage backend coming soon"):
            await nfs_storage.collect_outputs("/tmp/work", {})

    @pytest.mark.asyncio
    async def test_get_storage_metrics_raises(self, nfs_storage):
        with pytest.raises(NotImplementedError, match="NFS storage backend coming soon"):
            await nfs_storage.get_storage_metrics()


# -- Registry tests --


class TestAdapterRegistry:
    def setup_method(self):
        registry.reset_registry()

    def teardown_method(self):
        registry.reset_registry()

    def test_registry_returns_k8s_adapters_for_kubernetes(self):
        from app.adapters.compute.kubernetes import KubernetesComputeProvider
        from app.adapters.notebooks.kubernetes import KubernetesNotebookProvider
        from app.adapters.storage.gcs import GcsStorageProvider

        registry.initialize_adapters_sync("kubernetes")

        assert isinstance(registry.get_compute_adapter(), KubernetesComputeProvider)
        assert isinstance(registry.get_storage_adapter(), GcsStorageProvider)
        assert isinstance(registry.get_notebook_adapter(), KubernetesNotebookProvider)

    def test_registry_returns_slurm_adapters_for_slurm(self):
        registry.initialize_adapters_sync("slurm")

        assert isinstance(registry.get_compute_adapter(), SlurmComputeProvider)
        assert isinstance(registry.get_storage_adapter(), NfsStorageProvider)
        assert isinstance(registry.get_notebook_adapter(), SlurmNotebookProvider)

    def test_registry_raises_for_unknown_stack(self):
        with pytest.raises(ValueError, match="Unknown compute_stack 'hpc_magic'"):
            registry.initialize_adapters_sync("hpc_magic")

    def test_registry_raises_when_not_initialized(self):
        with pytest.raises(RuntimeError, match="Adapter registry not initialized"):
            registry.get_compute_adapter()

        with pytest.raises(RuntimeError, match="Adapter registry not initialized"):
            registry.get_storage_adapter()

        with pytest.raises(RuntimeError, match="Adapter registry not initialized"):
            registry.get_notebook_adapter()

    def test_reset_clears_adapters(self):
        registry.initialize_adapters_sync("kubernetes")
        assert registry.get_compute_adapter() is not None

        registry.reset_registry()
        with pytest.raises(RuntimeError, match="Adapter registry not initialized"):
            registry.get_compute_adapter()


# -- get_job_progress tests --


class TestGetJobProgress:
    """Tests for ComputeProvider.get_job_progress() method."""

    @pytest.mark.asyncio
    async def test_slurm_get_job_progress_raises(self):
        """SLURM stub raises NotImplementedError for get_job_progress."""
        provider = SlurmComputeProvider()
        with pytest.raises(NotImplementedError, match="SLURM compute backend coming soon"):
            await provider.get_job_progress("job-123")

    @pytest.mark.asyncio
    async def test_k8s_local_returns_progress_structure(self):
        """K8s local mode returns a valid normalized progress dict."""
        from app.adapters.compute.kubernetes import KubernetesComputeProvider

        provider = KubernetesComputeProvider()
        result = await provider.get_job_progress("local-abc123")

        assert "percent_complete" in result
        assert "processes" in result
        assert isinstance(result["percent_complete"], (int, float))
        assert isinstance(result["processes"], list)

    @pytest.mark.asyncio
    async def test_k8s_local_progress_has_process_fields(self):
        """K8s local mode progress processes have required fields."""
        from app.adapters.compute.kubernetes import KubernetesComputeProvider

        provider = KubernetesComputeProvider()
        result = await provider.get_job_progress("local-abc123")

        for proc in result["processes"]:
            assert "name" in proc
            assert "status" in proc

    @pytest.mark.asyncio
    async def test_abc_requires_get_job_progress(self):
        """ComputeProvider subclass missing get_job_progress cannot instantiate."""

        class IncompleteProvider(ComputeProvider):
            async def submit_job(self, job_spec: dict) -> dict:
                return {}

            async def cancel_job(self, job_id: str) -> dict:
                return {}

            async def get_job_status(self, job_id: str) -> dict:
                return {}

            async def list_jobs(self, filters: dict | None = None) -> list[dict]:
                return []

            async def get_job_logs(self, job_id: str) -> str:
                return ""

            async def get_cluster_status(self) -> dict:
                return {}

            async def get_cluster_metrics(self) -> dict:
                return {}

            async def get_cost_estimate(self, job_spec: dict) -> dict:
                return {}

            async def get_connection_command(self, job_id: str) -> str:
                return ""

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteProvider()  # type: ignore[abstract]
