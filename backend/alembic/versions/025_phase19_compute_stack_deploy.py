"""Phase 19 - Compute stack selection and deployment.

Adds compute-related platform_config keys and upserts K8s-era component_states entries.

Revision ID: 025
Revises: 024
"""

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Seed compute-related platform_config keys
    op.execute("""
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

    # Upsert K8s-era component_states entries
    op.execute("""
        INSERT INTO component_states (component_key, enabled, status, config_json) VALUES
            ('kubernetes_cluster', false, 'disabled', '{}'),
            ('nextflow', false, 'disabled', '{}'),
            ('snakemake', false, 'disabled', '{}'),
            ('jupyterhub', false, 'disabled', '{}'),
            ('rstudio', false, 'disabled', '{}'),
            ('cellxgene', false, 'disabled', '{}'),
            ('qc_dashboard', false, 'disabled', '{}'),
            ('meilisearch', false, 'disabled', '{}')
        ON CONFLICT (component_key) DO NOTHING
    """)

    # Deprecate old SLURM-era entries if they exist
    op.execute("""
        UPDATE component_states
        SET status = 'deprecated'
        WHERE component_key IN ('slurm_cluster', 'filestore_nfs', 'k8s_pipeline_pool', 'k8s_interactive_pool')
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM platform_config
        WHERE key IN (
            'compute_stack', 'compute_deployed', 'gke_cluster_name',
            'gke_cluster_endpoint', 'gke_cluster_ca_cert',
            'k8s_pipeline_machine_type', 'k8s_pipeline_max_nodes',
            'k8s_pipeline_use_spot', 'k8s_interactive_machine_type',
            'k8s_interactive_max_nodes'
        )
    """)

    op.execute("""
        DELETE FROM component_states
        WHERE component_key IN (
            'kubernetes_cluster', 'nextflow', 'snakemake', 'jupyterhub',
            'rstudio', 'cellxgene', 'qc_dashboard', 'meilisearch'
        )
    """)

    # Restore deprecated entries
    op.execute("""
        UPDATE component_states
        SET status = 'disabled'
        WHERE component_key IN ('slurm_cluster', 'filestore_nfs', 'k8s_pipeline_pool', 'k8s_interactive_pool')
          AND status = 'deprecated'
    """)
