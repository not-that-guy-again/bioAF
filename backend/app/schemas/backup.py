from datetime import datetime

from pydantic import BaseModel


class BackupTierStatus(BaseModel):
    tier: str
    name: str
    last_backup: datetime | None = None
    size_bytes: int | None = None
    next_scheduled: datetime | None = None
    retention_days: int | None = None
    status: str = "unknown"
    pitr_window_hours: int | None = None
    versioning_enabled: bool | None = None


class BackupStatusResponse(BaseModel):
    tiers: list[BackupTierStatus]
    overall_status: str


class ConfigSnapshot(BaseModel):
    date: str
    size_bytes: int | None = None
    tier: str = "nightly"


class ConfigSnapshotListResponse(BaseModel):
    snapshots: list[ConfigSnapshot]
    total: int
    page: int
    page_size: int


class ConfigSnapshotDiff(BaseModel):
    snapshot_date: str
    compare_to: str
    additions: list[str] = []
    removals: list[str] = []
    changes: list[dict] = []


class RestoreRequest(BaseModel):
    confirmation_token: str
    restore_point: str | None = None


class RestoreResponse(BaseModel):
    status: str
    message: str


class BackupSettingsUpdate(BaseModel):
    cloud_sql_retention_days: int | None = None
    cloud_sql_pitr_days: int | None = None
    filestore_retention_days: int | None = None
    config_nightly_retention_days: int | None = None
    config_weekly_retention_weeks: int | None = None
    config_monthly_retention_months: int | None = None
