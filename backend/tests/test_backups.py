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
    assert len(data["tiers"]) == 5


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
    assert response.json()["status"] == "restored"


@pytest.mark.asyncio
async def test_restore_cloudsql(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/backups/restore/cloudsql",
        json={"confirmation_token": "CONFIRM"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "initiated"


@pytest.mark.asyncio
async def test_restore_filestore(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/backups/restore/filestore",
        json={"confirmation_token": "CONFIRM"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "initiated"


@pytest.mark.asyncio
async def test_update_backup_settings(client: AsyncClient, admin_token: str):
    response = await client.put(
        "/api/backups/settings",
        json={"cloud_sql_retention_days": 60},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_update_backup_settings_enforces_minimums(client: AsyncClient, admin_token: str):
    response = await client.put(
        "/api/backups/settings",
        json={"cloud_sql_pitr_days": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_backup_health_check():
    """Test backup health check does not error."""
    from app.services.backup_service import BackupService
    await BackupService.check_backup_health()
