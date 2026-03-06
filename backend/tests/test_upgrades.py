import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_current_version(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/upgrades/current",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "current_version" in data
    assert data["app_name"] == "bioAF"


@pytest.mark.asyncio
async def test_get_current_version_viewer(client: AsyncClient, viewer_token: str):
    response = await client.get(
        "/api/upgrades/current",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_check_for_updates(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/upgrades/check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "current_version" in data
    assert "latest_version" in data
    assert "update_available" in data


@pytest.mark.asyncio
async def test_check_for_updates_forbidden_for_viewer(client: AsyncClient, viewer_token: str):
    response = await client.get(
        "/api/upgrades/check",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upgrade_history_empty(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/upgrades/history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["upgrades"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_start_upgrade(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/upgrades/start",
        json={"target_version": "1.0.0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["to_version"] == "1.0.0"
    assert "upgrade_id" in data


@pytest.mark.asyncio
async def test_confirm_upgrade(client: AsyncClient, admin_token: str):
    # Start first
    start_resp = await client.post(
        "/api/upgrades/start",
        json={"target_version": "1.0.0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    upgrade_id = start_resp.json()["upgrade_id"]

    # Confirm
    response = await client.post(
        f"/api/upgrades/{upgrade_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_rollback_upgrade(client: AsyncClient, admin_token: str):
    # Start and confirm first
    start_resp = await client.post(
        "/api/upgrades/start",
        json={"target_version": "1.0.0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    upgrade_id = start_resp.json()["upgrade_id"]

    await client.post(
        f"/api/upgrades/{upgrade_id}/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Rollback
    response = await client.post(
        f"/api/upgrades/{upgrade_id}/rollback",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_confirm_nonexistent_upgrade(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/upgrades/99999/confirm",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upgrade_history_after_upgrade(client: AsyncClient, admin_token: str):
    # Start an upgrade
    await client.post(
        "/api/upgrades/start",
        json={"target_version": "2.0.0"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        "/api/upgrades/history",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_version_check_service():
    """Test version check returns valid data."""
    from app.services.upgrade_service import UpgradeService

    result = await UpgradeService.check_for_updates(1)
    assert "current_version" in result
    assert "update_available" in result
