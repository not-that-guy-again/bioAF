"""Test 15: Ingest pipeline triggers pipeline evaluation after successful ingest."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text


async def _seed_config(session):
    defaults = {
        "storage_deployed": "true",
        "ingest_bucket_name": "bioaf-ingest-testorg",
        "raw_bucket_name": "bioaf-raw-testorg",
        "ingest_cleanup_policy": "delete_after_copy",
        "auto_ingest_enabled": "true",
        "pubsub_topic_name": "bioaf-ingest-events-testorg",
        "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
    }
    for key, value in defaults.items():
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ).bindparams(k=key, v=value)
        )
    await session.commit()


@pytest_asyncio.fixture
async def _setup_profile(client, admin_token, session):
    await _seed_config(session)
    await client.post(
        "/api/naming-profiles",
        json={
            "name": "Trigger Test Profile",
            "segments": [
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "experiment_code", "required": True},
                {"position": 2, "field": "sample_id", "required": True},
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )


@pytest.mark.asyncio
async def test_ingest_triggers_pipeline_evaluation(client, admin_token, session, _setup_profile):
    """After a file is ingested, the trigger evaluation engine is invoked."""
    from app.services.ingest_service import process_ingest_event

    mock_evaluate = AsyncMock(return_value=[])
    mock_copy = AsyncMock(return_value="gs://bioaf-raw-testorg/experiments/1/P1_E1_S1.fastq.gz")
    mock_cleanup = AsyncMock()

    with (
        patch("app.services.ingest_service.copy_to_raw_bucket", mock_copy),
        patch("app.services.ingest_service.cleanup_ingest_file", mock_cleanup),
        patch(
            "app.services.trigger_service.TriggerService.evaluate_event_triggers",
            mock_evaluate,
        ),
    ):
        event = await process_ingest_event(
            filename="P1_E1_S1.fastq.gz",
            source_bucket="bioaf-ingest-testorg",
            source_path="P1_E1_S1.fastq.gz",
            org_id=1,
            db=session,
            user_id=None,
            file_size_bytes=1048576,
            content_md5="trigger_test_md5",
            ingest_source="auto_ingest",
        )
        await session.commit()

    assert event.ingest_status == "cataloged"
    mock_evaluate.assert_called_once()
    # The first argument should be the ingest event
    call_args = mock_evaluate.call_args
    assert call_args[0][0].id == event.id
