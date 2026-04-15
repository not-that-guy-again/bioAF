from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

LIBRARY_STATUSES = [
    "planned",
    "prepped",
    "qc_pass",
    "qc_fail",
    "sequenced",
    "retired",
]

INDEX_TYPES = ["none", "single", "dual", "udi"]


class Library(Base):
    __tablename__ = "libraries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    sample_id: Mapped[int] = mapped_column(Integer, ForeignKey("samples.id"), nullable=False, index=True)

    library_id_external: Mapped[str | None] = mapped_column(String(255), nullable=True)

    prep_kit: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prep_protocol_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prep_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assay_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    molecule_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    strandedness: Mapped[str | None] = mapped_column(String(50), nullable=True)
    read_layout: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_read_length: Mapped[int | None] = mapped_column(Integer, nullable=True)

    index_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="none")
    i5_sequence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    i7_sequence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    i5_orientation_convention: Mapped[str | None] = mapped_column(String(50), nullable=True)

    insert_size_mean: Mapped[int | None] = mapped_column(Integer, nullable=True)
    molarity_nm: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    concentration_ng_ul: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    qc_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qc_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    sequencing_batch_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sequencing_batches.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="planned")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "library_id_external", name="uq_libraries_org_external_id"),
        Index("idx_libraries_sample_id", "sample_id"),
        Index("idx_libraries_sequencing_batch_id", "sequencing_batch_id"),
        Index("idx_libraries_i7_i5", "i7_sequence", "i5_sequence"),
    )

    sample = relationship("Sample", back_populates="libraries")
    organization = relationship("Organization")
    sequencing_batch = relationship("SequencingBatch")
    files = relationship("File", back_populates="library")
    barcode_maps = relationship("BarcodeMap", back_populates="library", cascade="all, delete-orphan")
