"""Tests for the Terraform compute module (Phase 19).

1. test_compute_module_files_exist - Verify main.tf, variables.tf, outputs.tf exist.
2. test_compute_module_creates_cluster_and_pools - Parse HCL and verify expected resources.
"""

from pathlib import Path


COMPUTE_MODULE_DIR = Path(__file__).resolve().parents[2] / "terraform" / "modules" / "compute"


def test_compute_module_files_exist():
    """Verify compute module contains main.tf, variables.tf, and outputs.tf."""
    for filename in ("main.tf", "variables.tf", "outputs.tf"):
        filepath = COMPUTE_MODULE_DIR / filename
        assert filepath.exists(), f"{filename} should exist in terraform/modules/compute/"
        assert filepath.stat().st_size > 0, f"{filename} should not be empty"


def test_compute_module_creates_cluster_and_pools():
    """Parse HCL files and verify they define the expected GKE resources and outputs."""
    main_tf = (COMPUTE_MODULE_DIR / "main.tf").read_text()
    variables_tf = (COMPUTE_MODULE_DIR / "variables.tf").read_text()
    outputs_tf = (COMPUTE_MODULE_DIR / "outputs.tf").read_text()

    # main.tf should define a GKE cluster and two node pools
    assert 'resource "google_container_cluster"' in main_tf, "Should define a GKE cluster resource"
    assert 'resource "google_container_node_pool"' in main_tf, "Should define node pool resources"
    assert "bioaf-pipelines" in main_tf, "Should have a pipelines node pool"
    assert "bioaf-interactive" in main_tf, "Should have an interactive node pool"

    # Workload Identity should be configured
    assert "workload_identity_config" in main_tf, "Should configure Workload Identity"

    # Network policy should be enabled
    assert "network_policy" in main_tf, "Should enable network policy"

    # variables.tf should define expected input variables
    for var_name in (
        "project_id",
        "region",
        "zone",
        "org_slug",
        "k8s_pipeline_machine_type",
        "k8s_pipeline_max_nodes",
        "k8s_pipeline_use_spot",
        "k8s_interactive_machine_type",
        "k8s_interactive_max_nodes",
    ):
        assert f'"{var_name}"' in variables_tf, f"variables.tf should define var {var_name}"

    # outputs.tf should define expected outputs
    for output_name in ("cluster_name", "cluster_endpoint", "cluster_ca_cert"):
        assert f'"{output_name}"' in outputs_tf, f"outputs.tf should define output {output_name}"
