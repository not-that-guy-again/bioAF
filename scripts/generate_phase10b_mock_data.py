"""
Generate Phase 10b mock data for analysis snapshots.

Creates ~20 analysis snapshots across experiments and projects:
- 3 experiments x ~5 snapshots each (QC -> filter -> normalize -> cluster -> DE)
- 2 project-level snapshots (integrated analysis with/without batch correction)
- 3 starred snapshots (one per experiment)
- 1 experiment uses Seurat type with command_log_json
- All others use anndata type

Usage:
  cd backend && python -m scripts.generate_phase10b_mock_data
  # or from project root:
  python scripts/generate_phase10b_mock_data.py
"""

import asyncio
import sys

sys.path.insert(0, "backend")

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.analysis_snapshot import AnalysisSnapshot  # noqa: E402
from app.models.experiment import Experiment  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.user import User  # noqa: E402


ANNDATA_SNAPSHOTS_EXP1 = [
    {
        "label": "Post-QC: 9200 cells, 22000 genes",
        "object_type": "anndata",
        "cell_count": 9200,
        "gene_count": 22000,
        "parameters_json": {},
        "embeddings_json": {},
        "clusterings_json": {},
        "layers_json": ["counts"],
        "metadata_columns_json": ["n_genes", "total_counts", "pct_counts_mt"],
    },
    {
        "label": "Filtered: 8432 cells, 18291 genes",
        "object_type": "anndata",
        "cell_count": 8432,
        "gene_count": 18291,
        "parameters_json": {"filter": {"params": {"min_genes": 200, "max_pct_mt": 20}}},
        "embeddings_json": {},
        "clusterings_json": {},
        "layers_json": ["counts", "log1p"],
        "metadata_columns_json": ["n_genes", "total_counts", "pct_counts_mt", "batch"],
    },
    {
        "label": "leiden_0.8_no_correction",
        "object_type": "anndata",
        "cell_count": 8432,
        "gene_count": 18291,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 15, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.8}},
        },
        "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
        "clusterings_json": {
            "leiden": {
                "n_clusters": 14,
                "distribution": {str(i): max(100, 1400 - i * 95) for i in range(14)},
            }
        },
        "layers_json": ["counts", "log1p"],
        "metadata_columns_json": ["n_genes", "total_counts", "pct_counts_mt", "batch", "leiden"],
    },
    {
        "label": "leiden_0.5_no_correction",
        "object_type": "anndata",
        "cell_count": 8432,
        "gene_count": 18291,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 15, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.5}},
        },
        "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
        "clusterings_json": {
            "leiden": {
                "n_clusters": 9,
                "distribution": {"0": 1200, "1": 980, "2": 850, "3": 720, "4": 650, "5": 580, "6": 510, "7": 480, "8": 462},
            }
        },
        "layers_json": ["counts", "log1p"],
        "metadata_columns_json": ["n_genes", "total_counts", "pct_counts_mt", "batch", "leiden"],
        "starred": True,
        "notes": "Clean separation of major cell types",
    },
    {
        "label": "DE complete: 2847 significant genes",
        "object_type": "anndata",
        "cell_count": 8432,
        "gene_count": 18291,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 15, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.5}},
            "rank_genes_groups": {"params": {"method": "wilcoxon", "groupby": "leiden"}},
        },
        "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
        "clusterings_json": {
            "leiden": {
                "n_clusters": 9,
                "distribution": {"0": 1200, "1": 980, "2": 850, "3": 720, "4": 650, "5": 580, "6": 510, "7": 480, "8": 462},
            }
        },
        "layers_json": ["counts", "log1p"],
        "metadata_columns_json": ["n_genes", "total_counts", "pct_counts_mt", "batch", "leiden"],
    },
]

