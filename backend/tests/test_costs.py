import pytest
from decimal import Decimal
from datetime import date, datetime, timezone

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_cost_summary(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/costs/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "current_month_spend" in data
    assert "daily_trend" in data
    assert "breakdown_by_component" in data
    assert "monthly_budget" in data
    assert "projected_month_end" in data


@pytest.mark.asyncio
async def test_get_cost_summary_forbidden_for_viewer(client: AsyncClient, viewer_token: str):
    response = await client.get(
        "/api/costs/summary",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_cost_history(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/costs/history?start_date=2025-01-01&end_date=2025-12-31",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "records" in data
    assert "total_amount" in data


@pytest.mark.asyncio
async def test_get_budget_config_default(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/costs/budget",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["threshold_50_enabled"] is True
    assert data["threshold_80_enabled"] is True
    assert data["threshold_100_enabled"] is True
    assert data["scale_to_zero_on_100"] is False


@pytest.mark.asyncio
async def test_update_budget_config(client: AsyncClient, admin_token: str):
    response = await client.put(
        "/api/costs/budget",
        json={"monthly_budget": "5000.00", "scale_to_zero_on_100": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["monthly_budget"] == "5000.00"
    assert data["scale_to_zero_on_100"] is True


@pytest.mark.asyncio
async def test_trigger_billing_sync(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/costs/sync",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sync_initiated"


@pytest.mark.asyncio
async def test_cost_summary_with_records(client: AsyncClient, admin_token: str, admin_user, session):
    """Insert cost records and verify summary includes them."""
    from app.models.cost_record import CostRecord

    now = datetime.now(timezone.utc)
    month_start = date(now.year, now.month, 1)

    for i, component in enumerate(["compute", "storage", "network"]):
        record = CostRecord(
            organization_id=admin_user.organization_id,
            record_date=month_start,
            component=component,
            cost_amount=Decimal(f"{(i + 1) * 100}.00"),
        )
        session.add(record)
    await session.flush()
    await session.commit()

    response = await client.get(
        "/api/costs/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["current_month_spend"]) >= 600.0
    assert len(data["breakdown_by_component"]) >= 3


@pytest.mark.asyncio
async def test_cost_history_with_records(client: AsyncClient, admin_token: str, admin_user, session):
    """Insert cost records and verify history returns them."""
    from app.models.cost_record import CostRecord

    record = CostRecord(
        organization_id=admin_user.organization_id,
        record_date=date(2025, 6, 15),
        component="compute",
        cost_amount=Decimal("250.00"),
    )
    session.add(record)
    await session.flush()
    await session.commit()

    response = await client.get(
        "/api/costs/history?start_date=2025-06-01&end_date=2025-06-30",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert float(data["total_amount"]) >= 250.0


@pytest.mark.asyncio
async def test_budget_threshold_check(admin_user, session):
    """Test budget threshold checking emits no errors."""
    from app.services.cost_service import CostService

    await CostService.check_budget_thresholds(session, admin_user.organization_id)
