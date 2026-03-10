"""NFS storage adapter stub.

NFS support is planned for a future release. All methods raise NotImplementedError.
"""

from app.adapters.base import StorageProvider


class NfsStorageProvider(StorageProvider):
    """NFS storage backend - not yet implemented."""

    async def resolve_input_path(self, file_record: dict) -> str:
        raise NotImplementedError("NFS storage backend coming soon. Select Kubernetes during setup.")

    async def resolve_output_path(self, pipeline_run: dict, filename: str) -> str:
        raise NotImplementedError("NFS storage backend coming soon. Select Kubernetes during setup.")

    async def stage_inputs(self, file_records: list[dict], working_dir: str) -> list[str]:
        raise NotImplementedError("NFS storage backend coming soon. Select Kubernetes during setup.")

    async def collect_outputs(self, working_dir: str, pipeline_run: dict) -> list[dict]:
        raise NotImplementedError("NFS storage backend coming soon. Select Kubernetes during setup.")

    async def get_storage_metrics(self) -> dict:
        raise NotImplementedError("NFS storage backend coming soon. Select Kubernetes during setup.")
