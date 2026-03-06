from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserQuota(Base):
    __tablename__ = "user_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    cpu_hours_monthly_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_hours_used_current_month: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, server_default="0")
    quota_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    organization = relationship("Organization")
