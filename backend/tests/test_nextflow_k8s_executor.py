"""Tests that Nextflow uses the K8s executor instead of Docker profile.

GKE nodes use containerd, not Docker. Nextflow must use the K8s executor
so each process runs as its own K8s pod rather than trying to spawn
Docker containers inside the pipeline pod.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.compute.kubernetes import KubernetesComputeProvider


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("BIOAF_COMPUTE_MODE", "k8s")
    provider = KubernetesComputeProvider()
    provider._namespace_ready = True
    provider._cluster_config = {
        "gcp_service_account_key": '{"type": "service_account", "project_id": "test"}',
    }
    return provider


def _mock_batch_client():
    mock_batch = MagicMock()
    mock_job = MagicMock()
    mock_job.metadata.name = "bioaf-pipeline-1"
    mock_batch.create_namespaced_job.return_value = mock_job
    return mock_batch


def _mock_core_client():
    return MagicMock()


class TestK8sExecutor:
    def test_command_does_not_include_profile_docker(self):
        """Nextflow command must NOT use -profile docker on GKE."""
        job_spec = {
            "pipeline_source": "https://github.com/nf-core/scrnaseq",
            "pipeline_version": "2.7.1",
            "parameters": {"outdir": "/data/results"},
            "sample_sheet": "sample,fastq_1\nS1,gs://bucket/R1.fastq.gz\n",
        }

        command = KubernetesComputeProvider._build_nextflow_command(job_spec)
        shell_cmd = command[-1]
        assert "-profile docker" not in shell_cmd

    def test_command_references_k8s_config_file(self):
        """Nextflow command should use -c /data/nextflow.config for K8s executor."""
        job_spec = {
            "pipeline_source": "https://github.com/nf-core/scrnaseq",
            "pipeline_version": "2.7.1",
            "parameters": {"outdir": "/data/results"},
            "sample_sheet": "sample,fastq_1\nS1,gs://bucket/R1.fastq.gz\n",
        }

        command = KubernetesComputeProvider._build_nextflow_command(job_spec)
        shell_cmd = command[-1]
        assert "-c /data/nextflow.config" in shell_cmd

    @pytest.mark.asyncio
    async def test_init_container_writes_nextflow_config(self, adapter):
        """An init container must write nextflow.config with K8s executor settings."""
        mock_batch = _mock_batch_client()
        mock_core = _mock_core_client()

        with (
            patch.object(adapter, "_get_k8s_batch_client", return_value=mock_batch),
            patch.object(adapter, "_get_k8s_core_client", return_value=mock_core),
        ):
            await adapter._k8s_submit_job(
                {
                    "run_id": 1,
                    "pipeline_name": "test",
                    "pipeline_source": "https://github.com/nf-core/scrnaseq",
                    "pipeline_version": "2.7.1",
                    "container_image": "nextflow/nextflow:24.04.4",
                    "namespace": "bioaf-pipelines",
                    "input_files": [],
                    "parameters": {},
                    "sample_sheet": "sample,fastq_1\nS1,gs://bucket/R1.fastq.gz\n",
                }
            )

        body = mock_batch.create_namespaced_job.call_args[1]["body"]
        pod_spec = body["spec"]["template"]["spec"]
        init_containers = pod_spec.get("initContainers", [])

        # Find the config-writer init container
        config_writers = [ic for ic in init_containers if ic["name"] == "write-nf-config"]
        assert len(config_writers) == 1, "Expected a write-nf-config init container"

        config_script = config_writers[0]["command"][-1]
        assert "process.executor" in config_script
        assert "'k8s'" in config_script
        assert "bioaf-pipelines" in config_script
        assert "bioaf-pipeline-runner" in config_script

    @pytest.mark.asyncio
    async def test_k8s_config_includes_gcs_credentials(self, adapter):
        """K8s executor config must propagate GCS credentials to spawned pods."""
        mock_batch = _mock_batch_client()
        mock_core = _mock_core_client()

        with (
            patch.object(adapter, "_get_k8s_batch_client", return_value=mock_batch),
            patch.object(adapter, "_get_k8s_core_client", return_value=mock_core),
        ):
            await adapter._k8s_submit_job(
                {
                    "run_id": 1,
                    "pipeline_name": "test",
                    "pipeline_source": "https://github.com/nf-core/scrnaseq",
                    "pipeline_version": "2.7.1",
                    "namespace": "bioaf-pipelines",
                    "input_files": [],
                    "parameters": {},
                    "sample_sheet": "sample,fastq_1\nS1,gs://bucket/R1.fastq.gz\n",
                }
            )

        body = mock_batch.create_namespaced_job.call_args[1]["body"]
        pod_spec = body["spec"]["template"]["spec"]
        init_containers = pod_spec.get("initContainers", [])

        config_writers = [ic for ic in init_containers if ic["name"] == "write-nf-config"]
        config_script = config_writers[0]["command"][-1]

        # K8s executor pods need the GCS secret mounted
        assert "gcp-sa-key" in config_script or "bioaf-gcs-sa-key" in config_script
        assert "GOOGLE_APPLICATION_CREDENTIALS" in config_script

    @pytest.mark.asyncio
    async def test_k8s_config_omits_unsupported_tolerations(self, adapter):
        """Nextflow K8s executor does not support tolerations in k8s.pod."""
        mock_batch = _mock_batch_client()
        mock_core = _mock_core_client()

        with (
            patch.object(adapter, "_get_k8s_batch_client", return_value=mock_batch),
            patch.object(adapter, "_get_k8s_core_client", return_value=mock_core),
        ):
            await adapter._k8s_submit_job(
                {
                    "run_id": 1,
                    "pipeline_name": "test",
                    "pipeline_source": "https://github.com/nf-core/scrnaseq",
                    "pipeline_version": "2.7.1",
                    "namespace": "bioaf-pipelines",
                    "input_files": [],
                    "parameters": {},
                    "sample_sheet": "sample,fastq_1\nS1,gs://bucket/R1.fastq.gz\n",
                }
            )

        body = mock_batch.create_namespaced_job.call_args[1]["body"]
        pod_spec = body["spec"]["template"]["spec"]
        init_containers = pod_spec.get("initContainers", [])

        config_writers = [ic for ic in init_containers if ic["name"] == "write-nf-config"]
        config_script = config_writers[0]["command"][-1]

        # Nextflow doesn't support tolerations or nodeSelector in k8s.pod
        assert "tolerations" not in config_script
        assert "nodeSelector" not in config_script
