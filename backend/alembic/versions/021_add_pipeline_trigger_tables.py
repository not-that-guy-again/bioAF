"""Add pipeline triggers, trigger evaluations, and cost history tables.

Revision ID: 021
Revises: 020
Create Date: 2026-03-10

Adds pipeline_triggers, trigger_evaluations, and pipeline_cost_history tables
for automated pipeline triggering with budget-aware pre-flight checks.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- pipeline_triggers ---
    op.create_table(
        "pipeline_triggers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("trigger_mode", sa.String(20), nullable=False),
        sa.Column("event_config", JSONB, nullable=True),
        sa.Column("schedule_config", JSONB, nullable=True),
        sa.Column("parameter_defaults", JSONB, nullable=False, server_default="{}"),
        sa.Column("budget_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipeline_catalog.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("idx_pipeline_triggers_org_id", "pipeline_triggers", ["organization_id"])
    op.create_index("idx_pipeline_triggers_pipeline_id", "pipeline_triggers", ["pipeline_id"])
    op.create_index("idx_pipeline_triggers_enabled", "pipeline_triggers", ["organization_id", "enabled"])

    # --- trigger_evaluations ---
    op.create_table(
        "trigger_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trigger_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_type", sa.String(20), nullable=False),
        sa.Column("matched_files", JSONB, nullable=True),
        sa.Column("budget_check_result", JSONB, nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["trigger_id"], ["pipeline_triggers.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
    )
    op.create_index("idx_trigger_evaluations_trigger_id", "trigger_evaluations", ["trigger_id"])
    op.create_index("idx_trigger_evaluations_created_at", "trigger_evaluations", ["created_at"])

    # --- pipeline_cost_history ---
    op.create_table(
        "pipeline_cost_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_name", sa.String(255), nullable=False),
        sa.Column("input_file_count", sa.Integer(), nullable=True),
        sa.Column("input_total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("actual_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimation_error_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
    )
    op.create_index("idx_pipeline_cost_history_pipeline_name", "pipeline_cost_history", ["pipeline_name"])
    op.create_index("idx_pipeline_cost_history_created_at", "pipeline_cost_history", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_pipeline_cost_history_created_at", table_name="pipeline_cost_history")
    op.drop_index("idx_pipeline_cost_history_pipeline_name", table_name="pipeline_cost_history")
    op.drop_table("pipeline_cost_history")

    op.drop_index("idx_trigger_evaluations_created_at", table_name="trigger_evaluations")
    op.drop_index("idx_trigger_evaluations_trigger_id", table_name="trigger_evaluations")
    op.drop_table("trigger_evaluations")

    op.drop_index("idx_pipeline_triggers_enabled", table_name="pipeline_triggers")
    op.drop_index("idx_pipeline_triggers_pipeline_id", table_name="pipeline_triggers")
    op.drop_index("idx_pipeline_triggers_org_id", table_name="pipeline_triggers")
    op.drop_table("pipeline_triggers")
