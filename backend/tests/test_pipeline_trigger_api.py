"""Tests for pipeline trigger API endpoints."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def pipeline_id(client, admin_token):
    """Create a pipeline catalog entry and return its ID."""
    from sqlalchemy import text
    # Use the client's internal test infrastructure to create a pipeline
    # We'll use a direct DB approach via the admin API
    # Since there's no pipeline creation endpoint, we need to be creative
    # Actually, pipeline triggers reference pipeline_catalog.id
    # Let's just create one via the test session
    return None  # Will create via session in tests


@pytest.mark.asyncio
async def test_create_trigger(client, admin_token, session):
    from app.models.pipeline_catalog_entry import PipelineCatalogEntry
    from sqlalchemy import text

    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()

    pipeline = PipelineCatalogEntry(
        organization_id=org.id,
        pipeline_key="api-test-pipeline",
        name="API Test Pipeline",
        source_type="github",
        source_url="https://example.com",
        version="1.0",
    )
    session.add(pipeline)
    await session.flush()
    await session.commit()

    response = await client.post(
        "/api/pipeline-triggers",
        json={
            "pipeline_id": pipeline.id,
            "trigger_mode": "event_driven",
            "event_config": {"file_types": ["fastq"], "batching_window_minutes": 15},
            "enabled": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["trigger_mode"] == "event_driven"
    assert data["enabled"] is True
    return data["id"]


@pytest.mark.asyncio
async def test_list_triggers(client, admin_token, session):
    response = await client.get(
        "/api/pipeline-triggers",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_queue_listing(client, admin_token):
    response = await client.get(
        "/api/pipeline-triggers/queue",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_cost_estimate(client, admin_token):
    response = await client.post(
        "/api/pipeline-runs/estimate-cost",
        json={"pipeline_name": "test", "input_file_count": 4, "input_total_bytes": 1000000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "estimated_cost" in data
    assert "budget_check" in data


@pytest.mark.asyncio
async def test_budget_status(client, admin_token):
    response = await client.get(
        "/api/budget/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "current_month_spend" in data
    assert "monthly_budget" in data
    assert "remaining" in data


@pytest.mark.asyncio
async def test_viewer_denied(client, viewer_token):
    response = await client.get(
        "/api/pipeline-triggers",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
