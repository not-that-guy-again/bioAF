"""Add expected_contamination_pct column to libraries.

Revision ID: 068
Revises: 067
Create Date: 2026-04-15

Records the expected index-hopping rate for a library, either inferred
from the sequencer model at create time or set by the caller. Additive,
nullable column.
"""

import sqlalchemy as sa
from alembic import op

revision = "068"
down_revision = "067"


def upgrade() -> None:
    op.add_column(
        "libraries",
        sa.Column("expected_contamination_pct", sa.Numeric(5, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("libraries", "expected_contamination_pct")
