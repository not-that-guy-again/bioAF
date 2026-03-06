from datetime import datetime

from pydantic import BaseModel


class PartitionStatus(BaseModel):
    name: str
    max_nodes: int
    active_nodes: int
    idle_nodes: int
    queue_depth: int
    instance_type: str
    use_spot: bool


class ClusterStatusResponse(BaseModel):
    controller_status: str
    partitions: list[PartitionStatus]
    total_nodes: int
    active_nodes: int
    queue_depth: int
    cost_burn_rate_hourly: float | None = None


class QuotaResponse(BaseModel):
    user_id: int
    user_name: str | None = None
    user_email: str | None = None
    user_role: str | None = None
    cpu_hours_limit: int | None = None
    cpu_hours_used: float
    quota_reset_at: datetime


class QuotaUpdateRequest(BaseModel):
    cpu_hours_monthly_limit: int | None = None


class BudgetResponse(BaseModel):
    monthly_budget: float | None = None
    current_spend: float
    projected_spend: float
    threshold_alerts: list[str] = []
