from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileParseResult(Base):
    __tablename__ = "file_parse_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id"), nullable=False)
    naming_profile_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("naming_profiles.id"), nullable=True)
    parsed_segments_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    match_status: Mapped[str] = mapped_column(String(20), nullable=False)
    auto_linked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    file = relationship("File")
    naming_profile = relationship("NamingProfile")
    reviewer = relationship("User")
