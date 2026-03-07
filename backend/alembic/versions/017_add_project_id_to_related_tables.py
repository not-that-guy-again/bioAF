"""Add project_id FK to pipeline_runs, files, and notebook_sessions.

Revision ID: 017
Revises: 016
Create Date: 2026-03-06

Enables pipeline runs, files, and notebook sessions to be scoped
to a project in addition to (or instead of) an experiment.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pipeline_runs", sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True))
    op.create_index("idx_pipeline_runs_project_id", "pipeline_runs", ["project_id"])

    op.add_column("files", sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True))
    op.create_index("idx_files_project_id", "files", ["project_id"])

    op.add_column(
        "notebook_sessions", sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True)
    )
    op.create_index("idx_notebook_sessions_project_id", "notebook_sessions", ["project_id"])


def downgrade() -> None:
    op.drop_index("idx_notebook_sessions_project_id", table_name="notebook_sessions")
    op.drop_column("notebook_sessions", "project_id")

    op.drop_index("idx_files_project_id", table_name="files")
    op.drop_column("files", "project_id")

    op.drop_index("idx_pipeline_runs_project_id", table_name="pipeline_runs")
    op.drop_column("pipeline_runs", "project_id")
