"""Add naming profiles, file parse results, and ingest events tables.

Revision ID: 020
Revises: 019
Create Date: 2026-03-10

Adds naming_profiles, file_parse_results, and ingest_events tables.
Also adds is_unclaimed to projects, experiments, and samples,
and file_date, version, ingest_source to files.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- naming_profiles ---
    op.create_table(
        "naming_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delimiter", sa.String(10), nullable=False, server_default="_"),
        sa.Column("strip_extension", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("segments_json", JSONB, nullable=False),
        sa.Column("project_code_mappings", JSONB, nullable=False, server_default="{}"),
        sa.Column("experiment_code_mappings", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("idx_naming_profiles_org_id", "naming_profiles", ["organization_id"])
    op.create_index("idx_naming_profiles_status", "naming_profiles", ["organization_id", "status"])

    # --- file_parse_results ---
    op.create_table(
        "file_parse_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=False),
        sa.Column("naming_profile_id", sa.Integer(), nullable=True),
        sa.Column("parsed_segments_json", JSONB, nullable=True),
        sa.Column("match_status", sa.String(20), nullable=False),
        sa.Column("auto_linked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["naming_profile_id"], ["naming_profiles.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
    )
    op.create_index("idx_file_parse_results_file_id", "file_parse_results", ["file_id"])
    op.create_index("idx_file_parse_results_profile_id", "file_parse_results", ["naming_profile_id"])

    # --- ingest_events ---
    op.create_table(
        "ingest_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.Column("source_bucket", sa.String(255), nullable=False),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("naming_profile_id", sa.Integer(), nullable=True),
        sa.Column("parsed_project_code", sa.String(255), nullable=True),
        sa.Column("parsed_experiment_code", sa.String(255), nullable=True),
        sa.Column("parsed_sample_id", sa.String(255), nullable=True),
        sa.Column("resolved_project_id", sa.Integer(), nullable=True),
        sa.Column("resolved_experiment_id", sa.Integer(), nullable=True),
        sa.Column("resolved_sample_id", sa.Integer(), nullable=True),
        sa.Column("auto_created_entities", JSONB, nullable=True),
        sa.Column("ingest_status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["naming_profile_id"], ["naming_profiles.id"]),
        sa.ForeignKeyConstraint(["resolved_project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["resolved_experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["resolved_sample_id"], ["samples.id"]),
    )
    op.create_index("idx_ingest_events_file_id", "ingest_events", ["file_id"])
    op.create_index("idx_ingest_events_status", "ingest_events", ["ingest_status"])
    op.create_index("idx_ingest_events_created_at", "ingest_events", ["created_at"])

    # --- Column additions to existing tables ---
    op.add_column("projects", sa.Column("is_unclaimed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column(
        "experiments", sa.Column("is_unclaimed", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.add_column("samples", sa.Column("is_unclaimed", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("files", sa.Column("file_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("files", sa.Column("version", sa.String(50), nullable=True))
    op.add_column("files", sa.Column("ingest_source", sa.String(20), server_default="manual", nullable=True))


def downgrade() -> None:
    op.drop_column("files", "ingest_source")
    op.drop_column("files", "version")
    op.drop_column("files", "file_date")
    op.drop_column("samples", "is_unclaimed")
    op.drop_column("experiments", "is_unclaimed")
    op.drop_column("projects", "is_unclaimed")

    op.drop_index("idx_ingest_events_created_at", table_name="ingest_events")
    op.drop_index("idx_ingest_events_status", table_name="ingest_events")
    op.drop_index("idx_ingest_events_file_id", table_name="ingest_events")
    op.drop_table("ingest_events")

    op.drop_index("idx_file_parse_results_profile_id", table_name="file_parse_results")
    op.drop_index("idx_file_parse_results_file_id", table_name="file_parse_results")
    op.drop_table("file_parse_results")

    op.drop_index("idx_naming_profiles_status", table_name="naming_profiles")
    op.drop_index("idx_naming_profiles_org_id", table_name="naming_profiles")
    op.drop_table("naming_profiles")
