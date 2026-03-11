"""Add GCP configuration keys to platform_config.

Revision ID: 022
Revises: 021
Create Date: 2026-03-11

Inserts the seven platform_config keys required for GCP credential
configuration and validation.  Uses ON CONFLICT DO NOTHING so the
migration is idempotent.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO platform_config (key, value) VALUES
            ('gcp_project_id',             ''),
            ('gcp_region',                 'us-central1'),
            ('gcp_zone',                   'us-central1-a'),
            ('org_slug',                   ''),
            ('gcp_credentials_configured', 'false'),
            ('gcp_validation_status',      ''),
            ('gcp_credential_source',      'vm_default')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM platform_config
        WHERE key IN (
            'gcp_project_id',
            'gcp_region',
            'gcp_zone',
            'org_slug',
            'gcp_credentials_configured',
            'gcp_validation_status',
            'gcp_credential_source'
        )
        """
    )
