"""Add MINSEQE fields to samples table.

Revision ID: 005
Revises: 004
Create Date: 2026-03-06

Adds molecule_type, library_prep_method, library_layout columns
for MINSEQE compliance (ADR-013).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("samples", sa.Column("molecule_type", sa.String(100), server_default=sa.text("'total RNA'"), nullable=True))
    op.add_column("samples", sa.Column("library_prep_method", sa.String(200), nullable=True))
    op.add_column("samples", sa.Column("library_layout", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("samples", "library_layout")
    op.drop_column("samples", "library_prep_method")
    op.drop_column("samples", "molecule_type")
