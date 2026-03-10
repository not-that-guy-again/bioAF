import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_pipeline_trigger_creation(client, admin_token, session):
    """Test PipelineTrigger model instantiation with valid data."""
    from app.models.pipeline_trigger import PipelineTrigger
    from app.models.pipeline_catalog_entry import PipelineCatalogEntry

    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()
    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user = result.fetchone()

    pipeline = PipelineCatalogEntry(
        organization_id=org.id,
        pipeline_key="nf-core-scrnaseq",
        name="nf-core/scrnaseq",
        source_type="github",
        source_url="https://github.com/nf-core/scrnaseq",
        version="2.0.0",
    )
    session.add(pipeline)
    await session.flush()

    trigger = PipelineTrigger(
        pipeline_id=pipeline.id,
        organization_id=org.id,
        trigger_mode="event_driven",
        event_config={"file_types": ["fastq", "fastq.gz"], "batching_window_minutes": 15},
        parameter_defaults={"genome": "GRCh38"},
        budget_config={"require_approval_on_budget_warning": True},
        enabled=True,
        created_by=user.id,
    )
    session.add(trigger)
    await session.flush()
    assert trigger.id is not None
    assert trigger.trigger_mode == "event_driven"
    assert trigger.enabled is True


@pytest.mark.asyncio
async def test_pipeline_trigger_mode_values(client, admin_token, session):
    """Test trigger_mode accepts manual, event_driven, and scheduled."""
    from app.models.pipeline_trigger import PipelineTrigger
    from app.models.pipeline_catalog_entry import PipelineCatalogEntry

    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()
    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user = result.fetchone()

    pipeline = PipelineCatalogEntry(
        organization_id=org.id,
        pipeline_key="nf-core-rnaseq",
        name="nf-core/rnaseq",
        source_type="github",
        source_url="https://github.com/nf-core/rnaseq",
        version="3.0.0",
    )
    session.add(pipeline)
    await session.flush()

    for mode in ["manual", "event_driven", "scheduled"]:
        trigger = PipelineTrigger(
            pipeline_id=pipeline.id,
            organization_id=org.id,
            trigger_mode=mode,
            enabled=True,
            created_by=user.id,
        )
        session.add(trigger)
        await session.flush()
        assert trigger.trigger_mode == mode


@pytest.mark.asyncio
async def test_trigger_evaluation_creation(client, admin_token, session):
    """Test TriggerEvaluation model instantiation."""
    from app.models.pipeline_trigger import PipelineTrigger
    from app.models.trigger_evaluation import TriggerEvaluation
    from app.models.pipeline_catalog_entry import PipelineCatalogEntry

    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()
    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user = result.fetchone()

    pipeline = PipelineCatalogEntry(
        organization_id=org.id,
        pipeline_key="test-pipeline",
        name="test-pipeline",
        source_type="github",
        source_url="https://example.com",
        version="1.0",
    )
    session.add(pipeline)
    await session.flush()

    trigger = PipelineTrigger(
        pipeline_id=pipeline.id,
        organization_id=org.id,
        trigger_mode="event_driven",
        enabled=True,
        created_by=user.id,
    )
    session.add(trigger)
    await session.flush()

    evaluation = TriggerEvaluation(
        trigger_id=trigger.id,
        evaluation_type="file_ingest",
        matched_files=[1, 2, 3],
        budget_check_result={"estimated_cost": 5.50, "decision": "within_budget"},
        result="submitted",
    )
    session.add(evaluation)
    await session.flush()
    assert evaluation.id is not None
    assert evaluation.result == "submitted"
    assert evaluation.matched_files == [1, 2, 3]


@pytest.mark.asyncio
async def test_pipeline_cost_history_creation(client, admin_token, session):
    """Test PipelineCostHistory model with JSONB and Decimal fields."""
    from app.models.pipeline_cost_history import PipelineCostHistory
    from app.models.pipeline_run import PipelineRun
    from decimal import Decimal

    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()

    run = PipelineRun(
        organization_id=org.id,
        pipeline_name="nf-core/scrnaseq",
        status="completed",
    )
    session.add(run)
    await session.flush()

    cost = PipelineCostHistory(
        pipeline_run_id=run.id,
        pipeline_name="nf-core/scrnaseq",
        input_file_count=4,
        input_total_bytes=1_000_000_000,
        estimated_cost=Decimal("5.00"),
        actual_cost=Decimal("4.75"),
        estimation_error_pct=Decimal("-5.00"),
    )
    session.add(cost)
    await session.flush()
    assert cost.id is not None
    assert cost.pipeline_name == "nf-core/scrnaseq"
    assert cost.actual_cost == Decimal("4.75")
