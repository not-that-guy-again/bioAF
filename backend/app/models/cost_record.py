from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CostRecord(Base):
    __tablename__ = "cost_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    component: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), server_default="USD", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization")
