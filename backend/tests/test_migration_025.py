"""Tests for migration 025 - Phase 19 compute stack deployment.

Tests that:
- New platform_config keys exist (compute_stack, compute_deployed, gke_cluster_name,
  gke_cluster_endpoint, gke_cluster_ca_cert, k8s_pipeline_machine_type,
  k8s_pipeline_max_nodes, k8s_pipeline_use_spot, k8s_interactive_machine_type,
  k8s_interactive_max_nodes)
- component_states entries exist for K8s-era components
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_migration_seeds_compute_platform_config_keys(session):
    """Migration 025 inserts compute-related platform_config keys."""
    await session.execute(
        text("""
        INSERT INTO platform_config (key, value) VALUES
            ('compute_stack', 'null'),
            ('compute_deployed', 'false'),
            ('gke_cluster_name', 'null'),
            ('gke_cluster_endpoint', 'null'),
            ('gke_cluster_ca_cert', 'null'),
            ('k8s_pipeline_machine_type', 'n2-highmem-8'),
            ('k8s_pipeline_max_nodes', '20'),
            ('k8s_pipeline_use_spot', 'true'),
            ('k8s_interactive_machine_type', 'n2-standard-4'),
            ('k8s_interactive_max_nodes', '5')
        ON CONFLICT (key) DO NOTHING
        """)
    )
    await session.commit()

    rows = (
        await session.execute(
            text(
                "SELECT key, value FROM platform_config "
                "WHERE key IN ("
                "  'compute_stack', 'compute_deployed', 'gke_cluster_name',"
                "  'gke_cluster_endpoint', 'gke_cluster_ca_cert',"
                "  'k8s_pipeline_machine_type', 'k8s_pipeline_max_nodes',"
                "  'k8s_pipeline_use_spot', 'k8s_interactive_machine_type',"
                "  'k8s_interactive_max_nodes'"
                ") ORDER BY key"
            )
        )
    ).fetchall()

    config = {r[0]: r[1] for r in rows}
    assert len(config) == 10
    assert config["compute_stack"] == "null"
    assert config["compute_deployed"] == "false"
    assert config["gke_cluster_name"] == "null"
    assert config["gke_cluster_endpoint"] == "null"
    assert config["gke_cluster_ca_cert"] == "null"
    assert config["k8s_pipeline_machine_type"] == "n2-highmem-8"
    assert config["k8s_pipeline_max_nodes"] == "20"
    assert config["k8s_pipeline_use_spot"] == "true"
    assert config["k8s_interactive_machine_type"] == "n2-standard-4"
    assert config["k8s_interactive_max_nodes"] == "5"


@pytest.mark.asyncio
async def test_migration_upserts_component_states(session):
    """Migration 025 upserts K8s-era component_states entries."""
    expected_keys = [
        "kubernetes_cluster",
        "nextflow",
        "snakemake",
        "jupyterhub",
        "rstudio",
        "cellxgene",
        "qc_dashboard",
        "meilisearch",
    ]

    for key in expected_keys:
        await session.execute(
            text("""
            INSERT INTO component_states (component_key, enabled, status, config_json)
            VALUES (:key, false, 'disabled', '{}')
            ON CONFLICT (component_key) DO NOTHING
            """).bindparams(key=key)
        )
    await session.commit()

    rows = (
        await session.execute(
            text(
                "SELECT component_key, enabled, status FROM component_states "
                "WHERE component_key = ANY(:keys) ORDER BY component_key"
            ).bindparams(keys=expected_keys)
        )
    ).fetchall()

    found_keys = {r[0] for r in rows}
    for key in expected_keys:
        assert key in found_keys, f"component_states entry for '{key}' should exist"

    for row in rows:
        assert row[1] is False, f"{row[0]} should have enabled=false"
        assert row[2] == "disabled", f"{row[0]} should have status='disabled'"
