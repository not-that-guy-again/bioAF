from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Environment(Base):
    __tablename__ = "environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    env_type: Mapped[str] = mapped_column(String(50), nullable=False)
    yaml_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    jupyter_kernel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization = relationship("Organization")
    created_by = relationship("User")
    packages = relationship("EnvironmentPackage", back_populates="environment", lazy="selectin")


class EnvironmentPackage(Base):
    __tablename__ = "environment_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    environment_id: Mapped[int] = mapped_column(Integer, ForeignKey("environments.id"), nullable=False)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    environment = relationship("Environment", back_populates="packages")
