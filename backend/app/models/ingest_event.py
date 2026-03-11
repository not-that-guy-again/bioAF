from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class IngestEvent(Base):
    __tablename__ = "ingest_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("files.id"), nullable=True)
    source_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    naming_profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("naming_profiles.id"), nullable=True)
    parsed_project_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_experiment_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parsed_sample_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id"), nullable=True)
    resolved_experiment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("experiments.id"), nullable=True)
    resolved_sample_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("samples.id"), nullable=True)
    auto_created_entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship("File")
    naming_profile = relationship("NamingProfile")
    resolved_project = relationship("Project")
    resolved_experiment = relationship("Experiment")
    resolved_sample = relationship("Sample")
