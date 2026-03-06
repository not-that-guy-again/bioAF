"""Create pipeline_run_references association table.

Revision ID: 014
Revises: 013
Create Date: 2026-03-06

Many-to-many linkage between pipeline_runs and reference_datasets.
Composite PK on (pipeline_run_id, reference_dataset_id).
Index on reference_dataset_id for efficient impact queries.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pipeline_run_references",
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("reference_dataset_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["reference_dataset_id"], ["reference_datasets.id"]),
        sa.PrimaryKeyConstraint("pipeline_run_id", "reference_dataset_id"),
    )
    op.create_index(
        "idx_pipeline_run_references_dataset_id",
        "pipeline_run_references",
        ["reference_dataset_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_pipeline_run_references_dataset_id", table_name="pipeline_run_references")
    op.drop_table("pipeline_run_references")
