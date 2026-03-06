"""Create controlled_vocabularies table.

Revision ID: 008
Revises: 007
Create Date: 2026-03-06

New table for managing controlled vocabulary values
for MINSEQE fields (ADR-013).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "controlled_vocabularies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("allowed_value", sa.String(length=300), nullable=False),
        sa.Column("display_label", sa.String(length=300), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_name", "allowed_value", name="uq_controlled_vocab_field_value"),
    )
    op.create_index("idx_controlled_vocab_field_name", "controlled_vocabularies", ["field_name"])


def downgrade() -> None:
    op.drop_index("idx_controlled_vocab_field_name", table_name="controlled_vocabularies")
    op.drop_table("controlled_vocabularies")
