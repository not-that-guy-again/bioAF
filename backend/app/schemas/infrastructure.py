from pydantic import BaseModel


class NodePoolStatus(BaseModel):
    name: str
    machine_type: str = "unknown"
    min_nodes: int = 0
    max_nodes: int = 0
    current_nodes: int = 0
    status: str = "unknown"
    spot: bool = False


class InfraComputeStatusResponse(BaseModel):
    controller_status: str
    node_pools: list[NodePoolStatus]
    total_nodes: int
    active_nodes: int
    queue_depth: int
    health: str = "unknown"


class NodePoolMetrics(BaseModel):
    name: str
    cpu_utilization_pct: float = 0.0
    memory_utilization_pct: float = 0.0
    cost_rate_hourly: float = 0.0


class InfraComputeMetricsResponse(BaseModel):
    cpu_utilization_pct: float
    memory_utilization_pct: float
    cost_burn_rate_hourly: float
    node_pools: list[NodePoolMetrics]


class BucketMetrics(BaseModel):
    name: str
    size_gb: float
    object_count: int
    storage_class: str
    cost_monthly_usd: float


class InfraStorageMetricsResponse(BaseModel):
    buckets: list[BucketMetrics]
    total_size_gb: float
    total_cost_monthly_usd: float


class ComputeStackResponse(BaseModel):
    compute_stack: str


class ComponentDefinitionResponse(BaseModel):
    key: str
    name: str
    category: str
    description: str
    cost_estimate: str
    dependencies: list[str]
    configurable_fields: list[dict]
    status: str  # "available" or "coming_soon"


class ComponentsListResponse(BaseModel):
    compute_stack: str
    components: list[ComponentDefinitionResponse]


class StorageBucketInfo(BaseModel):
    name: str
    purpose: str
    is_ingest: bool
    size_gb: float
    object_count: int


class StorageBucketsResponse(BaseModel):
    org_slug: str
    buckets: list[StorageBucketInfo]
