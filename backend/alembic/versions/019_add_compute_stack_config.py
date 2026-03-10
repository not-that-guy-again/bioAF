"""Add compute_stack platform config with kubernetes as default.

Revision ID: 019
Revises: 018
Create Date: 2026-03-10

Adds a platform_config row for compute_stack selection.
Allowed values: kubernetes, slurm. Default: kubernetes.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO platform_config (key, value) VALUES ('compute_stack', 'kubernetes') "
        "ON CONFLICT (key) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM platform_config WHERE key = 'compute_stack'")
