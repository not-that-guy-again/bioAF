"""MaxQuant proteomics QC template.

Reads MaxQuant `summary.txt` (TSV, one row per raw file plus a Total row) for
high-level identification metrics. Future work can layer in proteinGroups.txt
totals for per-protein QC.
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any


def render_config() -> dict:
    return {
        "template": "proteomics_maxquant",
        "sections": [
            {
                "id": "hero",
                "layout": "hero",
                "metrics": ["psm_count", "id_rate", "mass_accuracy_ppm"],
            },
            {
                "id": "identification",
                "title": "Identification",
                "layout": "grid",
                "metrics": [
                    "psm_count",
                    "peptide_count",
                    "id_rate",
                ],
            },
            {
                "id": "quality",
                "title": "Spectral Quality",
                "layout": "grid",
                "metrics": [
                    "mass_accuracy_ppm",
                    "missed_cleavages_pct",
                ],
            },
        ],
        "metrics": {
            "psm_count": {"label": "Identified PSMs", "format": "integer"},
            "peptide_count": {"label": "Peptide Sequences Identified", "format": "integer"},
            "id_rate": {
                "label": "MS/MS Identification Rate",
                "format": "percent_decimal",
                "thresholds": {"good": ">=0.7", "warn": ">=0.4"},
            },
            "mass_accuracy_ppm": {
                "label": "Avg Absolute Mass Deviation",
                "format": "decimal",
                "thresholds": {"good": "<5", "warn": "<10"},
            },
            "missed_cleavages_pct": {
                "label": "Missed Cleavages",
                "format": "percent_pct",
                "thresholds": {"good": "<15", "warn": "<30"},
            },
        },
        "charts": [],
        "plots": [],
    }


def compute_quality(metrics: dict[str, Any]) -> str:
    id_rate = metrics.get("id_rate")
    ppm = metrics.get("mass_accuracy_ppm")
    psm = metrics.get("psm_count")

    if id_rate is None and ppm is None and psm is None:
        return "pending_review"

    if id_rate is not None and id_rate < 0.3:
        return "concerning"
    if ppm is not None and ppm > 20:
        return "concerning"

    if id_rate is not None and id_rate >= 0.7 and ppm is not None and ppm <= 5:
        return "good"
    if id_rate is not None and id_rate >= 0.4:
        return "acceptable"
    return "acceptable"


def parse_summary_txt(content: str) -> dict[str, Any]:
    """Parse a MaxQuant summary.txt TSV. Returns metrics from the Total row.

    summary.txt has one row per Raw file followed by a `Total` row. We pull
    the Total row's identification rate, peptide count, and mass deviation.
    """
    reader = csv.DictReader(StringIO(content), delimiter="\t")
    rows = list(reader)
    if not rows:
        return {}

    total_row = next((r for r in rows if str(r.get("Raw file", "")).strip().lower() == "total"), None)
    row = total_row or rows[-1]

    metrics: dict[str, Any] = {}

    def _get_first(*keys: str) -> str | None:
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        return None

    psm_raw = _get_first("MS/MS Identified")
    if psm_raw is not None:
        try:
            metrics["psm_count"] = int(float(psm_raw))
        except ValueError:
            pass

    pep_raw = _get_first("Peptide Sequences Identified")
    if pep_raw is not None:
        try:
            metrics["peptide_count"] = int(float(pep_raw))
        except ValueError:
            pass

    id_pct_raw = _get_first("MS/MS Identified [%]", "MS/MS Identified Rate [%]")
    if id_pct_raw is not None:
        try:
            metrics["id_rate"] = float(id_pct_raw) / 100.0
        except ValueError:
            pass

    ppm_raw = _get_first("Av. Absolute Mass Deviation [ppm]", "Average Mass Accuracy [ppm]")
    if ppm_raw is not None:
        try:
            metrics["mass_accuracy_ppm"] = float(ppm_raw)
        except ValueError:
            pass

    return metrics


__all__ = ["render_config", "compute_quality", "parse_summary_txt"]
