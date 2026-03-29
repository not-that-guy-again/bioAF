"""Tests for PipelineOutputService - registers pipeline outputs as File records."""

import pytest
import pytest_asyncio

from sqlalchemy import select, text

from app.models.experiment import Experiment
from app.models.file import File
from app.models.pipeline_run import PipelineRun, PipelineRunSample
from app.models.sample import Sample
from app.services.pipeline_output_service import PipelineOutputService


@pytest_asyncio.fixture
async def experiment(session, admin_user):
    """Create a test experiment."""
    exp = Experiment(
        name="Test Experiment",
        organization_id=admin_user.organization_id,
        owner_user_id=admin_user.id,
        status="processing",
    )
    session.add(exp)
    await session.flush()
    return exp


@pytest_asyncio.fixture
async def samples(session, admin_user, experiment):
    """Create two test samples linked to the experiment."""
    s1 = Sample(
        sample_id_external="Sample-001",
        experiment_id=experiment.id,
    )
    s2 = Sample(
        sample_id_external="Sample-002",
        experiment_id=experiment.id,
    )
    session.add_all([s1, s2])
    await session.flush()
    return [s1, s2]


@pytest_asyncio.fixture
async def pipeline_run(session, admin_user, experiment, samples):
    """Create a pipeline run linked to the experiment and samples."""
    run = PipelineRun(
        organization_id=admin_user.organization_id,
        experiment_id=experiment.id,
        submitted_by_user_id=admin_user.id,
        pipeline_name="nf-core/scrnaseq",
        pipeline_version="2.7.1",
        status="completed",
        k8s_job_name="nf-scrnaseq-abc123",
    )
    session.add(run)
    await session.flush()

    for s in samples:
        session.add(PipelineRunSample(pipeline_run_id=run.id, sample_id=s.id))
    await session.flush()
    await session.commit()
    return run


def _make_collected(run_id: int, experiment_id: int) -> list[dict]:
    """Build a sample collect_outputs() result."""
    base = f"gs://bioaf-results-testorg/experiments/{experiment_id}/pipeline-runs/{run_id}"
    return [
        {
            "filename": "filtered.h5ad",
            "gcs_uri": f"{base}/filtered.h5ad",
            "size_bytes": 50_000_000,
            "md5_hash": "abc123",
            "experiment_id": experiment_id,
            "pipeline_run_id": run_id,
        },
        {
            "filename": "aligned.bam",
            "gcs_uri": f"{base}/aligned.bam",
            "size_bytes": 200_000_000,
            "md5_hash": "def456",
            "experiment_id": experiment_id,
            "pipeline_run_id": run_id,
        },
        {
            "filename": "qc_plot.png",
            "gcs_uri": f"{base}/qc_plot.png",
            "size_bytes": 50_000,
            "md5_hash": "ghi789",
            "experiment_id": experiment_id,
            "pipeline_run_id": run_id,
        },
    ]


@pytest.mark.asyncio
async def test_register_outputs_creates_file_records(session, pipeline_run, experiment):
    """File records are created with correct source_type, run ID, and types."""
    collected = _make_collected(pipeline_run.id, experiment.id)

    files = await PipelineOutputService.register_outputs(session, pipeline_run, collected)
    await session.commit()

    assert len(files) == 3

    h5ad = next(f for f in files if f.filename == "filtered.h5ad")
    assert h5ad.source_type == "pipeline_output"
    assert h5ad.source_pipeline_run_id == pipeline_run.id
    assert h5ad.experiment_id == experiment.id
    assert h5ad.file_type == "h5ad"
    assert h5ad.artifact_type == "anndata"

    bam = next(f for f in files if f.filename == "aligned.bam")
    assert bam.file_type == "bam"
    assert bam.artifact_type == "alignment"

    png = next(f for f in files if f.filename == "qc_plot.png")
    assert png.file_type == "image"
    assert png.artifact_type == "image"


@pytest.mark.asyncio
async def test_register_outputs_links_files_to_samples(session, pipeline_run, experiment, samples):
    """Each output file is linked to all samples from the pipeline run."""
    collected = _make_collected(pipeline_run.id, experiment.id)

    files = await PipelineOutputService.register_outputs(session, pipeline_run, collected)
    await session.commit()

    sample_ids = {s.id for s in samples}

    for f in files:
        rows = await session.execute(
            text("SELECT sample_id FROM sample_files WHERE file_id = :fid"),
            {"fid": f.id},
        )
        linked_ids = {row[0] for row in rows.all()}
        assert linked_ids == sample_ids, f"File {f.filename} not linked to all samples"


@pytest.mark.asyncio
async def test_register_outputs_skips_duplicates(session, pipeline_run, experiment, admin_user):
    """Files with an already-existing gcs_uri are not duplicated."""
    collected = _make_collected(pipeline_run.id, experiment.id)

    # Pre-create one file with the same gcs_uri
    existing = File(
        organization_id=admin_user.organization_id,
        gcs_uri=collected[0]["gcs_uri"],
        filename="filtered.h5ad",
        size_bytes=50_000_000,
        file_type="h5ad",
        source_type="upload",
    )
    session.add(existing)
    await session.flush()
    await session.commit()

    files = await PipelineOutputService.register_outputs(session, pipeline_run, collected)
    await session.commit()

    # Only 2 new files created (the duplicate was skipped)
    assert len(files) == 2

    # Verify only one file with that gcs_uri exists
    result = await session.execute(
        select(File).where(File.gcs_uri == collected[0]["gcs_uri"])
    )
    all_matches = result.scalars().all()
    assert len(all_matches) == 1


@pytest.mark.asyncio
async def test_register_outputs_handles_empty_list(session, pipeline_run):
    """Empty collected list returns empty result without errors."""
    files = await PipelineOutputService.register_outputs(session, pipeline_run, [])
    assert files == []


@pytest.mark.asyncio
async def test_register_outputs_no_samples(session, admin_user, experiment):
    """Works when the pipeline run has no linked samples."""
    run = PipelineRun(
        organization_id=admin_user.organization_id,
        experiment_id=experiment.id,
        submitted_by_user_id=admin_user.id,
        pipeline_name="nf-core/scrnaseq",
        status="completed",
    )
    session.add(run)
    await session.flush()
    await session.commit()

    collected = _make_collected(run.id, experiment.id)
    files = await PipelineOutputService.register_outputs(session, run, collected)
    await session.commit()

    assert len(files) == 3
    # No sample links, but files are still created
    for f in files:
        rows = await session.execute(
            text("SELECT sample_id FROM sample_files WHERE file_id = :fid"),
            {"fid": f.id},
        )
        assert rows.all() == []
