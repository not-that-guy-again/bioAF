import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_backup_status(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/backups/status",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "tiers" in data
    assert "overall_status" in data
    assert len(data["tiers"]) == 4
    tier_names = {t["tier"] for t in data["tiers"]}
    assert tier_names == {"postgres", "gcs", "platform_config", "terraform_state"}


@pytest.mark.asyncio
async def test_get_backup_status_forbidden_for_viewer(client: AsyncClient, viewer_token: str):
    response = await client.get(
        "/api/backups/status",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_config_snapshots(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/backups/config-snapshots",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "snapshots" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_get_config_snapshot_diff(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/backups/config-snapshots/2025-01-01/diff",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "snapshot_date" in data
    assert "compare_to" in data


@pytest.mark.asyncio
async def test_restore_config(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/backups/restore/config",
        json={"confirmation_token": "CONFIRM"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "initiated"


@pytest.mark.asyncio
async def test_update_backup_settings(client: AsyncClient, admin_token: str):
    response = await client.put(
        "/api/backups/settings",
        json={"postgres_retention_days": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_update_backup_settings_enforces_postgres_minimum(client: AsyncClient, admin_token: str):
    response = await client.put(
        "/api/backups/settings",
        json={"postgres_retention_days": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_trigger_postgres_backup_stub(client: AsyncClient, admin_token: str):
    """Trigger endpoint returns 501 until pg_dump is implemented."""
    response = await client.post(
        "/api/backups/trigger/postgres",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_postgres_snapshots_empty(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/backups/postgres-snapshots",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["snapshots"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_backup_health_check(admin_user):
    """Test backup health check does not error."""
    from app.services.backup_service import BackupService

    await BackupService.check_backup_health(admin_user.organization_id)
