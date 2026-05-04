"""Unit tests for the QC template registry.

Templates live in app.services.qc.templates. Each template owns its own
extractor, quality-rating logic, and render config. The dashboard service
dispatches by `qc_template` string -> Template instance.
"""

import pytest


def test_templates_registry_has_scrnaseq_proteomics_custom():
    from app.services.qc.templates import TEMPLATES

    assert "scrnaseq" in TEMPLATES
    assert "proteomics_maxquant" in TEMPLATES
    assert "custom" in TEMPLATES


def test_scrnaseq_render_config_shape():
    from app.services.qc.templates import TEMPLATES

    cfg = TEMPLATES["scrnaseq"].render_config()
    assert cfg["template"] == "scrnaseq"
    # Core sections include hero + cells + sequencing + mapping
    section_ids = {s["id"] for s in cfg["sections"]}
    assert "hero" in section_ids
    assert "cells" in section_ids
    # Hero section must surface cell_count + key per-cell metrics
    hero = next(s for s in cfg["sections"] if s["id"] == "hero")
    assert "cell_count" in hero["metrics"]
    # Metric definitions include label and format
    assert cfg["metrics"]["cell_count"]["label"] == "Estimated Number of Cells"
    assert cfg["metrics"]["cell_count"]["format"] == "integer"
    assert cfg["metrics"]["saturation"]["format"] == "percent_decimal"
    # Charts list includes barcode rank
    chart_types = [c["type"] for c in cfg["charts"]]
    assert "barcode_rank" in chart_types


def test_scrnaseq_compute_quality_matches_existing_rules():
    from app.services.qc.templates import TEMPLATES

    metrics = {
        "cell_count": 10000,
        "median_genes_per_cell": 3000,
        "median_reads_per_cell": 25000,
        "mito_pct_median": 2.0,
        "saturation": 0.85,
    }
    assert TEMPLATES["scrnaseq"].compute_quality(metrics) == "excellent"

    high_mito = {**metrics, "mito_pct_median": 25.0}
    assert TEMPLATES["scrnaseq"].compute_quality(high_mito) == "concerning"


def test_proteomics_render_config_has_proteomics_metrics():
    from app.services.qc.templates import TEMPLATES

    cfg = TEMPLATES["proteomics_maxquant"].render_config()
    assert cfg["template"] == "proteomics_maxquant"
    metric_keys = set(cfg["metrics"].keys())
    # Must surface MaxQuant-typical totals
    assert "psm_count" in metric_keys
    assert "id_rate" in metric_keys
    assert "mass_accuracy_ppm" in metric_keys
    assert "missed_cleavages_pct" in metric_keys
    # id_rate is a percent-from-decimal value
    assert cfg["metrics"]["id_rate"]["format"] == "percent_decimal"


def test_custom_render_config_uses_pipeline_override():
    """Custom template defers its render config to the pipeline-version
    override. Without an override it returns a minimal placeholder."""
    from app.services.qc.templates import TEMPLATES

    override = {
        "template": "custom",
        "sections": [{"id": "main", "layout": "grid", "metrics": ["foo"]}],
        "metrics": {"foo": {"label": "Foo Score", "format": "decimal"}},
        "charts": [],
        "plots": [],
    }
    cfg = TEMPLATES["custom"].render_config(override=override)
    assert cfg["sections"][0]["metrics"] == ["foo"]
    assert cfg["metrics"]["foo"]["label"] == "Foo Score"

    # No override -> empty / placeholder shape, but still valid
    bare = TEMPLATES["custom"].render_config()
    assert bare["template"] == "custom"
    assert isinstance(bare["sections"], list)
    assert isinstance(bare["metrics"], dict)


def test_custom_quality_defaults_to_pending_review_unless_emitted():
    from app.services.qc.templates import TEMPLATES

    assert TEMPLATES["custom"].compute_quality({}) == "pending_review"
    # If pipeline emits an explicit rating, honor it
    assert TEMPLATES["custom"].compute_quality({"quality_rating": "good"}) == "good"


def test_proteomics_compute_quality_basic_thresholds():
    """Proteomics QC: id_rate >= 0.7 + mass_accuracy_ppm <= 5 -> good."""
    from app.services.qc.templates import TEMPLATES

    good = {"id_rate": 0.75, "mass_accuracy_ppm": 3.0, "psm_count": 50000}
    assert TEMPLATES["proteomics_maxquant"].compute_quality(good) == "good"

    poor = {"id_rate": 0.2, "mass_accuracy_ppm": 30.0, "psm_count": 100}
    assert TEMPLATES["proteomics_maxquant"].compute_quality(poor) == "concerning"

    empty: dict = {}
    assert TEMPLATES["proteomics_maxquant"].compute_quality(empty) == "pending_review"


def test_proteomics_extract_summary_txt_parses_key_metrics():
    """MaxQuant summary.txt is a TSV with one row per raw file plus a Total row.
    Parser extracts MS/MS Identified rate, peptide count, mass accuracy."""
    from app.services.qc.templates.proteomics_maxquant import parse_summary_txt

    # MaxQuant summary.txt (simplified): header row + sample rows + Total row
    content = (
        "Raw file\tMS\tMS/MS\tMS/MS Submitted\tMS/MS Identified\tMS/MS Identified [%]\t"
        "Peptide Sequences Identified\tAv. Absolute Mass Deviation [ppm]\n"
        "sample_A\t10000\t8000\t8000\t6400\t80.0\t12000\t1.8\n"
        "sample_B\t9000\t7000\t7000\t5250\t75.0\t11000\t2.2\n"
        "Total\t19000\t15000\t15000\t11650\t77.7\t23000\t2.0\n"
    )
    metrics = parse_summary_txt(content)
    assert metrics["psm_count"] == 11650
    assert metrics["id_rate"] == pytest.approx(0.777, abs=0.01)
    assert metrics["mass_accuracy_ppm"] == pytest.approx(2.0, abs=0.01)
