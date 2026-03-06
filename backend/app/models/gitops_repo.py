from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GitOpsRepo(Base):
    __tablename__ = "gitops_repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False, unique=True)
    github_repo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    github_repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
    last_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    initialized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization")