ANNDATA_SNAPSHOTS_EXP2 = [
    {
        "label": "Post-QC: 6100 cells",
        "object_type": "anndata",
        "cell_count": 6100,
        "gene_count": 19500,
        "parameters_json": {},
        "embeddings_json": {},
        "clusterings_json": {},
        "layers_json": ["counts"],
    },
    {
        "label": "leiden_0.5_harmony",
        "object_type": "anndata",
        "cell_count": 5980,
        "gene_count": 17200,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 20, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.5}},
            "harmony": {"params": {"theta": 2.0, "sigma": 0.1}},
        },
        "embeddings_json": {
            "X_pca": {"n_components": 50},
            "X_harmony": {"n_components": 50},
            "X_umap": {"n_components": 2},
        },
        "clusterings_json": {
            "leiden": {
                "n_clusters": 7,
                "distribution": {"0": 1100, "1": 950, "2": 900, "3": 800, "4": 750, "5": 530, "6": 450},
            }
        },
        "layers_json": ["counts", "log1p"],
        "starred": True,
        "notes": "Harmony batch correction resolves batch effect cleanly",
    },
    {
        "label": "leiden_0.3_scvi",
        "object_type": "anndata",
        "cell_count": 5980,
        "gene_count": 17200,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 20, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.3}},
            "scvi": {"params": {"n_latent": 30, "n_layers": 2}},
        },
        "embeddings_json": {
            "X_pca": {"n_components": 50},
            "X_scVI": {"n_components": 30},
            "X_umap": {"n_components": 2},
        },
        "clusterings_json": {
            "leiden": {
                "n_clusters": 5,
                "distribution": {"0": 1500, "1": 1300, "2": 1200, "3": 1100, "4": 880},
            }
        },
        "layers_json": ["counts", "log1p"],
    },
    {
        "label": "DE complete: 1823 significant genes",
        "object_type": "anndata",
        "cell_count": 5980,
        "gene_count": 17200,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 20, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.5}},
            "harmony": {"params": {"theta": 2.0}},
            "rank_genes_groups": {"params": {"method": "wilcoxon", "groupby": "leiden"}},
        },
        "embeddings_json": {
            "X_pca": {"n_components": 50},
            "X_harmony": {"n_components": 50},
            "X_umap": {"n_components": 2},
        },
        "clusterings_json": {
            "leiden": {
                "n_clusters": 7,
                "distribution": {"0": 1100, "1": 950, "2": 900, "3": 800, "4": 750, "5": 530, "6": 450},
            }
        },
        "layers_json": ["counts", "log1p"],
    },
]

SEURAT_SNAPSHOTS_EXP3 = [
    {
        "label": "Post-QC: 8102 cells",
        "object_type": "seurat",
        "cell_count": 8102,
        "gene_count": 20100,
        "parameters_json": {},
        "embeddings_json": {},
        "clusterings_json": {},
        "command_log_json": [
            {"name": "CreateSeuratObject", "params": {"min.cells": 3, "min.features": 200}},
        ],
    },
    {
        "label": "sct_leiden_0.5",
        "object_type": "seurat",
        "cell_count": 8102,
        "gene_count": 20100,
        "parameters_json": {
            "FindNeighbors": {"params": {"dims": "1:30"}},
            "FindClusters": {"params": {"resolution": 0.5}},
        },
        "embeddings_json": {"pca": {"n_components": 50}, "umap": {"n_components": 2}},
        "clusterings_json": {
            "seurat_clusters": {
                "n_clusters": 8,
                "distribution": {"0": 1400, "1": 1200, "2": 1100, "3": 900, "4": 850, "5": 800, "6": 500, "7": 352},
            }
        },
        "command_log_json": [
            {"name": "CreateSeuratObject", "params": {"min.cells": 3, "min.features": 200}},
            {"name": "NormalizeData", "params": {"assay": "RNA"}},
            {"name": "FindVariableFeatures", "params": {"assay": "RNA", "nfeatures": 2000}},
            {"name": "ScaleData", "params": {"assay": "RNA"}},
            {"name": "RunPCA", "params": {"assay": "RNA", "npcs": 50}},
            {"name": "FindNeighbors", "params": {"reduction": "pca", "dims": "1:30"}},
            {"name": "FindClusters", "params": {"resolution": 0.5}},
            {"name": "RunUMAP", "params": {"reduction": "pca", "dims": "1:30"}},
        ],
        "starred": True,
        "notes": "Standard SCTransform workflow",
    },
    {
        "label": "sct_leiden_0.3",
        "object_type": "seurat",
        "cell_count": 8102,
        "gene_count": 20100,
        "parameters_json": {
            "FindNeighbors": {"params": {"dims": "1:30"}},
            "FindClusters": {"params": {"resolution": 0.3}},
        },
        "embeddings_json": {"pca": {"n_components": 50}, "umap": {"n_components": 2}},
        "clusterings_json": {
            "seurat_clusters": {
                "n_clusters": 6,
                "distribution": {"0": 1800, "1": 1600, "2": 1500, "3": 1300, "4": 1100, "5": 802},
            }
        },
        "command_log_json": [
            {"name": "CreateSeuratObject", "params": {"min.cells": 3, "min.features": 200}},
            {"name": "NormalizeData", "params": {"assay": "RNA"}},
            {"name": "FindVariableFeatures", "params": {"assay": "RNA", "nfeatures": 2000}},
            {"name": "ScaleData", "params": {"assay": "RNA"}},
            {"name": "RunPCA", "params": {"assay": "RNA", "npcs": 50}},
            {"name": "FindNeighbors", "params": {"reduction": "pca", "dims": "1:30"}},
            {"name": "FindClusters", "params": {"resolution": 0.3}},
            {"name": "RunUMAP", "params": {"reduction": "pca", "dims": "1:30"}},
        ],
    },
    {
        "label": "sct_harmony_leiden_0.5",
        "object_type": "seurat",
        "cell_count": 8100,
        "gene_count": 20100,
        "parameters_json": {
            "FindNeighbors": {"params": {"dims": "1:30"}},
            "FindClusters": {"params": {"resolution": 0.5}},
            "RunHarmony": {"params": {"theta": 2.0, "group.by.vars": "batch"}},
        },
        "embeddings_json": {
            "pca": {"n_components": 50},
            "harmony": {"n_components": 50},
            "umap": {"n_components": 2},
        },
        "clusterings_json": {
            "seurat_clusters": {
                "n_clusters": 9,
                "distribution": {"0": 1200, "1": 1100, "2": 1000, "3": 900, "4": 850, "5": 800, "6": 700, "7": 350, "8": 200},
            }
        },
        "command_log_json": [
            {"name": "CreateSeuratObject", "params": {"min.cells": 3, "min.features": 200}},
            {"name": "NormalizeData", "params": {"assay": "RNA"}},
            {"name": "FindVariableFeatures", "params": {"assay": "RNA", "nfeatures": 2000}},
            {"name": "ScaleData", "params": {"assay": "RNA"}},
            {"name": "RunPCA", "params": {"assay": "RNA", "npcs": 50}},
            {"name": "RunHarmony", "params": {"theta": 2.0, "group.by.vars": "batch"}},
            {"name": "FindNeighbors", "params": {"reduction": "harmony", "dims": "1:30"}},
            {"name": "FindClusters", "params": {"resolution": 0.5}},
            {"name": "RunUMAP", "params": {"reduction": "harmony", "dims": "1:30"}},
        ],
    },
]

