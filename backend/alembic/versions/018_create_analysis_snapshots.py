"""Create analysis_snapshots table.

Revision ID: 018
Revises: 017
Create Date: 2026-03-06

Table created now for Phase 10b SDK. Will be empty until then.
CHECK constraint ensures at least one of experiment_id or project_id is set.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("notebook_session_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("object_type", sa.String(50), nullable=False),
        sa.Column("cell_count", sa.Integer(), nullable=True),
        sa.Column("gene_count", sa.Integer(), nullable=True),
        sa.Column("parameters_json", JSONB, nullable=True),
        sa.Column("embeddings_json", JSONB, nullable=True),
        sa.Column("clusterings_json", JSONB, nullable=True),
        sa.Column("layers_json", JSONB, nullable=True),
        sa.Column("metadata_columns_json", JSONB, nullable=True),
        sa.Column("command_log_json", JSONB, nullable=True),
        sa.Column("figure_file_id", sa.Integer(), nullable=True),
        sa.Column("checkpoint_file_id", sa.Integer(), nullable=True),
        sa.Column("starred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["notebook_session_id"], ["notebook_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["figure_file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["checkpoint_file_id"], ["files.id"]),
        sa.CheckConstraint(
            "experiment_id IS NOT NULL OR project_id IS NOT NULL",
            name="ck_analysis_snapshots_scope",
        ),
    )
    op.create_index("idx_analysis_snapshots_org_experiment", "analysis_snapshots", ["organization_id", "experiment_id"])
    op.create_index("idx_analysis_snapshots_org_project", "analysis_snapshots", ["organization_id", "project_id"])
    op.create_index("idx_analysis_snapshots_notebook", "analysis_snapshots", ["notebook_session_id"])


def downgrade() -> None:
    op.drop_index("idx_analysis_snapshots_notebook", table_name="analysis_snapshots")
    op.drop_index("idx_analysis_snapshots_org_project", table_name="analysis_snapshots")
    op.drop_index("idx_analysis_snapshots_org_experiment", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
