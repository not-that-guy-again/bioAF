"""scRNA-seq QC template.

Lifts the existing scRNA-seq dashboard logic from QCDashboardService into a
self-contained template. The render config matches the layout the original
hardcoded dashboard page produced.
"""

from __future__ import annotations

from typing import Any


def render_config() -> dict:
    return {
        "template": "scrnaseq",
        "sections": [
            {
                "id": "hero",
                "layout": "hero",
                "metrics": [
                    "cell_count",
                    "mean_reads_per_cell",
                    "median_genes_per_cell",
                    "median_umi_per_cell",
                ],
            },
            {
                "id": "cells",
                "title": "Cells",
                "layout": "grid",
                "metrics": [
                    "cell_count",
                    "total_genes_detected",
                    "median_genes_per_cell",
                    "mean_genes_per_cell",
                    "median_umi_per_cell",
                    "mean_umi_per_cell",
                    "umis_in_cells",
                    "mito_pct_median",
                    "doublet_score_median",
                ],
            },
            {
                "id": "sequencing",
                "title": "Sequencing",
                "layout": "grid",
                "metrics": [
                    "number_of_reads",
                    "median_reads_per_cell",
                    "mean_reads_per_cell",
                    "saturation",
                    "valid_barcodes",
                    "q30_bases_barcode",
                    "q30_bases_rna_read",
                ],
            },
            {
                "id": "mapping",
                "title": "Mapping",
                "layout": "grid",
                "metrics": [
                    "reads_mapped_genome",
                    "reads_mapped_genome_unique",
                ],
            },
            {
                "id": "bulk",
                "title": "Per-Sample QC (FastQC aggregate)",
                "layout": "grid",
                "metrics": [
                    "total_sequences",
                    "total_samples",
                    "percent_duplicates",
                    "percent_gc",
                    "avg_sequence_length",
                ],
            },
        ],
        "metrics": {
            "cell_count": {"label": "Estimated Number of Cells", "format": "integer"},
            "total_genes_detected": {"label": "Total Genes Detected", "format": "integer"},
            "median_genes_per_cell": {"label": "Median Genes per Cell", "format": "integer"},
            "mean_genes_per_cell": {"label": "Mean Genes per Cell", "format": "integer"},
            "median_umi_per_cell": {"label": "Median UMI per Cell", "format": "integer"},
            "mean_umi_per_cell": {"label": "Mean UMI per Cell", "format": "integer"},
            "umis_in_cells": {"label": "UMIs in Cells", "format": "integer"},
            "mito_pct_median": {
                "label": "Median Mitochondrial %",
                "format": "decimal",
                "thresholds": {"good": "<5", "warn": "<10"},
            },
            "doublet_score_median": {"label": "Median Doublet Score", "format": "decimal"},
            "number_of_reads": {"label": "Number of Reads", "format": "integer"},
            "median_reads_per_cell": {"label": "Median Reads per Cell", "format": "integer"},
            "mean_reads_per_cell": {"label": "Mean Reads per Cell", "format": "integer"},
            "saturation": {
                "label": "Sequencing Saturation",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.8", "warn": ">=0.5"},
            },
            "valid_barcodes": {
                "label": "Reads With Valid Barcodes",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.95", "warn": ">=0.85"},
            },
            "q30_bases_barcode": {
                "label": "Q30 Bases in CB+UMI",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.9", "warn": ">=0.8"},
            },
            "q30_bases_rna_read": {
                "label": "Q30 Bases in RNA Read",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.9", "warn": ">=0.8"},
            },
            "reads_mapped_genome": {
                "label": "Reads Mapped to Genome",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.9", "warn": ">=0.5"},
            },
            "reads_mapped_genome_unique": {
                "label": "Reads Mapped to Genome (Unique)",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.7", "warn": ">=0.5"},
            },
            "total_sequences": {"label": "Total Sequences", "format": "integer"},
            "total_samples": {"label": "Samples", "format": "integer"},
            "percent_duplicates": {
                "label": "Duplicates",
                "format": "percent_pct",
                "thresholds": {"good": "<30", "warn": "<50"},
            },
            "percent_gc": {"label": "GC Content", "format": "percent_pct"},
            "avg_sequence_length": {"label": "Avg Read Length", "format": "bp"},
        },
        "charts": [
            {"type": "barcode_rank", "metric_key": "barcode_rank_data", "title": "Barcode Rank"},
            {"type": "star_alignment", "metric_key": "chart_data.star_alignment", "title": "STAR Alignment"},
            {"type": "base_quality", "metric_key": "chart_data.base_quality", "title": "Per-Base Sequence Quality"},
            {"type": "gc_content", "metric_key": "chart_data.gc_content", "title": "GC Content Distribution"},
            {"type": "duplication", "metric_key": "chart_data.duplication", "title": "Sequence Duplication Levels"},
        ],
        "plots": [
            {
                "file_glob": "multiqc/multiqc_plots/png/star_alignment_plot-pct.png",
                "title": "STAR Alignment",
                "type": "star_alignment",
            },
            {
                "file_glob": "multiqc/multiqc_plots/png/fastqc_per_base_sequence_quality_plot.png",
                "title": "Per-Base Sequence Quality",
                "type": "base_quality",
            },
            {
                "file_glob": "multiqc/multiqc_plots/png/fastqc_per_sequence_gc_content_plot_Percentages.png",
                "title": "GC Content Distribution",
                "type": "gc_content",
            },
            {
                "file_glob": "multiqc/multiqc_plots/png/fastqc_sequence_duplication_levels_plot.png",
                "title": "Sequence Duplication Levels",
                "type": "duplication",
            },
            {
                "file_glob": "multiqc/multiqc_plots/png/fastqc_sequence_counts_plot-cnt.png",
                "title": "Sequence Counts",
                "type": "seq_counts",
            },
            {
                "file_glob": "multiqc/multiqc_plots/png/general_stats_table.png",
                "title": "General Statistics",
                "type": "general_stats",
            },
        ],
    }