PROJECT_SNAPSHOTS = [
    {
        "label": "Integrated: no batch correction",
        "object_type": "anndata",
        "cell_count": 14412,
        "gene_count": 16800,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 15, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.5}},
        },
        "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
        "clusterings_json": {
            "leiden": {
                "n_clusters": 12,
                "distribution": {str(i): max(200, 1800 - i * 140) for i in range(12)},
            }
        },
        "layers_json": ["counts", "log1p"],
        "notes": "Batch effect visible in UMAP",
    },
    {
        "label": "Integrated: scVI batch corrected",
        "object_type": "anndata",
        "cell_count": 14410,
        "gene_count": 16800,
        "parameters_json": {
            "neighbors": {"params": {"n_neighbors": 15, "method": "umap"}},
            "leiden": {"params": {"resolution": 0.5}},
            "scvi": {"params": {"n_latent": 30, "n_layers": 2, "batch_key": "experiment"}},
        },
        "embeddings_json": {
            "X_pca": {"n_components": 50},
            "X_scVI": {"n_components": 30},
            "X_umap": {"n_components": 2},
        },
        "clusterings_json": {
            "leiden": {
                "n_clusters": 10,
                "distribution": {str(i): max(300, 2000 - i * 180) for i in range(10)},
            }
        },
        "layers_json": ["counts", "log1p"],
        "notes": "Batch effect resolved, clean integration",
    },
]


async def generate() -> None:
    async with async_session_factory() as session:
        session: AsyncSession

        # Clean existing snapshots
        await session.execute(delete(AnalysisSnapshot))
        await session.flush()

        # Get user
        user_result = await session.execute(select(User).where(User.role == "comp_bio").limit(1))
        user = user_result.scalar_one_or_none()
        if not user:
            user_result = await session.execute(select(User).limit(1))
            user = user_result.scalar_one()

        # Get experiments
        exp_result = await session.execute(select(Experiment).order_by(Experiment.id).limit(3))
        experiments = exp_result.scalars().all()
        if len(experiments) < 3:
            print(f"Warning: only {len(experiments)} experiments found, need 3")
            return

        # Get project
        proj_result = await session.execute(select(Project).limit(1))
        project = proj_result.scalar_one_or_none()

        snapshot_sets = [
            (experiments[0], ANNDATA_SNAPSHOTS_EXP1),
            (experiments[1], ANNDATA_SNAPSHOTS_EXP2),
            (experiments[2], SEURAT_SNAPSHOTS_EXP3),
        ]

        count = 0
        for exp, snap_list in snapshot_sets:
            for snap_data in snap_list:
                starred = snap_data.pop("starred", False)
                notes = snap_data.pop("notes", None)
                snapshot = AnalysisSnapshot(
                    organization_id=user.organization_id,
                    experiment_id=exp.id,
                    user_id=user.id,
                    starred=starred,
                    notes=notes,
                    **snap_data,
                )
                session.add(snapshot)
                count += 1

        if project:
            for snap_data in PROJECT_SNAPSHOTS:
                notes = snap_data.pop("notes", None)
                snapshot = AnalysisSnapshot(
                    organization_id=user.organization_id,
                    project_id=project.id,
                    user_id=user.id,
                    notes=notes,
                    **snap_data,
                )
                session.add(snapshot)
                count += 1

        await session.commit()
        print(f"Created {count} analysis snapshots")


if __name__ == "__main__":
    asyncio.run(generate())
