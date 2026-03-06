"""Update experiment status enum to add pipeline_complete and reviewed.

Revision ID: 010
Revises: 009
Create Date: 2026-03-06

The experiment status is stored as VARCHAR with application-level
validation, so no DDL changes are needed. This migration exists
as a marker for the logical schema change (ADR-019).
"""

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Status is validated at the application level via EXPERIMENT_STATUSES
    # and EXPERIMENT_STATUS_TRANSITIONS in app/models/experiment.py.
    # New values: "pipeline_complete" and "reviewed" are added there.
    pass


def downgrade() -> None:
    # No DDL to revert. Application code handles the rollback.
    pass
