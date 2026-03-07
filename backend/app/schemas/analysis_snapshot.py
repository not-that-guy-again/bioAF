from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, field_validator


class SnapshotCreate(BaseModel):
    experiment_id: int | None = None
    project_id: int | None = None
    notebook_session_id: int | None = None
    label: str
    notes: str | None = None
    object_type: Literal["anndata", "seurat"]
    cell_count: int | None = None
    gene_count: int | None = None
    parameters_json: dict | None = None
    embeddings_json: dict | None = None
    clusterings_json: dict | None = None
    layers_json: list[str] | None = None
    metadata_columns_json: list[str] | None = None
    command_log_json: list[dict] | None = None
    figure_file_id: int | None = None
    checkpoint_file_id: int | None = None

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("label must not be empty")
        return v.strip()


class SnapshotResponse(BaseModel):
    id: int
    experiment_id: int | None
    project_id: int | None
    notebook_session_id: int | None
    user_id: int
    user_name: str
    label: str
    notes: str | None
    object_type: str
    cell_count: int | None
    gene_count: int | None
    cluster_count: int | None
    starred: bool
    figure_url: str | None
    created_at: str

    model_config = {"from_attributes": True}


class SnapshotDetailResponse(SnapshotResponse):
    parameters_json: dict | None
    embeddings_json: dict | None
    clusterings_json: dict | None
    layers_json: list[str] | None
    metadata_columns_json: list[str] | None
    command_log_json: list[dict] | None
    checkpoint_url: str | None


class ParameterDiff(BaseModel):
    parameter_path: str
    values: dict[int, Any]
    changed: bool


class EmbeddingDiff(BaseModel):
    embedding_name: str
    dimensions: dict[int, int | None]
    present_in: list[int]


class ClusteringDiff(BaseModel):
    clustering_name: str
    n_clusters: dict[int, int]
    distributions: dict[int, dict[str, int]]
    present_in: list[int]


class CommandDiff(BaseModel):
    command_name: str
    present_in: list[int]
    params_differ: bool
    params: dict[int, dict] | None


class CellCountPoint(BaseModel):
    snapshot_id: int
    label: str
    cell_count: int
    created_at: str


class SnapshotComparison(BaseModel):
    snapshots: list[SnapshotDetailResponse]
    parameter_diff: list[ParameterDiff]
    embedding_diff: list[EmbeddingDiff]
    clustering_diff: list[ClusteringDiff]
    command_log_diff: list[CommandDiff] | None
    cell_count_series: list[CellCountPoint]


class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotResponse]
    total: int
