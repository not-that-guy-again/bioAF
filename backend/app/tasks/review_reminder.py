"""Background task: remind users about unreviewed pipeline runs."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_bus import event_bus
from app.services.event_types import PIPELINE_RUN_REVIEW_REMINDER
from app.services.pipeline_review_service import PipelineReviewService

logger = logging.getLogger("bioaf.review_reminder")


async def check_unreviewed_runs(session: AsyncSession, hours_threshold: int = 72) -> int:
    """Find unreviewed pipeline runs older than threshold and emit reminders.

    Returns the number of reminders emitted.
    """
    unreviewed = await PipelineReviewService.get_unreviewed_runs(session, hours_threshold)

    count = 0
    for run in unreviewed:
        hours_since = 0
        if run.completed_at:
            hours_since = int((datetime.now(timezone.utc) - run.completed_at).total_seconds() / 3600)

        experiment_name = run.experiment.name if run.experiment else "Unknown"

        await event_bus.emit(
            PIPELINE_RUN_REVIEW_REMINDER,
            {
                "event_type": PIPELINE_RUN_REVIEW_REMINDER,
                "org_id": run.organization_id,
                "user_id": run.submitted_by_user_id,
                "target_user_id": run.submitted_by_user_id,
                "entity_type": "pipeline_run",
                "entity_id": run.id,
                "title": f"Pipeline run awaiting review ({hours_since}h)",
                "message": (
                    f"Pipeline run {run.id} for experiment '{experiment_name}' "
                    f"completed {hours_since} hours ago and has not been reviewed."
                ),
                "severity": "warning",
                "summary": f"Unreviewed pipeline run {run.id} ({hours_since}h old)",
                "metadata": {
                    "pipeline_run_id": run.id,
                    "experiment_id": run.experiment_id,
                    "hours_since_completion": hours_since,
                },
            },
        )
        count += 1

    if count > 0:
        logger.info("Sent %d review reminder(s)", count)

    return count
