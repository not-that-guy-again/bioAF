"""Create reference_dataset_files table.

Revision ID: 013
Revises: 012
Create Date: 2026-03-06

File manifest for each reference dataset. ON DELETE CASCADE so
dropping a reference dataset removes its file records.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_dataset_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reference_dataset_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("gcs_uri", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("md5_checksum", sa.String(length=32), nullable=True),
        sa.Column("file_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["reference_dataset_id"],
            ["reference_datasets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_reference_dataset_files_dataset_id",
        "reference_dataset_files",
        ["reference_dataset_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_reference_dataset_files_dataset_id", table_name="reference_dataset_files")
    op.drop_table("reference_dataset_files")
