"""Phase 21 - Auto-ingest Pub/Sub configuration.

Adds platform_config keys for Pub/Sub topic, subscription,
auto-ingest toggle, and cleanup policy.

Revision ID: 027
Revises: 026
"""

from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO platform_config (key, value) VALUES
            ('pubsub_topic_name', 'null'),
            ('pubsub_subscription_name', 'null'),
            ('auto_ingest_enabled', 'false'),
            ('ingest_cleanup_policy', 'delete_after_copy')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM platform_config
        WHERE key IN (
            'pubsub_topic_name', 'pubsub_subscription_name',
            'auto_ingest_enabled', 'ingest_cleanup_policy'
        )
    """)
