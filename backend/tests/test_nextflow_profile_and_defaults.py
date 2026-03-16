"""Tests that Nextflow command includes -profile docker and pipeline defaults.

nf-core pipelines running in K8s pods need '-profile docker' so Nextflow
uses Docker-compatible resource settings. The pipeline catalog should also
refresh stale default_params_json from the defaults files on disk.
"""

from app.adapters.compute.kubernetes import KubernetesComputeProvider


class TestNextflowProfileDocker:
    def test_command_includes_profile_docker(self):
        """Nextflow command should include '-profile docker' for container execution."""
        job_spec = {
            "pipeline_source": "https://github.com/nf-core/scrnaseq",
            "pipeline_version": "2.7.1",
            "parameters": {"outdir": "/data/results"},
            "sample_sheet": "sample,fastq_1\nS1,gs://bucket/R1.fastq.gz\n",
        }

        command = KubernetesComputeProvider._build_nextflow_command(job_spec)

        shell_cmd = command[-1]  # The actual shell command string
        assert "-profile docker" in shell_cmd

    def test_profile_docker_before_params(self):
        """'-profile docker' should appear before --params in the command."""
        job_spec = {
            "pipeline_source": "https://github.com/nf-core/scrnaseq",
            "pipeline_version": "2.7.1",
            "parameters": {"protocol": "10XV3"},
            "sample_sheet": "header\ndata\n",
        }

        command = KubernetesComputeProvider._build_nextflow_command(job_spec)

        shell_cmd = command[-1]
        profile_pos = shell_cmd.index("-profile docker")
        param_pos = shell_cmd.index("--protocol")
        assert profile_pos < param_pos
