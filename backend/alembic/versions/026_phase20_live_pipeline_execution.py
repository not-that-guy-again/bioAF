"""Phase 20 - Live pipeline execution on GKE.

Adds K8s-specific columns to pipeline_runs and seeds k8s_pipeline_namespace config.

Revision ID: 026
Revises: 025
"""

import sqlalchemy as sa
from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add K8s columns to pipeline_runs
    op.add_column("pipeline_runs", sa.Column("k8s_job_name", sa.String(255), nullable=True))
    op.add_column("pipeline_runs", sa.Column("k8s_namespace", sa.String(100), nullable=True))
    op.add_column("pipeline_runs", sa.Column("k8s_pod_name", sa.String(255), nullable=True))
    op.add_column("pipeline_runs", sa.Column("actual_cost", sa.Numeric(10, 2), nullable=True))

    # Seed k8s_pipeline_namespace platform_config key
    op.execute("""
        INSERT INTO platform_config (key, value) VALUES
            ('k8s_pipeline_namespace', 'bioaf-pipelines')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_column("pipeline_runs", "actual_cost")
    op.drop_column("pipeline_runs", "k8s_pod_name")
    op.drop_column("pipeline_runs", "k8s_namespace")
    op.drop_column("pipeline_runs", "k8s_job_name")

    op.execute("""
        DELETE FROM platform_config WHERE key = 'k8s_pipeline_namespace'
    """)
