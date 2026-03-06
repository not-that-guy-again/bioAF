"""Add MINSEQE fields to pipeline_runs table.

Revision ID: 007
Revises: 006
Create Date: 2026-03-06

Adds reference_genome and alignment_algorithm columns
for MINSEQE compliance (ADR-013).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("reference_genome", sa.String(200), nullable=True))
    op.add_column("pipeline_runs", sa.Column("alignment_algorithm", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("pipeline_runs", "alignment_algorithm")
    op.drop_column("pipeline_runs", "reference_genome")
