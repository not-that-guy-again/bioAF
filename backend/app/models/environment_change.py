from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EnvironmentChange(Base):
    __tablename__ = "environment_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(Integer, ForeignKey("environments.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    package_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    new_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    git_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization")
    environment = relationship("Environment")
    user = relationship("User")
