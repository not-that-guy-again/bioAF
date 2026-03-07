"""
Example scRNA-seq workflow with bioAF snapshot integration.

This template demonstrates how to capture analysis snapshots at key
checkpoints during a single-cell RNA-seq analysis. Each snapshot records
the current state of the AnnData object (cell/gene counts, parameters,
embeddings, clusterings) without manual parameter logging.

Usage:
    In a bioAF-launched Jupyter session, the connection is auto-configured.
    For external sessions:
        bioaf.connect(api_url="https://...", token="...")
"""

import scanpy as sc

import bioaf

# Connect to bioAF (auto-reads BIOAF_API_URL, BIOAF_TOKEN, BIOAF_EXPERIMENT_ID)
bioaf.connect()

# ── Load data ────────────────────────────────────────────────
adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")
adata.var_names_make_unique()

# ── QC and filtering ────────────────────────────────────────
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True)
adata = adata[adata.obs.pct_counts_mt < 20, :].copy()

# Snapshot after QC
bioaf.snapshot(adata, label=f"Post-QC: {adata.n_obs} cells, {adata.n_vars} genes")

# ── Normalization ────────────────────────────────────────────
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)
adata.raw = adata
adata = adata[:, adata.var.highly_variable].copy()

# ── Dimensionality reduction ────────────────────────────────
sc.pp.scale(adata, max_value=10)
sc.tl.pca(adata, svd_solver="arpack")
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=40)
sc.tl.umap(adata)

# ── Clustering ───────────────────────────────────────────────
# Try multiple resolutions
for res in [0.3, 0.5, 0.8]:
    key = f"leiden_{res}"
    sc.tl.leiden(adata, resolution=res, key_added=key)

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    sc.pl.umap(adata, color=key, ax=ax, show=False, title=f"Leiden res={res}")

    n_clusters = adata.obs[key].nunique()
    bioaf.snapshot(
        adata,
        label=f"Clustered: resolution={res}, {n_clusters} clusters",
        figure=fig,
        notes=f"Leiden clustering with resolution {res}",
    )
    plt.close(fig)

# ── Select best resolution and run DE ───────────────────────
# (Suppose 0.5 was chosen after comparing snapshots in the UI)
adata.obs["leiden"] = adata.obs["leiden_0.5"]
sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")

n_sig = sum(
    1
    for group in adata.uns["rank_genes_groups"]["pvals_adj"]
    for p in adata.uns["rank_genes_groups"]["pvals_adj"][group]
    if p < 0.05
)

# Final snapshot with checkpoint
bioaf.snapshot(
    adata,
    label=f"DE complete: {n_sig} significant genes",
    save_checkpoint=True,
    notes="Final analysis state with differential expression results",
)
