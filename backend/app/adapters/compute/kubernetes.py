"""Kubernetes compute adapter.

Supports local/mock mode for development and real K8s API for production.
Mode is controlled by the BIOAF_COMPUTE_MODE environment variable.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import ComputeProvider
from app.models.pipeline_run import PipelineRun

logger = logging.getLogger("bioaf.adapters.compute.k8s")


class KubernetesComputeProvider(ComputeProvider):
    """Kubernetes compute backend with local mode for development."""

    def __init__(self, session_factory=None):
        self._mode = os.environ.get("BIOAF_COMPUTE_MODE", "local")
        self._session_factory = session_factory

    @property
    def is_local(self) -> bool:
        return self._mode == "local"

    async def submit_job(self, job_spec: dict) -> dict:
        if self.is_local:
            return await self._local_submit_job(job_spec)
        return await self._k8s_submit_job(job_spec)

    async def cancel_job(self, job_id: str) -> dict:
        if self.is_local:
            return await self._local_cancel_job(job_id)
        return await self._k8s_cancel_job(job_id)

    async def get_job_status(self, job_id: str) -> dict:
        if self.is_local:
            return await self._local_get_job_status(job_id)
        return await self._k8s_get_job_status(job_id)

    async def list_jobs(self, filters: dict | None = None) -> list[dict]:
        if self.is_local:
            return await self._local_list_jobs(filters)
        return await self._k8s_list_jobs(filters)

    async def get_job_logs(self, job_id: str) -> str:
        if self.is_local:
            return f"[local mode] No logs available for job {job_id}"
        return await self._k8s_get_job_logs(job_id)

    async def get_cluster_status(self) -> dict:
        if self.is_local:
            return self._local_cluster_status()
        return await self._k8s_get_cluster_status()

    async def get_cluster_metrics(self) -> dict:
        if self.is_local:
            return self._local_cluster_metrics()
        return await self._k8s_get_cluster_metrics()

    async def get_cost_estimate(self, job_spec: dict) -> dict:
        input_count = len(job_spec.get("input_files", []))
        base_cost = 0.50
        estimated = base_cost + (input_count * 0.10)
        return {
            "estimated_cost_usd": round(estimated, 2),
            "confidence_low": round(estimated * 0.7, 2),
            "confidence_high": round(estimated * 1.5, 2),
            "currency": "USD",
            "basis": "input file count heuristic",
        }

    # -- Local mode implementations --

    async def _local_submit_job(self, job_spec: dict) -> dict:
        job_id = f"local-{uuid.uuid4().hex[:12]}"
        logger.info("Local mode: submitted job %s", job_id)
        cost_estimate = await self.get_cost_estimate(job_spec)
        return {
            "job_id": job_id,
            "status": "queued",
            "estimated_cost": cost_estimate,
            "namespace": "bioaf-pipelines",
            "node_pool": "bioaf-pipelines",
        }

    async def _local_cancel_job(self, job_id: str) -> dict:
        logger.info("Local mode: cancelled job %s", job_id)
        return {
            "job_id": job_id,
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _local_get_job_status(self, job_id: str) -> dict:
        return {
            "job_id": job_id,
            "status": "completed",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "exit_code": 0,
        }

    async def _local_list_jobs(self, filters: dict | None = None) -> list[dict]:
        return []

    def _local_cluster_status(self) -> dict:
        return {
            "controller_status": "running",
            "node_pools": [
                {
                    "name": "bioaf-platform",
                    "machine_type": "e2-standard-2",
                    "min_nodes": 1,
                    "max_nodes": 3,
                    "current_nodes": 1,
                    "status": "healthy",
                },
                {
                    "name": "bioaf-pipelines",
                    "machine_type": "n2-highmem-8",
                    "min_nodes": 0,
                    "max_nodes": 20,
                    "current_nodes": 0,
                    "status": "healthy",
                    "spot": True,
                },
                {
                    "name": "bioaf-interactive",
                    "machine_type": "n2-standard-4",
                    "min_nodes": 0,
                    "max_nodes": 5,
                    "current_nodes": 0,
                    "status": "healthy",
                },
            ],
            "total_nodes": 1,
            "active_nodes": 1,
            "queue_depth": 0,
            "health": "healthy",
        }

    def _local_cluster_metrics(self) -> dict:
        return {
            "cpu_utilization_pct": 12.5,
            "memory_utilization_pct": 28.3,
            "cost_burn_rate_hourly": 0.15,
            "node_pools": [
                {
                    "name": "bioaf-platform",
                    "cpu_utilization_pct": 25.0,
                    "memory_utilization_pct": 45.0,
                    "cost_rate_hourly": 0.15,
                },
                {
                    "name": "bioaf-pipelines",
                    "cpu_utilization_pct": 0.0,
                    "memory_utilization_pct": 0.0,
                    "cost_rate_hourly": 0.0,
                },
                {
                    "name": "bioaf-interactive",
                    "cpu_utilization_pct": 0.0,
                    "memory_utilization_pct": 0.0,
                    "cost_rate_hourly": 0.0,
                },
            ],
        }

    # -- K8s API implementations (production) --

    async def _k8s_submit_job(self, job_spec: dict) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_cancel_job(self, job_id: str) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_get_job_status(self, job_id: str) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_list_jobs(self, filters: dict | None = None) -> list[dict]:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_get_job_logs(self, job_id: str) -> str:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_get_cluster_status(self) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_get_cluster_metrics(self) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")
