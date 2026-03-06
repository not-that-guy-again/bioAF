"""Seed controlled_vocabularies table with GEO-compatible values.

Revision ID: 011
Revises: 010
Create Date: 2026-03-06

Populates controlled_vocabularies with all values from the Phase 8 spec
Section 2.7 (ADR-013).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

SEED_DATA = [
    # molecule_type
    ("molecule_type", "total RNA", None, 1, True),
    ("molecule_type", "polyA RNA", None, 2, False),
    ("molecule_type", "cytoplasmic RNA", None, 3, False),
    ("molecule_type", "nuclear RNA", None, 4, False),
    ("molecule_type", "genomic DNA", None, 5, False),
    ("molecule_type", "protein", None, 6, False),
    ("molecule_type", "other", None, 7, False),
    # library_layout
    ("library_layout", "single", None, 1, True),
    ("library_layout", "paired", None, 2, False),
    ("library_layout", "other", None, 3, False),
    # instrument_platform
    ("instrument_platform", "ILLUMINA", None, 1, True),
    ("instrument_platform", "PACBIO_SMRT", None, 2, False),
    ("instrument_platform", "OXFORD_NANOPORE", None, 3, False),
    ("instrument_platform", "OTHER", None, 4, False),
    # instrument_model - Illumina
    ("instrument_model", "Illumina NovaSeq 6000", None, 1, True),
    ("instrument_model", "Illumina NovaSeq X", None, 2, False),
    ("instrument_model", "Illumina NextSeq 500", None, 3, False),
    ("instrument_model", "Illumina NextSeq 550", None, 4, False),
    ("instrument_model", "Illumina NextSeq 1000", None, 5, False),
    ("instrument_model", "Illumina NextSeq 2000", None, 6, False),
    ("instrument_model", "Illumina HiSeq 2500", None, 7, False),
    ("instrument_model", "Illumina HiSeq 3000", None, 8, False),
    ("instrument_model", "Illumina HiSeq 4000", None, 9, False),
    ("instrument_model", "Illumina MiSeq", None, 10, False),
    ("instrument_model", "Illumina iSeq 100", None, 11, False),
    ("instrument_model", "Illumina NovaSeq X Plus", None, 12, False),
    # instrument_model - PacBio
    ("instrument_model", "PacBio Sequel", None, 13, False),
    ("instrument_model", "PacBio Sequel II", None, 14, False),
    ("instrument_model", "PacBio Sequel IIe", None, 15, False),
    ("instrument_model", "PacBio Revio", None, 16, False),
    # instrument_model - ONT
    ("instrument_model", "Oxford Nanopore MinION", None, 17, False),
    ("instrument_model", "Oxford Nanopore GridION", None, 18, False),
    ("instrument_model", "Oxford Nanopore PromethION", None, 19, False),
    # quality_score_encoding
    ("quality_score_encoding", "Phred+33", None, 1, True),
    ("quality_score_encoding", "Phred+64", None, 2, False),
    # reference_genome
    ("reference_genome", "GRCh38", None, 1, True),
    ("reference_genome", "GRCh37", None, 2, False),
    ("reference_genome", "GRCm39", None, 3, False),
    ("reference_genome", "GRCm38", None, 4, False),
    ("reference_genome", "T2T-CHM13", None, 5, False),
    ("reference_genome", "other", None, 6, False),
    # alignment_algorithm
    ("alignment_algorithm", "STARsolo", None, 1, False),
    ("alignment_algorithm", "CellRanger", None, 2, False),
    ("alignment_algorithm", "Salmon/Alevin", None, 3, False),
    ("alignment_algorithm", "Kallisto-Bustools", None, 4, False),
    ("alignment_algorithm", "other", None, 5, False),
    # library_prep_method
    ("library_prep_method", "10x Chromium 3' v3.1", None, 1, True),
    ("library_prep_method", "10x Chromium 3' v3", None, 2, False),
    ("library_prep_method", "10x Chromium 3' v2", None, 3, False),
    ("library_prep_method", "10x Chromium 5' v2", None, 4, False),
    ("library_prep_method", "10x Chromium 5' v1.1", None, 5, False),
    ("library_prep_method", "Smart-seq2", None, 6, False),
    ("library_prep_method", "other", None, 7, False),
]


def upgrade() -> None:
    table = sa.table(
        "controlled_vocabularies",
        sa.column("field_name", sa.String),
        sa.column("allowed_value", sa.String),
        sa.column("display_label", sa.String),
        sa.column("display_order", sa.Integer),
        sa.column("is_default", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    rows = [
        {
            "field_name": field_name,
            "allowed_value": allowed_value,
            "display_label": display_label,
            "display_order": display_order,
            "is_default": is_default,
            "is_active": True,
        }
        for field_name, allowed_value, display_label, display_order, is_default in SEED_DATA
    ]
    op.bulk_insert(table, rows)


def downgrade() -> None:
    op.execute("DELETE FROM controlled_vocabularies")
