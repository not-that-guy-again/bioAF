"""Phase 17 - terraform executor columns and platform_config keys.

Revision ID: 023
Revises: 022
Create Date: 2026-03-11

Adds columns to terraform_runs for module tracking, plan JSON, resource
progress, apply log, and state URL. Seeds platform_config with keys
for terraform state bucket and initialization flag.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("terraform_runs", sa.Column("module_name", sa.String(length=100), nullable=True))
    op.add_column("terraform_runs", sa.Column("plan_json", JSONB(), nullable=True))
    op.add_column("terraform_runs", sa.Column("resources_planned", sa.Integer(), nullable=True))
    op.add_column(
        "terraform_runs",
        sa.Column("resources_completed", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("terraform_runs", sa.Column("apply_log", sa.Text(), nullable=True))
    op.add_column("terraform_runs", sa.Column("terraform_state_url", sa.String(length=500), nullable=True))

    op.execute(
        """
        INSERT INTO platform_config (key, value) VALUES
            ('terraform_state_bucket', ''),
            ('terraform_initialized',  'false')
        ON CONFLICT (key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM platform_config
        WHERE key IN ('terraform_state_bucket', 'terraform_initialized')
        """
    )
    op.drop_column("terraform_runs", "terraform_state_url")
    op.drop_column("terraform_runs", "apply_log")
    op.drop_column("terraform_runs", "resources_completed")
    op.drop_column("terraform_runs", "resources_planned")
    op.drop_column("terraform_runs", "plan_json")
    op.drop_column("terraform_runs", "module_name")
