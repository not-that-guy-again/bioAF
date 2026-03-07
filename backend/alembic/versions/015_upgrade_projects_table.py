"""Upgrade projects table with status, hypothesis, owner_user_id.

Revision ID: 015
Revises: 014
Create Date: 2026-03-06

All new columns are nullable so existing project rows are unaffected.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("status", sa.String(50), server_default="active", nullable=True))
    op.add_column("projects", sa.Column("hypothesis", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    op.create_index("idx_projects_owner_user_id", "projects", ["owner_user_id"])
    op.create_index("idx_projects_status", "projects", ["status"])


def downgrade() -> None:
    op.drop_index("idx_projects_status", table_name="projects")
    op.drop_index("idx_projects_owner_user_id", table_name="projects")
    op.drop_column("projects", "owner_user_id")
    op.drop_column("projects", "hypothesis")
    op.drop_column("projects", "status")
