"""Initial schema - all tables for bioAF platform.

Revision ID: 001
Revises:
Create Date: 2026-03-05

Phase 1 tables: organizations, users, verification_codes, audit_log,
                component_states, terraform_runs, platform_config
Phase 2 tables: projects, experiments, samples, batches, experiment_templates,
                experiment_custom_fields
Phase 3+ placeholders: sample_files, pipeline_runs, pipeline_run_samples,
                       notebook_session_files
Phase 3 tables: notebook_sessions, slurm_jobs, user_quotas
Phase 4 tables: pipeline_catalog, pipeline_processes
Phase 4 updates: pipeline_runs (additional columns)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # Phase 1 tables (fully used)
    # ---------------------------------------------------------------

    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("setup_complete", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("smtp_configured", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), server_default=sa.text("'viewer'"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "verification_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "terraform_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("triggered_by_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("component_key", sa.String(length=50), nullable=True),
        sa.Column("plan_summary_json", JSONB(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("details_json", JSONB(), nullable=True),
        sa.Column("previous_value_json", JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "component_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("component_key", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'disabled'"), nullable=False),
        sa.Column("config_json", JSONB(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("last_terraform_run_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["last_terraform_run_id"], ["terraform_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("component_key"),
    )

    op.create_table(
        "platform_config",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # ---------------------------------------------------------------
    # Phase 2 tables (experiment tracking)
    # ---------------------------------------------------------------

    op.create_table(
        "experiment_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_fields_json", JSONB(), nullable=True),
        sa.Column("custom_fields_schema_json", JSONB(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("protocol_doc_id", sa.Integer(), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'registered'"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("expected_sample_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["experiment_templates.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prep_date", sa.Date(), nullable=True),
        sa.Column("operator_user_id", sa.Integer(), nullable=True),
        sa.Column("sequencer_run_id", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("sample_id_external", sa.String(length=255), nullable=True),
        sa.Column("organism", sa.String(length=100), nullable=True),
        sa.Column("tissue_type", sa.String(length=100), nullable=True),
        sa.Column("donor_source", sa.String(length=255), nullable=True),
        sa.Column("treatment_condition", sa.String(length=255), nullable=True),
        sa.Column("chemistry_version", sa.String(length=50), nullable=True),
        sa.Column("viability_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("cell_count", sa.Integer(), nullable=True),
        sa.Column("prep_notes", sa.Text(), nullable=True),
        sa.Column("qc_status", sa.String(length=20), nullable=True),
        sa.Column("qc_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'registered'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "experiment_custom_fields",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=True),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------------------------------------------------------------
    # Phase 3+ placeholder tables
    # ---------------------------------------------------------------

    op.create_table(
        "sample_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sample_id", sa.Integer(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("pipeline_name", sa.String(length=255), nullable=False),
        sa.Column("pipeline_version", sa.String(length=50), nullable=True),
        sa.Column("parameters_json", JSONB(), nullable=True),
        sa.Column("input_files_json", JSONB(), nullable=True),
        sa.Column("output_files_json", JSONB(), nullable=True),
        sa.Column("container_versions_json", JSONB(), nullable=True),
        sa.Column("nextflow_trace_json", JSONB(), nullable=True),
        sa.Column("progress_json", JSONB(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("cost_estimate", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("work_dir", sa.String(length=500), nullable=True),
        sa.Column("slurm_job_id", sa.String(length=50), nullable=True),
        sa.Column("resume_from_run_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["resume_from_run_id"], ["pipeline_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pipeline_run_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------------------------------------------------------------
    # Phase 4 tables (pipeline orchestration)
    # ---------------------------------------------------------------

    op.create_table(
        "pipeline_catalog",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("schema_json", JSONB(), nullable=True),
        sa.Column("default_params_json", JSONB(), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "pipeline_key", name="uq_pipeline_catalog_org_key"),
    )

    op.create_table(
        "pipeline_processes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("process_name", sa.String(length=255), nullable=False),
        sa.Column("task_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("cpu_usage", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("memory_peak_gb", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("slurm_job_id", sa.String(length=50), nullable=True),
        sa.Column("stdout_path", sa.String(length=500), nullable=True),
        sa.Column("stderr_path", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------------------------------------------------------------
    # Phase 3 tables (compute + notebooks)
    # ---------------------------------------------------------------

    op.create_table(
        "notebook_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("session_type", sa.String(length=20), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("slurm_job_id", sa.String(length=50), nullable=True),
        sa.Column("resource_profile", sa.String(length=50), nullable=False),
        sa.Column("cpu_cores", sa.Integer(), nullable=False),
        sa.Column("memory_gb", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("idle_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proxy_url", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "slurm_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("slurm_job_id", sa.String(length=50), nullable=False),
        sa.Column("job_name", sa.String(length=255), nullable=True),
        sa.Column("partition", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("notebook_session_id", sa.Integer(), nullable=True),
        sa.Column("cpu_requested", sa.Integer(), nullable=True),
        sa.Column("memory_gb_requested", sa.Integer(), nullable=True),
        sa.Column("cpu_used", sa.Integer(), nullable=True),
        sa.Column("memory_gb_used", sa.Integer(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout_path", sa.String(length=500), nullable=True),
        sa.Column("stderr_path", sa.String(length=500), nullable=True),
        sa.Column("cost_estimate", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["notebook_session_id"], ["notebook_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_quotas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("cpu_hours_monthly_limit", sa.Integer(), nullable=True),
        sa.Column(
            "cpu_hours_used_current_month",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "quota_reset_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("date_trunc('month', NOW()) + INTERVAL '1 month'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "notebook_session_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.Column("access_type", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["notebook_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ---------------------------------------------------------------
    # Indexes
    # ---------------------------------------------------------------
    op.create_index("idx_experiments_org_id", "experiments", ["organization_id"])
    op.create_index("idx_experiments_project_id", "experiments", ["project_id"])
    op.create_index("idx_experiments_status", "experiments", ["status"])
    op.create_index("idx_experiments_owner", "experiments", ["owner_user_id"])
    op.create_index("idx_samples_experiment_id", "samples", ["experiment_id"])
    op.create_index("idx_samples_batch_id", "samples", ["batch_id"])
    op.create_index("idx_samples_qc_status", "samples", ["qc_status"])
    op.create_index("idx_batches_experiment_id", "batches", ["experiment_id"])
    op.create_index("idx_projects_org_id", "projects", ["organization_id"])
    op.create_index("idx_experiment_custom_fields_exp", "experiment_custom_fields", ["experiment_id"])
    op.create_index("idx_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("idx_audit_log_timestamp", "audit_log", ["timestamp"])

    # Phase 4 indexes
    op.create_index("idx_pipeline_runs_org", "pipeline_runs", ["organization_id"])
    op.create_index("idx_pipeline_runs_experiment", "pipeline_runs", ["experiment_id"])
    op.create_index("idx_pipeline_runs_status", "pipeline_runs", ["status"])
    op.create_index("idx_pipeline_runs_user", "pipeline_runs", ["submitted_by_user_id"])
    op.create_index("idx_pipeline_catalog_org", "pipeline_catalog", ["organization_id"])
    op.create_index("idx_pipeline_processes_run", "pipeline_processes", ["pipeline_run_id"])

    # Phase 3 indexes
    op.create_index("idx_notebook_sessions_user", "notebook_sessions", ["user_id"])
    op.create_index("idx_notebook_sessions_status", "notebook_sessions", ["status"])
    op.create_index("idx_notebook_sessions_org", "notebook_sessions", ["organization_id"])
    op.create_index("idx_slurm_jobs_user", "slurm_jobs", ["user_id"])
    op.create_index("idx_slurm_jobs_status", "slurm_jobs", ["status"])
    op.create_index("idx_slurm_jobs_org", "slurm_jobs", ["organization_id"])
    op.create_index("idx_slurm_jobs_experiment", "slurm_jobs", ["experiment_id"])
    op.create_index("idx_slurm_jobs_slurm_id", "slurm_jobs", ["slurm_job_id"])
    op.create_index("idx_user_quotas_user", "user_quotas", ["user_id"])

    # ---------------------------------------------------------------
    # Audit log role enforcement (ADR-009)
    # ---------------------------------------------------------------
    # Wrapped in try/except since the bioaf_app role may not exist
    # in test environments or local dev setups.
    try:
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bioaf_app")
        op.execute("REVOKE UPDATE, DELETE ON audit_log FROM bioaf_app")
        op.execute("REVOKE UPDATE, DELETE ON audit_log FROM PUBLIC")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bioaf_app")
    except Exception:
        # Role may not exist in test/dev environments - that's OK
        pass


def downgrade() -> None:
    # Drop Phase 4 indexes
    op.drop_index("idx_pipeline_processes_run")
    op.drop_index("idx_pipeline_catalog_org")
    op.drop_index("idx_pipeline_runs_user")
    op.drop_index("idx_pipeline_runs_status")
    op.drop_index("idx_pipeline_runs_experiment")
    op.drop_index("idx_pipeline_runs_org")

    # Drop Phase 4 tables
    op.drop_table("pipeline_processes")
    op.drop_table("pipeline_catalog")

    # Drop Phase 3 indexes
    op.drop_index("idx_user_quotas_user")
    op.drop_index("idx_slurm_jobs_slurm_id")
    op.drop_index("idx_slurm_jobs_experiment")
    op.drop_index("idx_slurm_jobs_org")
    op.drop_index("idx_slurm_jobs_status")
    op.drop_index("idx_slurm_jobs_user")
    op.drop_index("idx_notebook_sessions_org")
    op.drop_index("idx_notebook_sessions_status")
    op.drop_index("idx_notebook_sessions_user")

    # Drop indexes
    op.drop_index("idx_audit_log_timestamp")
    op.drop_index("idx_audit_log_entity")
    op.drop_index("idx_experiment_custom_fields_exp")
    op.drop_index("idx_projects_org_id")
    op.drop_index("idx_batches_experiment_id")
    op.drop_index("idx_samples_qc_status")
    op.drop_index("idx_samples_batch_id")
    op.drop_index("idx_samples_experiment_id")
    op.drop_index("idx_experiments_owner")
    op.drop_index("idx_experiments_status")
    op.drop_index("idx_experiments_project_id")
    op.drop_index("idx_experiments_org_id")

    # Drop in reverse dependency order
    op.drop_table("notebook_session_files")
    op.drop_table("user_quotas")
    op.drop_table("slurm_jobs")
    op.drop_table("notebook_sessions")
    op.drop_table("pipeline_run_samples")
    op.drop_table("pipeline_runs")
    op.drop_table("sample_files")
    op.drop_table("experiment_custom_fields")
    op.drop_table("samples")
    op.drop_table("batches")
    op.drop_table("experiments")
    op.drop_table("projects")
    op.drop_table("experiment_templates")
    op.drop_table("platform_config")
    op.drop_table("component_states")
    op.drop_table("audit_log")
    op.drop_table("terraform_runs")
    op.drop_table("verification_codes")
    op.drop_table("users")
    op.drop_table("organizations")
