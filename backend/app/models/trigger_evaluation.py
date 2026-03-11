from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TriggerEvaluation(Base):
    __tablename__ = "trigger_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trigger_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_triggers.id"), nullable=False)
    evaluation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    matched_files: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    budget_check_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    pipeline_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("pipeline_runs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trigger = relationship("PipelineTrigger", back_populates="evaluations")
    pipeline_run = relationship("PipelineRun")
