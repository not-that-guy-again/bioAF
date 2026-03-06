import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.services.pipeline_monitor_service import PipelineMonitorService, _parse_memory_gb, _parse_duration


# --- Unit tests for trace file parsing ---

SAMPLE_TRACE_TSV = """task_id\thash\tnative_id\tprocess\ttag\tname\tstatus\texit\tsubmit\tstart\tcomplete\tduration\trealtime\t%cpu\tpeak_rss\tpeak_vmem\trchar\twchar
1\tab/123456\t100\tSTARSOLO\t-\tSTARSOLO (SAMPLE_1)\tCOMPLETED\t0\t2026-01-01 00:00\t2026-01-01 00:01\t2026-01-01 00:30\t30m\t29m 45s\t85.2\t4.5 GB\t8.1 GB\t100\t200
2\tcd/789012\t101\tSAMTOOLS_SORT\t-\tSAMTOOLS_SORT (SAMPLE_1)\tRUNNING\t-\t2026-01-01 00:30\t2026-01-01 00:31\t-\t-\t-\t-\t-\t-\t-\t-
3\tef/345678\t102\tFASTQC\t-\tFASTQC (SAMPLE_1)\tFAILED\t1\t2026-01-01 00:00\t2026-01-01 00:01\t2026-01-01 00:05\t5m\t4m 30s\t20.5\t500 MB\t1.2 GB\t50\t10
"""


def test_parse_trace_tsv():
    """Parse a Nextflow trace.tsv into process records."""
    processes = PipelineMonitorService.parse_trace_tsv(SAMPLE_TRACE_TSV)
    assert len(processes) == 3
    assert processes[0]["process"] == "STARSOLO"
    assert processes[0]["status"] == "COMPLETED"
    assert processes[0]["exit"] == "0"
    assert processes[1]["status"] == "RUNNING"
    assert processes[2]["status"] == "FAILED"


def test_map_nf_status():
    """Map Nextflow status strings to our status."""
    assert PipelineMonitorService._map_nf_status("COMPLETED") == "completed"
    assert PipelineMonitorService._map_nf_status("RUNNING") == "running"
    assert PipelineMonitorService._map_nf_status("FAILED") == "failed"
    assert PipelineMonitorService._map_nf_status("CACHED") == "cached"
    assert PipelineMonitorService._map_nf_status("SUBMITTED") == "pending"


def test_parse_memory_gb():
    """Parse memory values from trace."""
    assert _parse_memory_gb("4.5 GB") == 4.5
    assert _parse_memory_gb("500 MB") == pytest.approx(0.49, rel=0.1)
    assert _parse_memory_gb("-") is None
    assert _parse_memory_gb(None) is None
    assert _parse_memory_gb("") is None


def test_parse_duration():
    """Parse duration values from trace."""
    assert _parse_duration("30s") == 30
    assert _parse_duration("5m 30s") == 330
    assert _parse_duration("1h 2m 3s") == 3723
    assert _parse_duration("-") is None
    assert _parse_duration(None) is None


# --- Integration tests for sync_run_statuses ---

@pytest_asyncio.fixture
async def running_pipeline_run(session, admin_user):
    from app.models.experiment import Experiment
    from app.models.pipeline_run import PipelineRun

    exp = Experiment(
        organization_id=admin_user.organization_id,
        name="Monitor Test Experiment",
        owner_user_id=admin_user.id,
        status="processing",
    )
    session.add(exp)
    await session.flush()

    run = PipelineRun(
        organization_id=admin_user.organization_id,
        experiment_id=exp.id,
        submitted_by_user_id=admin_user.id,
        pipeline_name="nf-core/scrnaseq",
        pipeline_version="2.7.1",
        status="running",
        work_dir="/data/working/nextflow/run-1",
    )
    session.add(run)
    await session.flush()
    await session.commit()
    return run


