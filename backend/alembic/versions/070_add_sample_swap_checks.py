"""Add sample_swap_checks table.

Revision ID: 070
Revises: 069
Create Date: 2026-04-15

Records per-library attribute mismatches surfaced by post-ingest QC
(species-ID, XIST/Y-chromosome calls, etc). The pipeline step that
populates these rows is tracked separately; this migration only adds
the table and supporting index.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "070"
down_revision = "069"


def upgrade() -> None:
    op.create_table(
        "sample_swap_checks",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "library_id",
            sa.Integer(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_runs.id"),
            nullable=True,
        ),
        sa.Column("expected_attribute", sa.String(length=255), nullable=False),
        sa.Column("observed_attribute", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_sample_swap_checks_library_id",
        "sample_swap_checks",
        ["library_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_sample_swap_checks_library_id", table_name="sample_swap_checks")
    op.drop_table("sample_swap_checks")
