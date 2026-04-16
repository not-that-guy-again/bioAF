from datetime import datetime
from typing import Literal

from pydantic import BaseModel


BarcodeType = Literal[
    "library_index",
    "cell_barcode",
    "umi",
    "sgrna",
    "hashtag",
    "lineage",
    "other",
]

ReadPosition = Literal["R1", "R2", "I1", "I2"]


class BarcodeMapCreate(BaseModel):
    """A single barcode row.

    Two modes:
      - Explicit sequence (``is_pattern_only=False``, the default): ``sequence`` is
        required unless ``whitelist_reference`` is set.
      - Pattern-only (``is_pattern_only=True``): used for UMIs and other
        positional patterns. ``read_position``, ``offset_in_read``, and ``length``
        are required; ``sequence`` must be null.
    """

    barcode_type: BarcodeType
    sequence: str | None = None
    name: str | None = None
    read_position: ReadPosition | None = None
    offset_in_read: int | None = None
    length: int | None = None
    allowed_mismatches: int | None = 1
    whitelist_reference: str | None = None
    attributes_json: dict | None = None
    is_pattern_only: bool = False


class BarcodeMapBulkCreate(BaseModel):
    entries: list[BarcodeMapCreate]


class BarcodeMapResponse(BaseModel):
    id: int
    organization_id: int
    library_id: int
    barcode_type: str
    sequence: str | None = None
    name: str | None = None
    read_position: str | None = None
    offset_in_read: int | None = None
    length: int | None = None
    allowed_mismatches: int | None = None
    whitelist_reference: str | None = None
    attributes_json: dict | None = None
    is_pattern_only: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class BarcodeCollisionEntry(BaseModel):
    """One pair of libraries in the same batch sharing an (i5, i7)."""

    library_a_id: int
    library_b_id: int
    i5_sequence: str | None
    i7_sequence: str | None


class BarcodeFuzzyMatch(BaseModel):
    id: int
    organization_id: int
    library_id: int
    barcode_type: str
    sequence: str
    name: str | None = None
    distance: int

    model_config = {"from_attributes": True}
