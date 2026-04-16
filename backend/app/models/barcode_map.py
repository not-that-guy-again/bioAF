from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

BARCODE_TYPES = [
    "library_index",
    "cell_barcode",
    "umi",
    "sgrna",
    "hashtag",
    "lineage",
    "other",
]

READ_POSITIONS = ["R1", "R2", "I1", "I2"]


class BarcodeMap(Base):
    __tablename__ = "barcode_maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    library_id: Mapped[int] = mapped_column(Integer, ForeignKey("libraries.id"), nullable=False, index=True)

    barcode_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sequence: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    read_position: Mapped[str | None] = mapped_column(String(8), nullable=True)
    offset_in_read: Mapped[int | None] = mapped_column(Integer, nullable=True)
    length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_mismatches: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="1")

    whitelist_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # True for UMIs and other positional patterns that have no concrete sequence
    # (the reader just consumes ``length`` bases starting at ``offset_in_read``).
    is_pattern_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_barcode_maps_library_id", "library_id"),
        Index("idx_barcode_maps_sequence", "sequence"),
        Index("idx_barcode_maps_type_sequence", "barcode_type", "sequence"),
        UniqueConstraint(
            "library_id",
            "barcode_type",
            "sequence",
            "read_position",
            name="uq_barcode_maps_library_type_seq_pos",
        ),
    )

    library = relationship("Library", back_populates="barcode_maps")
    organization = relationship("Organization")
