import csv
import io
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pipeline_process import PipelineProcess
from app.models.pipeline_run import PipelineRun
from app.services.audit_service import log_action
from app.services.slurm_service import SlurmService

logger = logging.getLogger("bioaf.pipeline_monitor")


class PipelineMonitorService:
    @staticmethod
    async def sync_run_statuses(session: AsyncSession) -> None:
        """Background task: sync pipeline run statuses by reading Nextflow trace files."""
        try:
            result = await session.execute(
                select(PipelineRun)
                .options(selectinload(PipelineRun.processes))
                .where(PipelineRun.status.in_(["running", "pending"]))
            )
            active_runs = list(result.scalars().all())

            for run in active_runs:
                try:
                    await PipelineMonitorService._sync_single_run(session, run)
                except Exception as e:
                    logger.warning("Failed to sync run %d: %s", run.id, e)

            await session.flush()
            await session.commit()
            if active_runs:
                logger.info("Pipeline monitor synced %d active runs", len(active_runs))

        except Exception as e:
            logger.error("Pipeline monitor sync failed: %s", e)

    @staticmethod
    async def _sync_single_run(session: AsyncSession, run: PipelineRun) -> None:
        """Sync a single run's status from its Nextflow trace file."""
        trace_path = f"{run.work_dir}/pipeline_info/trace.tsv"

        try:
            trace_content = await SlurmService._run_ssh_command(f"cat {trace_path} 2>/dev/null || echo ''")
        except Exception:
            return

        if not trace_content.strip():
            return

        # Parse TSV
        processes = PipelineMonitorService.parse_trace_tsv(trace_content)

        # Upsert pipeline_processes
        existing_by_task_id = {p.task_id: p for p in run.processes if p.task_id}

        for proc_data in processes:
            task_id = proc_data.get("task_id", "")
            if task_id in existing_by_task_id:
                proc = existing_by_task_id[task_id]
            else:
                proc = PipelineProcess(
                    pipeline_run_id=run.id, process_name=proc_data.get("process", ""), task_id=task_id
                )
                session.add(proc)

            proc.status = PipelineMonitorService._map_nf_status(proc_data.get("status", ""))
            proc.exit_code = _safe_int(proc_data.get("exit"))
            proc.cpu_usage = _safe_float(proc_data.get("%cpu"))
            proc.memory_peak_gb = _parse_memory_gb(proc_data.get("peak_rss"))
            proc.duration_seconds = _parse_duration(proc_data.get("realtime"))
            proc.slurm_job_id = proc_data.get("native_id")

        # Compute aggregate progress
        total = len(processes)
        completed = sum(1 for p in processes if p.get("status") == "COMPLETED")
        running = sum(1 for p in processes if p.get("status") == "RUNNING")
        failed = sum(1 for p in processes if p.get("status") == "FAILED")
        cached = sum(1 for p in processes if p.get("status") == "CACHED")

        run.progress_json = {
            "total_processes": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "cached": cached,
            "percent_complete": round((completed + cached) / total * 100, 1) if total > 0 else 0,
        }

        # Detect completion
        if total > 0 and running == 0 and (completed + cached + failed) == total:
            if failed > 0:
                run.status = "failed"
                run.error_message = f"{failed} process(es) failed"
            else:
                run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)

            await PipelineMonitorService._handle_completion(session, run)

    @staticmethod
    async def _handle_completion(session: AsyncSession, run: PipelineRun) -> None:
        """Handle pipeline completion: update experiment status, index outputs."""
        # Check if any other active runs for this experiment
        if run.experiment_id:
            other_active = await session.execute(
                select(PipelineRun.id).where(
                    PipelineRun.experiment_id == run.experiment_id,
                    PipelineRun.id != run.id,
                    PipelineRun.status.in_(["running", "pending"]),
                )
            )
            if not other_active.first():
                # No other active runs — advance experiment to "pipeline_complete"
                # (review step now precedes "analysis" per ADR-019)
                try:
                    from app.services.experiment_service import ExperimentService

                    await ExperimentService.update_status(
                        session,
                        run.experiment_id,
                        run.organization_id,
                        run.submitted_by_user_id,
                        "pipeline_complete",
                    )
                except Exception as e:
                    logger.warning("Could not advance experiment status: %s", e)

        # Index output files
        try:
            outdir = f"/data/results/experiments/{run.experiment_id}/runs/{run.id}"
            output = await SlurmService._run_ssh_command(f"find {outdir} -type f 2>/dev/null || echo ''")
            if output.strip():
                run.output_files_json = {"files": output.strip().split("\n")}
        except Exception as e:
            logger.warning("Failed to index output files for run %d: %s", run.id, e)

        # Audit log
        await log_action(
            session,
            user_id=run.submitted_by_user_id,
            entity_type="pipeline_run",
            entity_id=run.id,
            action="complete",
            details={"status": run.status, "progress": run.progress_json},
        )

        # Auto-generate QC dashboard if component is enabled and run succeeded
        if run.status == "completed":
            try:
                from app.services.component_service import ComponentService

                if await ComponentService.is_enabled(session, "qc_dashboard"):
                    from app.services.qc_dashboard_service import QCDashboardService

                    await QCDashboardService.generate_qc_dashboard(session, run.organization_id, run.id)
                    logger.info("QC dashboard generated for run %d", run.id)
            except Exception as e:
                logger.warning("Failed to generate QC dashboard for run %d: %s", run.id, e)

    @staticmethod
    def parse_trace_tsv(content: str) -> list[dict]:
        """Parse a Nextflow trace.tsv file into a list of dicts."""
        reader = csv.DictReader(io.StringIO(content), delimiter="\t")
        return [dict(row) for row in reader]

    @staticmethod
    def _map_nf_status(nf_status: str) -> str:
        mapping = {
            "COMPLETED": "completed",
            "RUNNING": "running",
            "FAILED": "failed",
            "CACHED": "cached",
            "SUBMITTED": "pending",
            "PENDING": "pending",
            "ABORTED": "failed",
        }
        return mapping.get(nf_status.upper(), nf_status.lower())

    @staticmethod
    async def get_run_logs(session: AsyncSession, run_id: int, process_name: str) -> dict:
        """Get stdout/stderr for a specific process."""
        result = await session.execute(
            select(PipelineProcess).where(
                PipelineProcess.pipeline_run_id == run_id,
                PipelineProcess.process_name == process_name,
            )
        )
        process = result.scalar_one_or_none()
        if not process:
            return {"stdout": "", "stderr": ""}

        stdout = ""
        stderr = ""
        try:
            if process.stdout_path:
                stdout = await SlurmService._run_ssh_command(f"cat {process.stdout_path} 2>/dev/null || echo ''")
            if process.stderr_path:
                stderr = await SlurmService._run_ssh_command(f"cat {process.stderr_path} 2>/dev/null || echo ''")
        except Exception as e:
            logger.warning("Failed to read logs for process %s: %s", process_name, e)

        return {"stdout": stdout, "stderr": stderr}

    @staticmethod
    async def get_run_report(session: AsyncSession, run_id: int) -> str:
        """Read the Nextflow HTML report."""
        result = await session.execute(select(PipelineRun.work_dir).where(PipelineRun.id == run_id))
        work_dir = result.scalar_one_or_none()
        if not work_dir:
            return ""

        try:
            report = await SlurmService._run_ssh_command(
                f"cat {work_dir}/pipeline_info/report.html 2>/dev/null || echo ''"
            )
            return report
        except Exception:
            return ""


