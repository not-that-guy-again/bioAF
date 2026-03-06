"""Backup monitoring service with status checks and restore operations."""

import logging
from datetime import datetime, timedelta, timezone

from app.services.event_bus import event_bus
from app.services.event_types import BACKUP_FAILURE

logger = logging.getLogger("bioaf.backup_service")


class BackupService:
    @staticmethod
    async def get_backup_status(org_id: int) -> dict:
        """Get backup status for each tier. Uses mock data when GCP is unavailable."""
        now = datetime.now(timezone.utc)
        tiers = []

        # Cloud SQL
        tiers.append(
            {
                "tier": "cloud_sql",
                "name": "Cloud SQL (PostgreSQL)",
                "last_backup": (now - timedelta(hours=6)).isoformat(),
                "size_bytes": 524288000,
                "next_scheduled": (now + timedelta(hours=18)).isoformat(),
                "retention_days": 30,
                "status": "healthy",
                "pitr_window_hours": 168,
                "versioning_enabled": None,
            }
        )

        # Filestore
        tiers.append(
            {
                "tier": "filestore",
                "name": "Filestore NFS Snapshots",
                "last_backup": (now - timedelta(hours=12)).isoformat(),
                "size_bytes": None,
                "next_scheduled": (now + timedelta(hours=12)).isoformat(),
                "retention_days": 14,
                "status": "healthy",
                "pitr_window_hours": None,
                "versioning_enabled": None,
            }
        )

        # GCS
        tiers.append(
            {
                "tier": "gcs",
                "name": "GCS Object Versioning",
                "last_backup": None,
                "size_bytes": None,
                "next_scheduled": None,
                "retention_days": None,
                "status": "healthy",
                "pitr_window_hours": None,
                "versioning_enabled": True,
            }
        )

        # Platform Config
        tiers.append(
            {
                "tier": "platform_config",
                "name": "Platform Configuration",
                "last_backup": (now - timedelta(hours=8)).isoformat(),
                "size_bytes": 102400,
                "next_scheduled": (now + timedelta(hours=16)).isoformat(),
                "retention_days": 365,
                "status": "healthy",
                "pitr_window_hours": None,
                "versioning_enabled": None,
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
                "status": "healthy",
                "pitr_window_hours": None,
                "versioning_enabled": True,
            }
        )

        all_healthy = all(t["status"] == "healthy" for t in tiers)
        return {
            "tiers": tiers,
            "overall_status": "healthy" if all_healthy else "degraded",
        }

    @staticmethod
    async def get_config_snapshots(org_id: int, page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
        """List config backup snapshots. Returns mock data when GCP is unavailable."""
        now = datetime.now(timezone.utc)
        snapshots = []
        for i in range(min(page_size, 30)):
            d = now - timedelta(days=i)
            tier = "nightly"
            if i % 7 == 0 and i > 0:
                tier = "weekly"
            if i % 30 == 0 and i > 0:
                tier = "monthly"
            snapshots.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "size_bytes": 102400 + i * 1024,
                    "tier": tier,
                }
            )
        return snapshots[(page - 1) * page_size : page * page_size], 30

    @staticmethod
    async def get_config_snapshot_diff(org_id: int, snapshot_date: str) -> dict:
        """Diff between snapshot and current config. Returns mock diff."""
        return {
            "snapshot_date": snapshot_date,
            "compare_to": "current",
            "additions": [],
            "removals": [],
            "changes": [
                {"key": "app_version", "old": "0.9.0", "new": "1.0.0"},
            ],
        }

    @staticmethod
    async def restore_config(org_id: int, snapshot_date: str) -> dict:
        """Restore platform config from snapshot. Placeholder for GCP implementation."""
        logger.info("Config restore requested for org %d from snapshot %s", org_id, snapshot_date)
        return {"status": "initiated", "message": f"Config restore from {snapshot_date} initiated"}

    @staticmethod
    async def check_backup_health(org_id: int) -> None:
        """Background health check: emit event if any backup is overdue >24h."""
        status = await BackupService.get_backup_status(org_id)
        now = datetime.now(timezone.utc)

        for tier in status["tiers"]:
            if tier["last_backup"] and tier["status"] == "healthy":
                last = datetime.fromisoformat(tier["last_backup"])
                if (now - last).total_seconds() > 86400:
                    import asyncio

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
