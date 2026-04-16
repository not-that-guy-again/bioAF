"""Add is_pattern_only column to barcode_maps.

Revision ID: 069
Revises: 068
Create Date: 2026-04-15

Distinguishes pattern-only barcode rows (UMIs and other positional
patterns with no concrete sequence) from explicit-sequence rows. Additive,
nullable column with default false so existing rows remain interpretable.
"""

import sqlalchemy as sa
from alembic import op

revision = "069"
down_revision = "068"


def upgrade() -> None:
    op.add_column(
        "barcode_maps",
        sa.Column(
            "is_pattern_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("barcode_maps", "is_pattern_only")