COMPLETED_TRACE = """task_id\thash\tnative_id\tprocess\ttag\tname\tstatus\texit\tsubmit\tstart\tcomplete\tduration\trealtime\t%cpu\tpeak_rss\tpeak_vmem\trchar\twchar
1\tab/123\t100\tPROCESS_A\t-\tPROCESS_A\tCOMPLETED\t0\t2026-01-01\t2026-01-01\t2026-01-01\t10m\t9m\t50.0\t1 GB\t2 GB\t0\t0
2\tcd/456\t101\tPROCESS_B\tCOMPLETED\tPROCESS_B\tCOMPLETED\t0\t2026-01-01\t2026-01-01\t2026-01-01\t5m\t4m\t30.0\t500 MB\t1 GB\t0\t0
"""


@pytest.mark.asyncio
async def test_sync_detects_completion(session, running_pipeline_run):
    """Monitor detects when all processes are completed."""
    with patch(
        "app.services.slurm_service.SlurmService._run_ssh_command",
        new_callable=AsyncMock,
        side_effect=[
            COMPLETED_TRACE,  # trace file read
            "",  # output file listing
        ],
    ), patch(
        "app.services.experiment_service.ExperimentService.update_status",
        new_callable=AsyncMock,
    ):
        await PipelineMonitorService.sync_run_statuses(session)

    # Refresh the run
    from sqlalchemy import select
    from app.models.pipeline_run import PipelineRun

    result = await session.execute(select(PipelineRun).where(PipelineRun.id == running_pipeline_run.id))
    run = result.scalar_one()
    assert run.status == "completed"
    assert run.progress_json is not None
    assert run.progress_json["total_processes"] == 2
    assert run.progress_json["completed"] == 2
    assert run.progress_json["percent_complete"] == 100.0


FAILED_TRACE = """task_id\thash\tnative_id\tprocess\ttag\tname\tstatus\texit\tsubmit\tstart\tcomplete\tduration\trealtime\t%cpu\tpeak_rss\tpeak_vmem\trchar\twchar
1\tab/123\t100\tPROCESS_A\t-\tPROCESS_A\tCOMPLETED\t0\t2026-01-01\t2026-01-01\t2026-01-01\t10m\t9m\t50.0\t1 GB\t2 GB\t0\t0
2\tcd/456\t101\tPROCESS_B\t-\tPROCESS_B\tFAILED\t1\t2026-01-01\t2026-01-01\t2026-01-01\t5m\t4m\t30.0\t500 MB\t1 GB\t0\t0
"""


@pytest.mark.asyncio
async def test_sync_detects_failure(session, running_pipeline_run):
    """Monitor detects when a process has failed."""
    with patch(
        "app.services.slurm_service.SlurmService._run_ssh_command",
        new_callable=AsyncMock,
        side_effect=[
            FAILED_TRACE,
            "",
        ],
    ), patch(
        "app.services.experiment_service.ExperimentService.update_status",
        new_callable=AsyncMock,
    ):
        await PipelineMonitorService.sync_run_statuses(session)

    from sqlalchemy import select
    from app.models.pipeline_run import PipelineRun

    result = await session.execute(select(PipelineRun).where(PipelineRun.id == running_pipeline_run.id))
    run = result.scalar_one()
    assert run.status == "failed"
    assert "1 process(es) failed" in run.error_message


@pytest.mark.asyncio
async def test_sync_creates_process_records(session, running_pipeline_run):
    """Monitor creates PipelineProcess records from trace."""
    with patch(
        "app.services.slurm_service.SlurmService._run_ssh_command",
        new_callable=AsyncMock,
        side_effect=[
            COMPLETED_TRACE,
            "",
        ],
    ), patch(
        "app.services.experiment_service.ExperimentService.update_status",
        new_callable=AsyncMock,
    ):
        await PipelineMonitorService.sync_run_statuses(session)

    from sqlalchemy import select
    from app.models.pipeline_process import PipelineProcess

    result = await session.execute(
        select(PipelineProcess).where(PipelineProcess.pipeline_run_id == running_pipeline_run.id)
    )
    processes = list(result.scalars().all())
    assert len(processes) == 2
    assert processes[0].process_name in ("PROCESS_A", "PROCESS_B")
