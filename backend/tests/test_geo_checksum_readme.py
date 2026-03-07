"""Tests for GEO checksum manifest and README generators."""

from app.services.geo.checksum_manifest import generate_checksum_manifest
from app.services.geo.readme_generator import generate_readme
from app.services.geo.validation import ValidationReport, ValidationSummary, FileManifestStatus


def test_checksum_manifest_format():
    files_data = {
        "raw_files": [
            {"filename": "R1.fastq.gz", "md5_checksum": "abc123"},
            {"filename": "R2.fastq.gz", "md5_checksum": "def456"},
        ],
        "processed_files": [
            {"filename": "matrix.h5", "md5_checksum": "ghi789"},
        ],
    }

    manifest, missing = generate_checksum_manifest(files_data)

    assert "abc123  R1.fastq.gz" in manifest
    assert "def456  R2.fastq.gz" in manifest
    assert "ghi789  matrix.h5" in manifest
    assert len(missing) == 0


def test_checksum_manifest_missing_checksums():
    files_data = {
        "raw_files": [
            {"filename": "R1.fastq.gz", "md5_checksum": "abc123"},
            {"filename": "R2.fastq.gz", "md5_checksum": None},
        ],
        "processed_files": [],
    }

    manifest, missing = generate_checksum_manifest(files_data)

    assert "abc123  R1.fastq.gz" in manifest
    assert "R2.fastq.gz" not in manifest  # Not in manifest since no checksum
    assert missing == ["R2.fastq.gz"]


def test_checksum_manifest_empty():
    manifest, missing = generate_checksum_manifest(None)
    assert manifest == ""
    assert missing == []


def test_readme_contains_experiment_name():
    report = ValidationReport(
        experiment_id=1,
        pipeline_run_id=10,
        series_fields=[],
        sample_validations=[],
        protocol_fields=[],
        file_manifest=FileManifestStatus(total_files=0, files_with_checksums=0, files_missing_checksums=0, files=[]),
        summary=ValidationSummary(
            total_fields=20, complete=15, populated_unvalidated=2, missing_required=1, missing_recommended=2
        ),
    )

    readme = generate_readme("My Experiment", report, None, [])
    assert "My Experiment" in readme
    assert "Missing (required):     1" in readme


def test_readme_warns_missing_checksums():
    report = ValidationReport(
        experiment_id=1,
        pipeline_run_id=None,
        series_fields=[],
        sample_validations=[],
        protocol_fields=[],
        file_manifest=FileManifestStatus(total_files=0, files_with_checksums=0, files_missing_checksums=0, files=[]),
        summary=ValidationSummary(
            total_fields=10, complete=10, populated_unvalidated=0, missing_required=0, missing_recommended=0
        ),
    )

    readme = generate_readme("Test", report, None, ["R1.fastq.gz"])
    assert "R1.fastq.gz" in readme
    assert "WARNING" in readme


def test_readme_includes_gcs_paths():
    report = ValidationReport(
        experiment_id=1,
        pipeline_run_id=10,
        series_fields=[],
        sample_validations=[],
        protocol_fields=[],
        file_manifest=FileManifestStatus(total_files=0, files_with_checksums=0, files_missing_checksums=0, files=[]),
        summary=ValidationSummary(
            total_fields=10, complete=10, populated_unvalidated=0, missing_required=0, missing_recommended=0
        ),
    )

    files_data = {
        "raw_files": [{"filename": "R1.fastq.gz", "gcs_uri": "gs://bucket/R1.fastq.gz"}],
        "processed_files": [],
    }

    readme = generate_readme("Test", report, files_data, [])
    assert "gs://bucket/R1.fastq.gz" in readme
    assert "FTP" in readme
