from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectSample(Base):
    __tablename__ = "project_samples"
    __table_args__ = (
        UniqueConstraint("project_id", "sample_id", name="uq_project_samples_project_sample"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    sample_id: Mapped[int] = mapped_column(Integer, ForeignKey("samples.id", ondelete="CASCADE"), nullable=False)
    added_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    project = relationship("Project", back_populates="project_samples")
    sample = relationship("Sample")
    added_by = relationship("User")
