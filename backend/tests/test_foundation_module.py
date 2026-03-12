"""Tests for the Terraform foundation module files (Step 3 - Phase 17).

Verifies that the required HCL files exist in terraform/modules/foundation/
and contain the expected resource definitions.
"""

from pathlib import Path


# Project root is two levels above backend/
REPO_ROOT = Path(__file__).parent.parent.parent
FOUNDATION_DIR = REPO_ROOT / "terraform" / "modules" / "foundation"


def test_foundation_main_tf_exists():
    """terraform/modules/foundation/main.tf must exist."""
    assert (FOUNDATION_DIR / "main.tf").exists()


def test_foundation_variables_tf_exists():
    """terraform/modules/foundation/variables.tf must exist."""
    assert (FOUNDATION_DIR / "variables.tf").exists()


def test_foundation_outputs_tf_exists():
    """terraform/modules/foundation/outputs.tf must exist."""
    assert (FOUNDATION_DIR / "outputs.tf").exists()


def test_foundation_main_contains_gcs_bucket():
    """main.tf must define a google_storage_bucket resource for Terraform state."""
    content = (FOUNDATION_DIR / "main.tf").read_text()
    assert "google_storage_bucket" in content


def test_foundation_main_contains_required_providers():
    """main.tf must declare a terraform block with required_providers."""
    content = (FOUNDATION_DIR / "main.tf").read_text()
    assert "required_providers" in content


def test_foundation_variables_tf_defines_project_id():
    """variables.tf must define a project_id variable."""
    content = (FOUNDATION_DIR / "variables.tf").read_text()
    assert 'variable "project_id"' in content


def test_foundation_variables_tf_defines_state_bucket_name():
    """variables.tf must define a state_bucket_name variable."""
    content = (FOUNDATION_DIR / "variables.tf").read_text()
    assert "state_bucket_name" in content


def test_foundation_outputs_tf_defines_state_bucket_name():
    """outputs.tf must output the state bucket name."""
    content = (FOUNDATION_DIR / "outputs.tf").read_text()
    assert "state_bucket_name" in content


def test_storage_module_gitkeep_exists():
    """terraform/modules/storage/.gitkeep must exist as a placeholder."""
    assert (REPO_ROOT / "terraform" / "modules" / "storage" / ".gitkeep").exists()


def test_compute_module_gitkeep_exists():
    """terraform/modules/compute/.gitkeep must exist as a placeholder."""
    assert (REPO_ROOT / "terraform" / "modules" / "compute" / ".gitkeep").exists()
