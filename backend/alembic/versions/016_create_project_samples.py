"""Create project_samples table for cross-experiment sample linkage.

Revision ID: 016
Revises: 015
Create Date: 2026-03-06

Links samples from multiple experiments to a single project.
Unique constraint on (project_id, sample_id) prevents duplicate additions.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.Integer(), nullable=False),
        sa.Column("added_by_user_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("project_id", "sample_id", name="uq_project_samples_project_sample"),
    )
    op.create_index("idx_project_samples_project_id", "project_samples", ["project_id"])
    op.create_index("idx_project_samples_sample_id", "project_samples", ["sample_id"])


def downgrade() -> None:
    op.drop_index("idx_project_samples_sample_id", table_name="project_samples")
    op.drop_index("idx_project_samples_project_id", table_name="project_samples")
    op.drop_table("project_samples")
