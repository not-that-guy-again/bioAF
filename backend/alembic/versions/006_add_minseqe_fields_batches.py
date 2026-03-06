"""Add MINSEQE fields to batches table.

Revision ID: 006
Revises: 005
Create Date: 2026-03-06

Adds instrument_model, instrument_platform, quality_score_encoding
columns for MINSEQE compliance (ADR-013).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("batches", sa.Column("instrument_model", sa.String(200), nullable=True))
    op.add_column("batches", sa.Column("instrument_platform", sa.String(100), nullable=True))
    op.add_column(
        "batches",
        sa.Column("quality_score_encoding", sa.String(50), server_default=sa.text("'Phred+33'"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("batches", "quality_score_encoding")
    op.drop_column("batches", "instrument_platform")
    op.drop_column("batches", "instrument_model")
