"""Add storage_deleted flag to files table.

When storage infrastructure is destroyed, files are marked as
storage_deleted rather than removed from the DB. This preserves
metadata (experiment associations, checksums, upload history)
while indicating the backing GCS object no longer exists.

Revision ID: 053
Revises: 052
"""

from alembic import op
import sqlalchemy as sa

revision = "053"
down_revision = "052"


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("storage_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_index("idx_files_storage_deleted", "files", ["storage_deleted"])


def downgrade() -> None:
    op.drop_index("idx_files_storage_deleted", table_name="files")
    op.drop_column("files", "storage_deleted")
