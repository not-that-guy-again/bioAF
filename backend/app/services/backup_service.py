"""Backup monitoring service with status checks and restore operations."""

import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.services.event_bus import event_bus
from app.services.event_types import BACKUP_FAILURE

logger = logging.getLogger("bioaf.backup_service")


class BackupService:
    @staticmethod
    async def get_backup_status(org_id: int) -> dict:
        """Get backup status for each tier. Returns local/mock data for now;
        Commit 4 wires this to real GCS checks."""
        now = datetime.now(timezone.utc)
        tiers = []

        # PostgreSQL (pg_dump)
        tiers.append(
            {
                "tier": "postgres",
                "name": "PostgreSQL (pg_dump)",
                "last_backup": None,
                "size_bytes": None,
                "next_scheduled": None,
                "retention_days": settings.backup_postgres_retention_days,
                "status": "unknown",
                "versioning_enabled": None,
                "backup_count": 0,
            }
        )

        # GCS Object Versioning
        tiers.append(
            {
                "tier": "gcs",
                "name": "GCS Object Versioning",
                "last_backup": None,
                "size_bytes": None,
                "next_scheduled": None,
                "retention_days": None,
                "status": "unknown",
                "versioning_enabled": None,
                "backup_count": None,
            }
        )

        # Platform Config
        tiers.append(
            {
                "tier": "platform_config",
                "name": "Platform Configuration",
                "last_backup": None,
                "size_bytes": None,
                "next_scheduled": None,
                "retention_days": settings.backup_config_retention_days,
                "status": "unknown",
                "versioning_enabled": None,
                "backup_count": 0,
            }
        )

        # Terraform State
        tiers.append(
            {
                "tier": "terraform_state",
                "name": "Terraform State",
                "last_backup": None,
                "size_bytes": None,
                "next_scheduled": None,
                "retention_days": None,
                "status": "unknown",
                "versioning_enabled": None,
                "backup_count": None,
            }
        )

        all_healthy = all(t["status"] == "healthy" for t in tiers)
        any_error = any(t["status"] == "error" for t in tiers)
        if all_healthy:
            overall = "healthy"
        elif any_error:
            overall = "error"
        else:
            overall = "unknown"

        return {
            "tiers": tiers,
            "overall_status": overall,
        }

    @staticmethod
    async def get_config_snapshots(org_id: int, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        """List config backup snapshots. Wired to real GCS in Commit 4."""
        return [], 0

    @staticmethod
    async def get_config_snapshot_diff(org_id: int, snapshot_date: str) -> dict:
        """Diff between snapshot and current config."""
        return {
            "snapshot_date": snapshot_date,
            "compare_to": "current",
            "additions": [],
            "removals": [],
            "changes": [],
        }

    @staticmethod
    async def restore_config(org_id: int, snapshot_date: str) -> dict:
        """Restore platform config from snapshot."""
        logger.info("Config restore requested for org %d from snapshot %s", org_id, snapshot_date)
        return {"status": "initiated", "message": f"Config restore from {snapshot_date} initiated"}

    @staticmethod
    async def get_postgres_snapshots(org_id: int) -> tuple[list[dict], int]:
        """List postgres backup snapshots. Wired to real storage in Commit 5."""
        return [], 0

    @staticmethod
    async def check_backup_health(org_id: int) -> None:
        """Background health check: emit event if any backup is overdue >24h."""
        import asyncio

        status = await BackupService.get_backup_status(org_id)
        now = datetime.now(timezone.utc)

        for tier in status["tiers"]:
            if tier["last_backup"] and tier["status"] == "healthy":
                last = datetime.fromisoformat(tier["last_backup"])
                if (now - last).total_seconds() > 86400:
                    asyncio.create_task(
                        event_bus.emit(
                            BACKUP_FAILURE,
                            {
                                "event_type": BACKUP_FAILURE,
                                "org_id": org_id,
                                "entity_type": "backup",
                                "title": f"Backup overdue: {tier['name']}",
                                "message": f"Last backup was {(now - last).total_seconds() / 3600:.1f} hours ago",
                                "severity": "critical",
                                "summary": f"Backup overdue for {tier['name']}",
                            },
                        )
                    )
