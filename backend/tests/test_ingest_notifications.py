"""Tests for ingest and trigger notification emissions."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.models.file import File
from app.models.ingest_event import IngestEvent
from app.models.pipeline_catalog_entry import PipelineCatalogEntry
from app.schemas.pipeline_trigger import (
    BudgetTriggerConfig,
    EventTriggerConfig,
    PipelineTriggerCreate,
)
from app.services.event_types import (
    AUTO_RUN_SUBMITTED,
    DUPLICATE_FILE,
    FILES_CATALOGED,
    RUN_QUEUED_BUDGET,
    UNMATCHED_FILE,
)
from app.services.ingest_service import process_ingest_event
from app.services.trigger_service import TriggerService


@pytest_asyncio.fixture
async def org_user(client, admin_token, session):
    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()
    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user = result.fetchone()
    return org.id, user.id


@pytest.mark.asyncio
async def test_cataloged_file_emits_files_cataloged(client, admin_token, session, org_user):
    """Cataloged files emit FILES_CATALOGED event."""
    org_id, user_id = org_user
    emitted = []

    async def capture_emit(event_type, data):
        emitted.append(event_type)

    with patch("app.services.ingest_service.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock(side_effect=capture_emit)
        # Create a naming profile so the file can be matched
        from app.models.naming_profile import NamingProfile

        profile = NamingProfile(
            organization_id=org_id,
            name="Test Notify Profile",
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
            ],
            status="active",
            created_by=user_id,
        )
        session.add(profile)

        from app.models.project import Project

        project = Project(organization_id=org_id, name="NotifyProject")
        session.add(project)
        await session.flush()
        await session.commit()

        event = await process_ingest_event(
            filename="NotifyProject.fastq",
            source_bucket="test-bucket",
            source_path="incoming/NotifyProject.fastq",
            org_id=org_id,
            db=session,
            user_id=user_id,
        )
        await session.commit()

        assert event.ingest_status == "cataloged"
        assert FILES_CATALOGED in emitted


@pytest.mark.asyncio
async def test_unmatched_file_emits_unmatched(client, admin_token, session, org_user):
    """Files not matching any profile emit UNMATCHED_FILE event."""
    org_id, user_id = org_user
    emitted = []

    async def capture_emit(event_type, data):
        emitted.append(event_type)

    with patch("app.services.ingest_service.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock(side_effect=capture_emit)
        event = await process_ingest_event(
            filename="random_unmatched_file.xyz",
            source_bucket="test-bucket",
            source_path="incoming/random_unmatched_file.xyz",
            org_id=org_id,
            db=session,
            user_id=user_id,
        )
        await session.commit()

        assert event.ingest_status == "unmatched"
        assert UNMATCHED_FILE in emitted


@pytest.mark.asyncio
async def test_duplicate_file_emits_duplicate(client, admin_token, session, org_user):
    """Duplicate file detection emits DUPLICATE_FILE event."""
    org_id, user_id = org_user

    # Create an existing file with md5
    existing = File(
        organization_id=org_id,
        gcs_uri="gs://bucket/existing.fastq",
        filename="existing.fastq",
        file_type="fastq",
        md5_checksum="abc123duplicate",
        ingest_source="manual",
    )
    session.add(existing)
    await session.flush()
    await session.commit()

    emitted = []

    async def capture_emit(event_type, data):
        emitted.append(event_type)

    with patch("app.services.ingest_service.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock(side_effect=capture_emit)
        event = await process_ingest_event(
            filename="existing.fastq",
            source_bucket="test-bucket",
            source_path="incoming/existing.fastq",
            org_id=org_id,
            db=session,
            user_id=user_id,
            content_md5="abc123duplicate",
        )
        await session.commit()

        assert event.ingest_status == "duplicate"
        assert DUPLICATE_FILE in emitted


@pytest.mark.asyncio
async def test_trigger_submitted_emits_auto_run(client, admin_token, session, org_user, monkeypatch):
    """Trigger submission within budget emits AUTO_RUN_SUBMITTED."""
    monkeypatch.setenv("BIOAF_MOCK_MONTHLY_SPEND", "0")
    monkeypatch.setenv("BIOAF_MONTHLY_BUDGET", "500.0")
    org_id, user_id = org_user

    pipeline = PipelineCatalogEntry(
        organization_id=org_id,
        pipeline_key="notify-test-pipeline",
        name="Notify Pipeline",
        source_type="github",
        source_url="https://example.com",
        version="1.0",
    )
    session.add(pipeline)
    await session.flush()

    data = PipelineTriggerCreate(
        pipeline_id=pipeline.id,
        trigger_mode="event_driven",
        event_config=EventTriggerConfig(file_types=["fastq"], batching_window_minutes=0),
        budget_config=BudgetTriggerConfig(auto_queue_when_over_budget=True),
    )
    await TriggerService.create_trigger(session, org_id, user_id, data)
    await session.commit()

    file = File(
        organization_id=org_id,
        gcs_uri="gs://b/notify.fastq",
        filename="notify.fastq",
        file_type="fastq",
        ingest_source="auto_ingest",
    )
    session.add(file)
    await session.flush()

    ev = IngestEvent(
        file_id=file.id,
        source_bucket="b",
        source_path="notify.fastq",
        ingest_status="cataloged",
    )
    session.add(ev)
    await session.flush()

    emitted = []

    async def capture_emit(event_type, data):
        emitted.append(event_type)

    with patch("app.services.trigger_service.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock(side_effect=capture_emit)
        evaluations = await TriggerService.evaluate_event_triggers(ev, session)
        await session.commit()

    assert len(evaluations) >= 1
    submitted = [e for e in evaluations if e.result == "submitted"]
    assert len(submitted) >= 1
    assert AUTO_RUN_SUBMITTED in emitted

    TriggerService.clear_batches()


@pytest.mark.asyncio
async def test_trigger_queued_emits_budget_event(client, admin_token, session, org_user, monkeypatch):
    """Over-budget trigger queuing emits RUN_QUEUED_BUDGET."""
    monkeypatch.setenv("BIOAF_MOCK_MONTHLY_SPEND", "500.0")
    monkeypatch.setenv("BIOAF_MONTHLY_BUDGET", "500.0")
    org_id, user_id = org_user

    pipeline = PipelineCatalogEntry(
        organization_id=org_id,
        pipeline_key="budget-notify-pipeline",
        name="Budget Notify Pipeline",
        source_type="github",
        source_url="https://example.com",
        version="1.0",
    )
    session.add(pipeline)
    await session.flush()

    data = PipelineTriggerCreate(
        pipeline_id=pipeline.id,
        trigger_mode="event_driven",
        event_config=EventTriggerConfig(file_types=["fastq"], batching_window_minutes=0),
        budget_config=BudgetTriggerConfig(auto_queue_when_over_budget=True),
    )
    await TriggerService.create_trigger(session, org_id, user_id, data)
    await session.commit()

    file = File(
        organization_id=org_id,
        gcs_uri="gs://b/budget-notify.fastq",
        filename="budget-notify.fastq",
        file_type="fastq",
        ingest_source="auto_ingest",
    )
    session.add(file)
    await session.flush()

    ev = IngestEvent(
        file_id=file.id,
        source_bucket="b",
        source_path="budget-notify.fastq",
        ingest_status="cataloged",
    )
    session.add(ev)
    await session.flush()

    emitted = []

    async def capture_emit(event_type, data):
        emitted.append(event_type)

    with patch("app.services.trigger_service.event_bus") as mock_bus:
        mock_bus.emit = AsyncMock(side_effect=capture_emit)
        evaluations = await TriggerService.evaluate_event_triggers(ev, session)
        await session.commit()

    assert len(evaluations) >= 1
    queued = [e for e in evaluations if e.result == "queued"]
    assert len(queued) >= 1
    assert RUN_QUEUED_BUDGET in emitted

    TriggerService.clear_batches()
