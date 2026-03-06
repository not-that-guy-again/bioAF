# ADR-011: Single-Cell RNA-seq as Initial Workflow Scope

**Status:** Accepted
**Date:** 2026-03-05
**Deciders:** Brent (product owner)

## Context

Computational biology encompasses a wide range of workflows: single-cell RNA-seq, bulk RNA-seq, whole-genome sequencing, exome sequencing, metagenomics, proteomics, spatial transcriptomics, and more. Each has different tool chains, data sizes, compute profiles, and visualization needs.

Trying to support all workflows at launch would result in a shallow, poorly-tested platform. Focusing on one workflow allows deep integration and a polished experience.

## Decision

bioAF v1 targets single-cell RNA-seq (scRNA-seq) workflows, specifically the 10x Chromium / NovaSeq pipeline. All pre-built environments, pipeline configurations, visualization tools, QC dashboards, and template notebooks are optimized for this workflow.

### What This Means Concretely

**Pre-built environments include:**

- Python: scanpy, anndata, scvi-tools, leidenalg, scvelo, cellrank, scrublet, celltypist, matplotlib, seaborn, plotly
- R: Seurat, SingleCellExperiment, scater, scran, DESeq2, ggplot2, tidyverse, ComplexHeatmap, monocle3
- CLI: CellRanger (user-provided) / STARsolo (default), Nextflow, Snakemake, Singularity

**Pre-installed pipelines:**

- nf-core/scrnaseq (primary)
- nf-core/rnaseq (adjacent use case)
- nf-core/fetchngs (data retrieval)

**Visualization:**

- cellxgene for interactive cell atlas exploration
- Plotly Dash QC dashboard tuned for scRNA-seq metrics (reads/cell, genes/cell, mitochondrial %, knee plot)

**Template notebooks:**

- QC and filtering
- Normalization and dimensionality reduction
- Clustering and marker gene identification
- Differential expression
- Trajectory inference

### What This Does NOT Mean

- bioAF is not locked to scRNA-seq. The underlying infrastructure (SLURM, Nextflow, Jupyter, RStudio, conda) is general-purpose. Teams can install additional tools and run any workflow.
- Custom pipelines can be added via Git URL.
- Custom conda environments can be created for non-scRNA-seq work.
- The experiment tracking system is workflow-agnostic.

## Rationale

- **scRNA-seq is the most common and fastest-growing application** in computational biology. It's the workflow most likely to be run by our target users.
- **Data sizes are manageable.** A typical scRNA-seq experiment generates 50–200GB of raw data and a few GB of processed data. This fits comfortably in GCS without special architecture for petabyte-scale data.
- **The toolchain is well-defined.** The scRNA-seq ecosystem has converged on scanpy/Seurat for analysis, cellxgene for visualization, and nf-core/scrnaseq for pipeline orchestration. There are clear "right answers" for the pre-built environments.
- **The nf-core/scrnaseq pipeline provides strong out-of-the-box value.** It supports CellRanger, STARsolo, Alevin, and Kallisto-Bustools with a single pipeline definition.
- **cellxgene is a differentiated visualization feature.** Providing hosted cellxgene out of the box is something that competing platforms either don't do or do poorly.

## Consequences

- Marketing and documentation should position bioAF as "for single-cell RNA-seq" in v1, with the caveat that the platform supports general-purpose computational biology.
- Pre-built environments will be large (several GB for the conda environment + R packages). This affects the Packer image build time during SLURM provisioning.
- The QC dashboard is scRNA-seq-specific. Generalizing it for other workflow types is a v2 concern.
- v2 expansion candidates include: bulk RNA-seq (already partially supported via nf-core/rnaseq), whole-genome/exome sequencing, spatial transcriptomics (Visium, MERFISH), and multi-omics (CITE-seq, scATAC-seq). Each would need workflow-specific QC dashboards and template notebooks.
