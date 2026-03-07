"""Create reference_datasets table.

Revision ID: 012
Revises: 011
Create Date: 2026-03-06

Reference data registry for genomes, annotations, indices, and other
reference datasets used by pipelines (ADR-017).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("gcs_prefix", sa.Text(), nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("md5_manifest_json", JSONB(), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("deprecation_note", sa.Text(), nullable=True),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["reference_datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "name", "version", name="uq_reference_org_name_version"),
    )
    op.create_index("idx_reference_datasets_org_id", "reference_datasets", ["organization_id"])
    op.create_index("idx_reference_datasets_category", "reference_datasets", ["category"])
    op.create_index("idx_reference_datasets_status", "reference_datasets", ["status"])


def downgrade() -> None:
    op.drop_index("idx_reference_datasets_status", table_name="reference_datasets")
    op.drop_index("idx_reference_datasets_category", table_name="reference_datasets")
    op.drop_index("idx_reference_datasets_org_id", table_name="reference_datasets")
    op.drop_table("reference_datasets")
