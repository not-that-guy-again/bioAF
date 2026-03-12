"""GCS storage adapter.

Supports local/mock mode for development and real GCS API for production.
Mode is controlled by the BIOAF_COMPUTE_MODE environment variable.
"""

import logging
import os
import shutil
import uuid

from app.adapters.base import StorageProvider

logger = logging.getLogger("bioaf.adapters.storage.gcs")

LOCAL_DATA_ROOT = os.environ.get("BIOAF_LOCAL_DATA_ROOT", "/tmp/bioaf-data")


class GcsStorageProvider(StorageProvider):
    """GCS storage backend with local mode for development."""

    def __init__(self, org_slug: str = "demo"):
        self._mode = os.environ.get("BIOAF_COMPUTE_MODE", "local")
        self._org_slug = org_slug

    @property
    def is_local(self) -> bool:
        return self._mode == "local"

    @property
    def ingest_bucket(self) -> str:
        return f"bioaf-ingest-{self._org_slug}"

    @property
    def raw_bucket(self) -> str:
        return f"bioaf-raw-{self._org_slug}"

    @property
    def working_bucket(self) -> str:
        return f"bioaf-working-{self._org_slug}"

    @property
    def results_bucket(self) -> str:
        return f"bioaf-results-{self._org_slug}"

    @property
    def config_backups_bucket(self) -> str:
        return f"bioaf-config-backups-{self._org_slug}"

    async def resolve_input_path(self, file_record: dict) -> str:
        if self.is_local:
            return f"/data/inputs/{file_record.get('filename', 'unknown')}"
        return f"/data/inputs/{file_record.get('filename', 'unknown')}"

    async def resolve_output_path(self, pipeline_run: dict, filename: str) -> str:
        run_id = pipeline_run.get("id", "unknown")
        experiment_id = pipeline_run.get("experiment_id", "unknown")
        if self.is_local:
            return f"{LOCAL_DATA_ROOT}/results/experiments/{experiment_id}/runs/{run_id}/{filename}"
        return f"gs://{self.results_bucket}/experiments/{experiment_id}/runs/{run_id}/{filename}"

    async def stage_inputs(self, file_records: list[dict], working_dir: str) -> list[str]:
        if self.is_local:
            return await self._local_stage_inputs(file_records, working_dir)
        return await self._gcs_stage_inputs(file_records, working_dir)

    async def collect_outputs(self, working_dir: str, pipeline_run: dict) -> list[dict]:
        if self.is_local:
            return await self._local_collect_outputs(working_dir, pipeline_run)
        return await self._gcs_collect_outputs(working_dir, pipeline_run)

    async def get_storage_metrics(self) -> dict:
        if self.is_local:
            return self._local_storage_metrics()
        return await self._gcs_storage_metrics()

    # -- Local mode implementations --

    async def _local_stage_inputs(self, file_records: list[dict], working_dir: str) -> list[str]:
        os.makedirs(working_dir, exist_ok=True)
        staged_paths = []
        for record in file_records:
            filename = record.get("filename", f"file-{uuid.uuid4().hex[:8]}")
            src = record.get("local_path") or record.get("gcs_uri", "")
            dest = os.path.join(working_dir, filename)
            if src and os.path.exists(src):
                shutil.copy2(src, dest)
            else:
                # Create placeholder for local mode
                with open(dest, "w") as f:
                    f.write(f"# placeholder for {filename}\n")
            staged_paths.append(dest)
        return staged_paths

    async def _local_collect_outputs(self, working_dir: str, pipeline_run: dict) -> list[dict]:
        run_id = pipeline_run.get("id", "unknown")
        experiment_id = pipeline_run.get("experiment_id", "unknown")
        results_dir = f"{LOCAL_DATA_ROOT}/results/experiments/{experiment_id}/runs/{run_id}"
        os.makedirs(results_dir, exist_ok=True)

        collected = []
        if os.path.isdir(working_dir):
            for fname in os.listdir(working_dir):
                src = os.path.join(working_dir, fname)
                if os.path.isfile(src):
                    dest = os.path.join(results_dir, fname)
                    shutil.copy2(src, dest)
                    collected.append(
                        {
                            "filename": fname,
                            "local_path": dest,
                            "gcs_uri": f"gs://{self.results_bucket}/experiments/{experiment_id}/runs/{run_id}/{fname}",
                            "size_bytes": os.path.getsize(dest),
                        }
                    )
        return collected

    def _local_storage_metrics(self) -> dict:
        return {
            "buckets": [
                {
                    "name": self.ingest_bucket,
                    "size_gb": 0.0,
                    "object_count": 0,
                    "storage_class": "STANDARD",
                    "cost_monthly_usd": 0.0,
                },
                {
                    "name": self.raw_bucket,
                    "size_gb": 2.5,
                    "object_count": 45,
                    "storage_class": "STANDARD",
                    "cost_monthly_usd": 0.06,
                },
                {
                    "name": self.working_bucket,
                    "size_gb": 1.2,
                    "object_count": 120,
                    "storage_class": "STANDARD",
                    "cost_monthly_usd": 0.03,
                },
                {
                    "name": self.results_bucket,
                    "size_gb": 0.8,
                    "object_count": 35,
                    "storage_class": "STANDARD",
                    "cost_monthly_usd": 0.02,
                },
                {
                    "name": self.config_backups_bucket,
                    "size_gb": 0.01,
                    "object_count": 5,
                    "storage_class": "NEARLINE",
                    "cost_monthly_usd": 0.0,
                },
            ],
            "total_size_gb": 4.51,
            "total_cost_monthly_usd": 0.11,
        }

    # -- GCS API implementations (production) --

    async def _gcs_stage_inputs(self, file_records: list[dict], working_dir: str) -> list[str]:
        # TODO: Wire to real GCS downloads in Phase 20 when pipeline execution goes live
        raise NotImplementedError("GCS stage_inputs will be wired in Phase 20")

    async def _gcs_collect_outputs(self, working_dir: str, pipeline_run: dict) -> list[dict]:
        # TODO: Wire to real GCS uploads in Phase 20 when pipeline execution goes live
        raise NotImplementedError("GCS collect_outputs will be wired in Phase 20")

    async def _gcs_storage_metrics(self) -> dict:
        """Delegate to GcsStorageService for live bucket metrics.

        Requires a DB session to read platform_config. Since the BAL adapter
        interface does not pass a session, we create a short-lived one here.
        """
        from app.database import async_session_factory
        from app.services.gcs_storage import GcsStorageService

        async with async_session_factory() as session:
            metrics = await GcsStorageService.get_bucket_metrics(session)

        # Convert to the dict format expected by the adapter interface
        buckets = []
        for m in metrics:
            size_gb = m.size_bytes / (1024**3)
            buckets.append({
                "name": m.bucket_name,
                "size_gb": round(size_gb, 2),
                "object_count": m.object_count,
                "storage_class": m.storage_class,
                "cost_monthly_usd": round(size_gb * 0.026, 2),
            })

        total_gb = sum(b["size_gb"] for b in buckets)
        return {
            "buckets": buckets,
            "total_size_gb": round(total_gb, 2),
            "total_cost_monthly_usd": round(sum(b["cost_monthly_usd"] for b in buckets), 2),
        }
