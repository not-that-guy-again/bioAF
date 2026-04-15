"""Add Library and BarcodeMap tables plus File.library_id.

Revision ID: 067
Revises: 066
Create Date: 2026-04-15

Introduces the Library entity between Sample and File, the BarcodeMap
table for library indices and intra-library barcodes, and a nullable
File.library_id FK. All additive; no backfill.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "067"
down_revision = "066"


def upgrade() -> None:
    op.create_table(
        "libraries",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "sample_id",
            sa.Integer(),
            sa.ForeignKey("samples.id"),
            nullable=False,
        ),
        sa.Column("library_id_external", sa.String(length=255), nullable=True),
        sa.Column("prep_kit", sa.String(length=200), nullable=True),
        sa.Column("prep_protocol_version", sa.String(length=50), nullable=True),
        sa.Column("prep_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assay_type", sa.String(length=100), nullable=True),
        sa.Column("molecule_type", sa.String(length=100), nullable=True),
        sa.Column("strandedness", sa.String(length=50), nullable=True),
        sa.Column("read_layout", sa.String(length=50), nullable=True),
        sa.Column("target_read_length", sa.Integer(), nullable=True),
        sa.Column(
            "index_type",
            sa.String(length=20),
            nullable=False,
            server_default="none",
        ),
        sa.Column("i5_sequence", sa.String(length=32), nullable=True),
        sa.Column("i7_sequence", sa.String(length=32), nullable=True),
        sa.Column("i5_orientation_convention", sa.String(length=50), nullable=True),
        sa.Column("insert_size_mean", sa.Integer(), nullable=True),
        sa.Column("molarity_nm", sa.Numeric(10, 3), nullable=True),
        sa.Column("concentration_ng_ul", sa.Numeric(10, 3), nullable=True),
        sa.Column("qc_status", sa.String(length=20), nullable=True),
        sa.Column("qc_notes", sa.Text(), nullable=True),
        sa.Column(
            "sequencing_batch_id",
            sa.Integer(),
            sa.ForeignKey("sequencing_batches.id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="planned",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "library_id_external",
            name="uq_libraries_org_external_id",
        ),
    )
    op.create_index("idx_libraries_sample_id", "libraries", ["sample_id"])
    op.create_index(
        "idx_libraries_sequencing_batch_id", "libraries", ["sequencing_batch_id"]
    )
    op.create_index(
        "idx_libraries_i7_i5", "libraries", ["i7_sequence", "i5_sequence"]
    )

    op.create_table(
        "barcode_maps",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "library_id",
            sa.Integer(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column("barcode_type", sa.String(length=30), nullable=False),
        sa.Column("sequence", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("read_position", sa.String(length=8), nullable=True),
        sa.Column("offset_in_read", sa.Integer(), nullable=True),
        sa.Column("length", sa.Integer(), nullable=True),
        sa.Column(
            "allowed_mismatches", sa.Integer(), nullable=True, server_default="1"
        ),
        sa.Column("whitelist_reference", sa.String(length=255), nullable=True),
        sa.Column("attributes_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "library_id",
            "barcode_type",
            "sequence",
            "read_position",
            name="uq_barcode_maps_library_type_seq_pos",
        ),
    )
    op.create_index("idx_barcode_maps_library_id", "barcode_maps", ["library_id"])
    op.create_index("idx_barcode_maps_sequence", "barcode_maps", ["sequence"])
    op.create_index(
        "idx_barcode_maps_type_sequence",
        "barcode_maps",
        ["barcode_type", "sequence"],
    )

    op.add_column(
        "files",
        sa.Column(
            "library_id",
            sa.Integer(),
            sa.ForeignKey("libraries.id"),
            nullable=True,
        ),
    )
    op.create_index("idx_files_library_id", "files", ["library_id"])


def downgrade() -> None:
    op.drop_index("idx_files_library_id", table_name="files")
    op.drop_column("files", "library_id")

    op.drop_index("idx_barcode_maps_type_sequence", table_name="barcode_maps")
    op.drop_index("idx_barcode_maps_sequence", table_name="barcode_maps")
    op.drop_index("idx_barcode_maps_library_id", table_name="barcode_maps")
    op.drop_table("barcode_maps")

    op.drop_index("idx_libraries_i7_i5", table_name="libraries")
    op.drop_index("idx_libraries_sequencing_batch_id", table_name="libraries")
    op.drop_index("idx_libraries_sample_id", table_name="libraries")
    op.drop_table("libraries")
