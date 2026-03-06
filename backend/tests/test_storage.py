import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_storage_stats(client, admin_token):
    """Storage stats endpoint returns cached or refreshed data."""
    mock_stats = {
        "buckets": [
            {"bucket_name": "bioaf-raw", "total_bytes": 10737418240, "object_count": 100,
             "by_storage_class": {"STANDARD": 10737418240}, "cost_estimate_monthly": 0.2},
        ],
        "total_bytes": 10737418240,
        "total_cost_estimate_monthly": 0.2,
        "lifecycle_policies": [],
        "last_updated": "2026-01-01T00:00:00",
    }

    with patch(
        "app.services.storage_service.StorageService.get_storage_stats",
        new_callable=AsyncMock,
        return_value=mock_stats,
    ):
        resp = await client.get(
            "/api/storage/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_bytes"] == 10737418240
    assert len(data["buckets"]) == 1


@pytest.mark.asyncio
async def test_viewer_cannot_refresh_storage(client, viewer_token):
    """Only admins can force-refresh storage stats."""
    resp = await client.post(
        "/api/storage/refresh",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_lifecycle_policies(client, admin_token):
    """Lifecycle policies endpoint returns policy data."""
    with patch(
        "app.services.storage_service.StorageService.get_lifecycle_policies",
        new_callable=AsyncMock,
        return_value=[{"bucket_name": "bioaf-raw", "rules": [], "enabled": False}],
    ):
        resp = await client.get(
            "/api/storage/lifecycle",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["policies"]) == 1


# --- Cost calculation unit test ---

def test_storage_cost_rates():
    """Verify cost rates are reasonable."""
    from app.services.storage_service import STORAGE_COSTS

    assert STORAGE_COSTS["STANDARD"] > STORAGE_COSTS["NEARLINE"]
    assert STORAGE_COSTS["NEARLINE"] > STORAGE_COSTS["COLDLINE"]
    assert STORAGE_COSTS["COLDLINE"] > STORAGE_COSTS["ARCHIVE"]
    # 100 GB Standard should cost ~$2/month
    cost_100gb = 100 * STORAGE_COSTS["STANDARD"]
    assert 1.0 < cost_100gb < 5.0
