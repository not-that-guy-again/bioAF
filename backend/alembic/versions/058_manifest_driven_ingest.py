"""Manifest-driven ingest with batch separation.

Revision ID: 058
Revises: 057

Renames batches -> sample_batches, removes sequencer fields from
sample_batches, renames samples.batch_id -> sample_batch_id, adds
sequencing_batches and manifest_entries tables, adds
sequencing_batch_id to samples and files.
"""

from alembic import op
import sqlalchemy as sa

revision = "058"
down_revision = "057"


def upgrade() -> None:
    # --- Step 1: Rename batches table to sample_batches ---
    op.rename_table("batches", "sample_batches")

    # Rename samples.batch_id -> sample_batch_id and update FK
    op.alter_column("samples", "batch_id", new_column_name="sample_batch_id")
    # Drop old FK and create new one pointing to sample_batches
    op.drop_constraint("samples_batch_id_fkey", "samples", type_="foreignkey")
    op.create_foreign_key(
        "samples_sample_batch_id_fkey",
        "samples",
        "sample_batches",
        ["sample_batch_id"],
        ["id"],
    )

    # Remove sequencer fields from sample_batches (moved to sequencing_batches)
    op.drop_column("sample_batches", "sequencer_run_id")
    op.drop_column("sample_batches", "instrument_model")
    op.drop_column("sample_batches", "instrument_platform")
    op.drop_column("sample_batches", "quality_score_encoding")

    # --- Step 2: Create sequencing_batches table ---
    op.create_table(
        "sequencing_batches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("batch_number", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("instrument_model", sa.String(200), nullable=True),
        sa.Column("instrument_platform", sa.String(100), nullable=True),
        sa.Column("quality_score_encoding", sa.String(50), server_default="Phred+33", nullable=True),
        sa.Column("sequencer_run_id", sa.String(255), nullable=True),
        sa.Column("manifest_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_file_count", sa.Integer(), nullable=True),
        sa.Column("ingested_file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Step 3: Create manifest_entries table ---
    op.create_table(
        "manifest_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sequencing_batch_id", sa.Integer(), sa.ForeignKey("sequencing_batches.id"), nullable=False),
        sa.Column("expected_filename", sa.String(500), nullable=False),
        sa.Column("expected_md5", sa.String(64), nullable=False),
        sa.Column("resolved_sample_id", sa.Integer(), sa.ForeignKey("samples.id"), nullable=True),
        sa.Column("resolved_experiment_id", sa.Integer(), sa.ForeignKey("experiments.id"), nullable=True),
        sa.Column("resolved_project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Step 4: Add sequencing_batch_id FK to samples and files ---
    op.add_column(
        "samples",
        sa.Column("sequencing_batch_id", sa.Integer(), sa.ForeignKey("sequencing_batches.id"), nullable=True),
    )
    op.add_column(
        "files",
        sa.Column("sequencing_batch_id", sa.Integer(), sa.ForeignKey("sequencing_batches.id"), nullable=True),
    )


def downgrade() -> None:
    # Remove sequencing_batch_id from files and samples
    op.drop_column("files", "sequencing_batch_id")
    op.drop_column("samples", "sequencing_batch_id")

    # Drop new tables
    op.drop_table("manifest_entries")
    op.drop_table("sequencing_batches")

    # Add sequencer fields back to sample_batches
    op.add_column("sample_batches", sa.Column("quality_score_encoding", sa.String(50), server_default="Phred+33"))
    op.add_column("sample_batches", sa.Column("instrument_platform", sa.String(100)))
    op.add_column("sample_batches", sa.Column("instrument_model", sa.String(200)))
    op.add_column("sample_batches", sa.Column("sequencer_run_id", sa.String(255)))

    # Rename sample_batch_id back to batch_id
    op.drop_constraint("samples_sample_batch_id_fkey", "samples", type_="foreignkey")
    op.alter_column("samples", "sample_batch_id", new_column_name="batch_id")
    op.create_foreign_key(
        "samples_batch_id_fkey",
        "samples",
        "sample_batches",
        ["batch_id"],
        ["id"],
    )

    # Rename table back
    op.rename_table("sample_batches", "batches")
