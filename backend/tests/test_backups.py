from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

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
async def test_trigger_postgres_backup_via_api(client: AsyncClient, admin_token: str):
    """Trigger endpoint calls run_postgres_backup and returns result."""
    with patch(
        "app.api.backups.BackupService.run_postgres_backup",
        new_callable=AsyncMock,
        return_value={
            "status": "completed",
            "filename": "pgdump-test.dump",
            "size_bytes": 1024,
            "duration_seconds": 1.5,
        },
    ):
        response = await client.post(
            "/api/backups/trigger/postgres",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


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


# --- Local mode backup status tests ---


@pytest.mark.asyncio
async def test_backup_status_local_postgres_no_backups():
    """With no backup files on disk, postgres tier shows unknown status."""
    from app.services.backup_service import BackupService

    with patch("app.services.backup_service.settings") as mock_settings:
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = "/tmp/bioaf-test-backups-nonexistent"
        mock_settings.backup_postgres_interval_hours = 24
        mock_settings.backup_postgres_retention_days = 14
        mock_settings.backup_config_retention_days = 30

        status = await BackupService.get_backup_status(1)
        postgres = next(t for t in status["tiers"] if t["tier"] == "postgres")
        assert postgres["status"] == "unknown"
        assert postgres["backup_count"] == 0


@pytest.mark.asyncio
async def test_backup_status_local_postgres_healthy(tmp_path):
    """With a recent backup file, postgres tier shows healthy."""
    from app.services.backup_service import BackupService

    pg_dir = tmp_path / "postgres"
    pg_dir.mkdir()
    now = datetime.now(timezone.utc)
    filename = f"pgdump-{now.strftime('%Y%m%d-%H%M%S')}.dump"
    dump_file = pg_dir / filename
    dump_file.write_bytes(b"fake dump data")

    with patch("app.services.backup_service.settings") as mock_settings:
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)
        mock_settings.backup_postgres_interval_hours = 24
        mock_settings.backup_postgres_retention_days = 14
        mock_settings.backup_config_retention_days = 30

        status = await BackupService.get_backup_status(1)
        postgres = next(t for t in status["tiers"] if t["tier"] == "postgres")
        assert postgres["status"] == "healthy"
        assert postgres["backup_count"] == 1
        assert postgres["last_backup"] is not None


@pytest.mark.asyncio
async def test_backup_status_local_postgres_warning(tmp_path):
    """With a backup older than 2x interval, postgres tier shows warning."""
    from app.services.backup_service import BackupService

    pg_dir = tmp_path / "postgres"
    pg_dir.mkdir()
    old = datetime.now(timezone.utc) - timedelta(hours=50)
    filename = f"pgdump-{old.strftime('%Y%m%d-%H%M%S')}.dump"
    dump_file = pg_dir / filename
    dump_file.write_bytes(b"old dump")

    with patch("app.services.backup_service.settings") as mock_settings:
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)
        mock_settings.backup_postgres_interval_hours = 24
        mock_settings.backup_postgres_retention_days = 14
        mock_settings.backup_config_retention_days = 30

        status = await BackupService.get_backup_status(1)
        postgres = next(t for t in status["tiers"] if t["tier"] == "postgres")
        assert postgres["status"] == "warning"


@pytest.mark.asyncio
async def test_backup_status_local_config_healthy(tmp_path):
    """With a recent config backup, platform_config tier shows healthy."""
    from app.services.backup_service import BackupService

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    now = datetime.now(timezone.utc)
    filename = f"config-{now.strftime('%Y%m%d-%H%M%S')}.json"
    (config_dir / filename).write_text('{"app_version": "0.3.15"}')

    with patch("app.services.backup_service.settings") as mock_settings:
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)
        mock_settings.backup_postgres_interval_hours = 24
        mock_settings.backup_postgres_retention_days = 14
        mock_settings.backup_config_retention_days = 30

        status = await BackupService.get_backup_status(1)
        config_tier = next(t for t in status["tiers"] if t["tier"] == "platform_config")
        assert config_tier["status"] == "healthy"
        assert config_tier["backup_count"] == 1


