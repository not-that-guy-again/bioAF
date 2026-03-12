"""Phase 18 - GCS bucket infrastructure.

Adds storage-related platform_config keys and experiment_id column to files table.

Revision ID: 024
Revises: 023
"""

from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add experiment_id column to files table (nullable FK to experiments)
    op.add_column("files", sa.Column("experiment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_files_experiment_id",
        "files",
        "experiments",
        ["experiment_id"],
        ["id"],
    )
    op.create_index("idx_files_experiment_id", "files", ["experiment_id"])

    # Seed storage-related platform_config keys
    op.execute("""
        INSERT INTO platform_config (key, value) VALUES
            ('storage_deployed', 'false'),
            ('ingest_bucket_name', 'null'),
            ('raw_bucket_name', 'null'),
            ('working_bucket_name', 'null'),
            ('results_bucket_name', 'null'),
            ('config_backups_bucket_name', 'null')
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("idx_files_experiment_id", table_name="files")
    op.drop_constraint("fk_files_experiment_id", "files", type_="foreignkey")
    op.drop_column("files", "experiment_id")

    op.execute("""
        DELETE FROM platform_config
        WHERE key IN (
            'storage_deployed', 'ingest_bucket_name', 'raw_bucket_name',
            'working_bucket_name', 'results_bucket_name', 'config_backups_bucket_name'
        )
    """)
