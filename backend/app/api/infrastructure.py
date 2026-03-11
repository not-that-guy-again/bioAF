from fastapi import APIRouter, Depends

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.dependencies import require_role
from app.adapters.registry import get_compute_adapter, get_storage_adapter
from app.models.organization import Organization
from app.schemas.infrastructure import (
    InfraComputeStatusResponse,
    InfraComputeMetricsResponse,
    InfraStorageMetricsResponse,
    ComputeStackResponse,
    NodePoolStatus,
    NodePoolMetrics,
    BucketMetrics,
    ComponentDefinitionResponse,
    ComponentsListResponse,
    StorageBucketInfo,
    StorageBucketsResponse,
)

router = APIRouter(prefix="/api/v1/infrastructure", tags=["infrastructure"])


@router.get("/compute/status", response_model=InfraComputeStatusResponse)
async def get_compute_status(
    current_user: dict = require_role("admin", "comp_bio"),
):
    """Returns cluster status from the active compute adapter."""
    compute_adapter = get_compute_adapter()
    status = await compute_adapter.get_cluster_status()

    node_pools = []
    for pool in status.get("node_pools", []):
        node_pools.append(
            NodePoolStatus(
                name=pool.get("name", "unknown"),
                machine_type=pool.get("machine_type", "unknown"),
                min_nodes=pool.get("min_nodes", 0),
                max_nodes=pool.get("max_nodes", 0),
                current_nodes=pool.get("current_nodes", 0),
                status=pool.get("status", "unknown"),
                spot=pool.get("spot", False),
            )
        )

    return InfraComputeStatusResponse(
        controller_status=status.get("controller_status", "unknown"),
        node_pools=node_pools,
        total_nodes=status.get("total_nodes", 0),
        active_nodes=status.get("active_nodes", 0),
        queue_depth=status.get("queue_depth", 0),
        health=status.get("health", "unknown"),
    )


@router.get("/compute/metrics", response_model=InfraComputeMetricsResponse)
async def get_compute_metrics(
    current_user: dict = require_role("admin", "comp_bio"),
):
    """Returns cluster metrics from the active compute adapter."""
    compute_adapter = get_compute_adapter()
    metrics = await compute_adapter.get_cluster_metrics()

    node_pools = []
    for pool in metrics.get("node_pools", []):
        node_pools.append(
            NodePoolMetrics(
                name=pool.get("name", "unknown"),
                cpu_utilization_pct=pool.get("cpu_utilization_pct", 0.0),
                memory_utilization_pct=pool.get("memory_utilization_pct", 0.0),
                cost_rate_hourly=pool.get("cost_rate_hourly", 0.0),
            )
        )

    return InfraComputeMetricsResponse(
        cpu_utilization_pct=metrics.get("cpu_utilization_pct", 0.0),
        memory_utilization_pct=metrics.get("memory_utilization_pct", 0.0),
        cost_burn_rate_hourly=metrics.get("cost_burn_rate_hourly", 0.0),
        node_pools=node_pools,
    )


@router.get("/storage/metrics", response_model=InfraStorageMetricsResponse)
async def get_storage_metrics(
    current_user: dict = require_role("admin", "comp_bio"),
):
    """Returns storage metrics from the active storage adapter."""
    storage_adapter = get_storage_adapter()
    metrics = await storage_adapter.get_storage_metrics()

    buckets = []
    for bucket in metrics.get("buckets", []):
        buckets.append(
            BucketMetrics(
                name=bucket.get("name", "unknown"),
                size_gb=bucket.get("size_gb", 0.0),
                object_count=bucket.get("object_count", 0),
                storage_class=bucket.get("storage_class", "STANDARD"),
                cost_monthly_usd=bucket.get("cost_monthly_usd", 0.0),
            )
        )

    return InfraStorageMetricsResponse(
        buckets=buckets,
        total_size_gb=metrics.get("total_size_gb", 0.0),
        total_cost_monthly_usd=metrics.get("total_cost_monthly_usd", 0.0),
    )


@router.get("/compute/stack", response_model=ComputeStackResponse)
async def get_compute_stack(
    current_user: dict = require_role("admin", "comp_bio"),
    session: AsyncSession = Depends(get_session),
):
    """Returns the current compute stack selection."""
    result = await session.execute(text("SELECT value FROM platform_config WHERE key = 'compute_stack'"))
    row = result.first()
    return ComputeStackResponse(compute_stack=row[0] if row else "kubernetes")


@router.get("/components", response_model=ComponentsListResponse)
async def get_components(
    current_user: dict = require_role("admin", "comp_bio"),
    session: AsyncSession = Depends(get_session),
):
    """Returns component catalog filtered by active compute stack."""
    from app.services.component_service import COMPONENT_CATALOG

    result = await session.execute(text("SELECT value FROM platform_config WHERE key = 'compute_stack'"))
    row = result.first()
    compute_stack = row[0] if row else "kubernetes"

    components = []
    for key, defn in COMPONENT_CATALOG.items():
        comp_stack = defn.get("compute_stack")
        if compute_stack == "kubernetes":
            if comp_stack == "slurm":
                status = "coming_soon"
            else:
                status = "available"
        else:
            # slurm stack — all adapters are stubbed so mark k8s as coming_soon
            if comp_stack == "kubernetes":
                status = "coming_soon"
            else:
                status = "coming_soon"

        components.append(
            ComponentDefinitionResponse(
                key=key,
                name=defn["name"],
                category=defn["category"],
                description=defn["description"],
                cost_estimate=defn.get("estimated_monthly_cost", ""),
                dependencies=defn.get("dependencies", []),
                configurable_fields=defn.get("config_schema", []),
                status=status,
            )
        )

    return ComponentsListResponse(compute_stack=compute_stack, components=components)


# Bucket purpose descriptions keyed by bucket type
_BUCKET_PURPOSES = {
    "ingest": "Landing zone for incoming sequencing files. bioAF auto-detects and catalogs new files here.",
    "raw": "Permanent storage for raw sequencing data after ingest.",
    "working": "Intermediate pipeline outputs and working files.",
    "results": "Final pipeline results and analysis outputs.",
    "config-backups": "Automated backups of platform configuration and metadata.",
}


def _org_slug(org_name: str) -> str:
    """Generate a URL-safe slug from an organization name."""
    return org_name.lower().replace(" ", "-").replace("_", "-")


@router.get("/storage/buckets", response_model=StorageBucketsResponse)
async def get_storage_buckets(
    current_user: dict = require_role("admin", "comp_bio"),
    session: AsyncSession = Depends(get_session),
):
    """Returns GCS bucket configuration for the current organization."""
    org_id = current_user.get("org_id")
    org_result = await session.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    slug = _org_slug(org.name) if org else "demo"

    storage_adapter = get_storage_adapter()
    metrics = await storage_adapter.get_storage_metrics()
    metrics_by_name = {b["name"]: b for b in metrics.get("buckets", [])}

    bucket_types = ["ingest", "raw", "working", "results", "config-backups"]
    buckets = []
    for btype in bucket_types:
        bucket_name = f"bioaf-{btype}-{slug}"
        bmetrics = metrics_by_name.get(bucket_name, {})
        buckets.append(
            StorageBucketInfo(
                name=bucket_name,
                purpose=_BUCKET_PURPOSES.get(btype, ""),
                is_ingest=(btype == "ingest"),
                size_gb=bmetrics.get("size_gb", 0.0),
                object_count=bmetrics.get("object_count", 0),
            )
        )

    return StorageBucketsResponse(org_slug=slug, buckets=buckets)
