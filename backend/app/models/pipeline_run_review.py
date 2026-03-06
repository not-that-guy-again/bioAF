from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


REVIEW_VERDICTS = ["approved", "approved_with_caveats", "rejected", "revision_requested"]


class PipelineRunReview(Base):
    __tablename__ = "pipeline_run_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    reviewer_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_verdicts_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recommended_exclusions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("pipeline_run_reviews.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pipeline_run = relationship("PipelineRun", backref="reviews")
    reviewer = relationship("User")
    superseded_by = relationship("PipelineRunReview", remote_side=[id])
