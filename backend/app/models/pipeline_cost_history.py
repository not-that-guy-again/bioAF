from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineCostHistory(Base):
    __tablename__ = "pipeline_cost_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_file_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_total_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    actual_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    estimation_error_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pipeline_run = relationship("PipelineRun")
