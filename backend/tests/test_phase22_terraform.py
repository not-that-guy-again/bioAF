"""Tests for Phase 22 Terraform: Artifact Registry resource in notebooks.tf."""

import os


def test_artifact_registry_resource_in_terraform():
    """The notebooks.tf file includes a google_artifact_registry_repository resource."""
    tf_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "terraform", "notebooks.tf"
    )
    assert os.path.exists(tf_path), "terraform/notebooks.tf not found"

    with open(tf_path) as f:
        content = f.read()

    assert "google_artifact_registry_repository" in content
    assert 'repository_id' in content
    assert 'format' in content
    assert '"DOCKER"' in content


def test_artifact_registry_output_in_terraform():
    """The outputs.tf file includes an artifact_registry_repo output."""
    tf_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "terraform", "outputs.tf"
    )
    assert os.path.exists(tf_path), "terraform/outputs.tf not found"

    with open(tf_path) as f:
        content = f.read()

    assert "artifact_registry_repo" in content