def compute_quality(metrics: dict[str, Any]) -> str:
    """Mirrors QCDashboardService._compute_quality_rating for scRNA-seq.

    Kept verbatim so existing dashboards rate identically after migration.
    """
    mito = metrics.get("mito_pct_median")
    genes = metrics.get("median_genes_per_cell")
    reads = metrics.get("median_reads_per_cell")
    sat = metrics.get("saturation")
    mapping = metrics.get("reads_mapped_genome")
    q30_rna = metrics.get("q30_bases_rna_read")
    valid_bc = metrics.get("valid_barcodes")

    has_sc_metrics = genes is not None or mito is not None
    if has_sc_metrics:
        if mito is not None and mito > 20:
            return "concerning"
        if mapping is not None and mapping < 0.5:
            return "concerning"

        if mito is not None and genes is not None:
            if mito < 5 and genes > 1000 and (reads is None or reads > 2000):
                if sat is not None and sat > 0.7:
                    return "excellent"
                return "good"
            if mito < 10 and genes > 500:
                return "acceptable"
            return "acceptable"

        if genes is not None and genes > 1000:
            excellent_signals = [
                reads is not None and reads > 10000,
                sat is not None and sat > 0.7,
                mapping is not None and mapping > 0.9,
                q30_rna is not None and q30_rna > 0.9,
                valid_bc is not None and valid_bc > 0.95,
            ]
            good_count = sum(1 for s in excellent_signals if s)
            if good_count >= 4:
                return "excellent"
            if reads is not None and reads > 10000 and sat is not None and sat > 0.5:
                return "good"
            return "acceptable"
        if genes is not None and genes > 500:
            return "acceptable"
        if genes is not None:
            return "concerning"

        if mito is not None and mito > 20:
            return "concerning"
        return "acceptable"

    dup = metrics.get("percent_duplicates")
    gc = metrics.get("percent_gc")
    total = metrics.get("total_sequences")
    if total is not None:
        if dup is not None and dup < 30 and gc is not None and 35 <= gc <= 65:
            return "good"
        if dup is not None and dup < 50:
            return "acceptable"
        return "acceptable" if dup is None else "concerning"

    cell_count = metrics.get("cell_count")
    if cell_count is not None and cell_count > 0:
        return "pending_review"

    return "concerning"


__all__ = ["render_config", "compute_quality"]
