from datetime import datetime

from pydantic import BaseModel


class BucketStats(BaseModel):
    bucket_name: str
    total_bytes: int
    object_count: int
    by_storage_class: dict[str, int] = {}
    cost_estimate_monthly: float


class LifecyclePolicyStatus(BaseModel):
    bucket_name: str
    rules: list[dict] = []
    enabled: bool = False


class StorageDashboard(BaseModel):
    buckets: list[BucketStats]
    total_bytes: int
    total_cost_estimate_monthly: float
    lifecycle_policies: list[LifecyclePolicyStatus] = []
    last_updated: datetime
