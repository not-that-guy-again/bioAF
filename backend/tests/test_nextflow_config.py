"""Tests for Nextflow config generator (spec test 24).

Tests that the generator produces valid config with correct executor,
namespace, and GCS paths.
"""


from app.services.nextflow_config import generate_nextflow_config


class TestGenerateNextflowConfig:
    def test_generates_valid_config(self):
        """Test 24: generates valid Nextflow config with K8s executor."""
        config = generate_nextflow_config(org_slug="demo", namespace="bioaf-pipelines")

        assert "k8s" in config
        assert "bioaf-pipelines" in config
        assert "bioaf-pipeline-runner" in config
        assert "gs://bioaf-results-demo/" in config
        assert "docker.enabled" in config

    def test_uses_custom_namespace(self):
        """Config reflects the provided namespace."""
        config = generate_nextflow_config(org_slug="acme", namespace="custom-ns")

        assert "custom-ns" in config
        assert "gs://bioaf-results-acme/" in config

    def test_contains_profile_block(self):
        """Config wraps settings in a profiles block."""
        config = generate_nextflow_config(org_slug="demo", namespace="bioaf-pipelines")

        assert "profiles" in config
        assert "bioaf_k8s" in config