@pytest.mark.asyncio
async def test_config_snapshots_local(tmp_path):
    """Config snapshots list reads from local directory."""
    from app.services.backup_service import BackupService

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    for i in range(3):
        d = datetime.now(timezone.utc) - timedelta(days=i)
        filename = f"config-{d.strftime('%Y%m%d-%H%M%S')}.json"
        (config_dir / filename).write_text('{"test": true}')

    with patch("app.services.backup_service.settings") as mock_settings:
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)

        snapshots, total = await BackupService.get_config_snapshots(1)
        assert total == 3
        assert len(snapshots) == 3
        # Most recent first
        assert snapshots[0]["date"] >= snapshots[1]["date"]


# --- pg_dump tests ---


@pytest.mark.asyncio
async def test_run_postgres_backup_local(tmp_path):
    """pg_dump backup creates a .dump file in the local postgres directory."""
    from app.services.backup_service import BackupService

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"", b""))

    with (
        patch("app.services.backup_service.settings") as mock_settings,
        patch("app.services.backup_service.asyncio") as mock_asyncio,
    ):
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)
        mock_settings.backup_postgres_retention_days = 14
        mock_settings.database_url = "postgresql+asyncpg://bioaf_app:devpassword@postgres:5432/bioaf"
        mock_asyncio.create_subprocess_exec = AsyncMock(return_value=mock_process)

        result = await BackupService.run_postgres_backup(1)

    assert result["status"] == "completed"
    assert result["filename"].startswith("pgdump-")
    assert result["filename"].endswith(".dump")
    # Verify the subprocess was called with pg_dump
    call_args = mock_asyncio.create_subprocess_exec.call_args
    assert call_args[0][0] == "pg_dump"


@pytest.mark.asyncio
async def test_run_postgres_backup_failure(tmp_path):
    """pg_dump failure returns error status."""
    from app.services.backup_service import BackupService

    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate = AsyncMock(return_value=(b"", b"pg_dump: error: connection failed"))

    with (
        patch("app.services.backup_service.settings") as mock_settings,
        patch("app.services.backup_service.asyncio") as mock_asyncio,
    ):
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)
        mock_settings.backup_postgres_retention_days = 14
        mock_settings.database_url = "postgresql+asyncpg://bioaf_app:devpassword@postgres:5432/bioaf"
        mock_asyncio.create_subprocess_exec = AsyncMock(return_value=mock_process)

        result = await BackupService.run_postgres_backup(1)

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_rotate_local_backups(tmp_path):
    """Rotation deletes files older than retention period."""
    from app.services.backup_service import BackupService, _PG_FILENAME_RE

    pg_dir = tmp_path / "postgres"
    pg_dir.mkdir()

    # Create an old backup (20 days ago) and a recent one
    old = datetime.now(timezone.utc) - timedelta(days=20)
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    old_file = pg_dir / f"pgdump-{old.strftime('%Y%m%d-%H%M%S')}.dump"
    recent_file = pg_dir / f"pgdump-{recent.strftime('%Y%m%d-%H%M%S')}.dump"
    old_file.write_bytes(b"old")
    recent_file.write_bytes(b"recent")

    with patch("app.services.backup_service.settings") as mock_settings:
        mock_settings.compute_mode = "local"
        mock_settings.backup_local_dir = str(tmp_path)

        BackupService.rotate_local_backups(str(pg_dir), _PG_FILENAME_RE, retention_days=14)

    assert not old_file.exists()
    assert recent_file.exists()


@pytest.mark.asyncio
async def test_trigger_postgres_backup_forbidden_for_viewer(client: AsyncClient, viewer_token: str):
    response = await client.post(
        "/api/backups/trigger/postgres",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
