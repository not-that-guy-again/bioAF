from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineProcess(Base):
    __tablename__ = "pipeline_processes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False)
    process_name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_usage: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    memory_peak_gb: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slurm_job_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stdout_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stderr_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="processes")
