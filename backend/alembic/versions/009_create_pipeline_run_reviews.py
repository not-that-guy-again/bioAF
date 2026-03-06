"""Create pipeline_run_reviews table.

Revision ID: 009
Revises: 008
Create Date: 2026-03-06

New table for pipeline run review records (ADR-019).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sample_verdicts_json", JSONB(), nullable=True),
        sa.Column("recommended_exclusions", JSONB(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["pipeline_run_reviews.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pipeline_run_reviews_run_id", "pipeline_run_reviews", ["pipeline_run_id"])
    op.create_index(
        "idx_pipeline_run_reviews_active",
        "pipeline_run_reviews",
        ["pipeline_run_id", "superseded_by_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_pipeline_run_reviews_active", table_name="pipeline_run_reviews")
    op.drop_index("idx_pipeline_run_reviews_run_id", table_name="pipeline_run_reviews")
    op.drop_table("pipeline_run_reviews")