def _safe_int(val) -> int | None:
    if val is None or val == "" or val == "-":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    if val is None or val == "" or val == "-":
        return None
    try:
        return float(str(val).replace("%", ""))
    except (ValueError, TypeError):
        return None


def _parse_memory_gb(val) -> float | None:
    """Parse memory values like '1.2 GB' or '500 MB'."""
    if not val or val == "-":
        return None
    try:
        val = str(val).strip()
        if "GB" in val.upper():
            return float(val.upper().replace("GB", "").strip())
        if "MB" in val.upper():
            return round(float(val.upper().replace("MB", "").strip()) / 1024, 2)
        if "KB" in val.upper():
            return round(float(val.upper().replace("KB", "").strip()) / (1024 * 1024), 4)
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_duration(val) -> int | None:
    """Parse duration strings like '5m 30s' or '1h 2m 3s' into seconds."""
    if not val or val == "-":
        return None
    try:
        val = str(val).strip()
        # Try direct milliseconds first (Nextflow trace uses ms)
        if val.endswith("ms"):
            return int(float(val[:-2]) / 1000)
        if val.endswith("s") and "m" not in val and "h" not in val:
            return int(float(val[:-1]))
        # Parse h/m/s format
        seconds = 0
        if "h" in val:
            parts = val.split("h")
            seconds += int(parts[0].strip()) * 3600
            val = parts[1].strip()
        if "m" in val:
            parts = val.split("m")
            seconds += int(parts[0].strip()) * 60
            val = parts[1].strip()
        if val.endswith("s"):
            seconds += int(float(val[:-1]))
        return seconds if seconds > 0 else None
    except (ValueError, TypeError):
        return None
