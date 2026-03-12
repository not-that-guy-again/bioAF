"""Phase 22 - Live notebook sessions on GKE.

Adds K8s-related columns to notebook_sessions and seeds
platform_config keys for notebook namespace, idle timeout,
warning minutes, container image, and artifact registry.

Revision ID: 028
Revises: 027
"""

from alembic import op
import sqlalchemy as sa

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notebook_sessions",
        sa.Column("k8s_pod_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "notebook_sessions",
        sa.Column("k8s_namespace", sa.String(100), nullable=True),
    )
    op.add_column(
        "notebook_sessions",
        sa.Column("access_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "notebook_sessions",
        sa.Column("gcs_home_prefix", sa.String(500), nullable=True),
    )
    op.add_column(
        "notebook_sessions",
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.execute("""
        INSERT INTO platform_config (key, value) VALUES
            ('k8s_notebook_namespace', 'bioaf-notebooks'),
            ('notebook_idle_timeout_hours', '4'),
            ('notebook_idle_warning_minutes', '15'),
            ('bioaf_scrna_image', 'null'),
            ('artifact_registry_repo', 'null')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_column("notebook_sessions", "last_activity_at")
    op.drop_column("notebook_sessions", "gcs_home_prefix")
    op.drop_column("notebook_sessions", "access_url")
    op.drop_column("notebook_sessions", "k8s_namespace")
    op.drop_column("notebook_sessions", "k8s_pod_name")

    op.execute("""
        DELETE FROM platform_config
        WHERE key IN (
            'k8s_notebook_namespace', 'notebook_idle_timeout_hours',
            'notebook_idle_warning_minutes', 'bioaf_scrna_image',
            'artifact_registry_repo'
        )
    """)
