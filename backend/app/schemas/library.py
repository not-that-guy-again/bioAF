from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class LibraryCreate(BaseModel):
    sample_id: int
    library_id_external: str | None = None
    prep_kit: str | None = None
    prep_protocol_version: str | None = None
    prep_date: datetime | None = None
    assay_type: str | None = None
    molecule_type: str | None = None
    strandedness: str | None = None
    read_layout: str | None = None
    target_read_length: int | None = None
    index_type: Literal["none", "single", "dual", "udi"] = "none"
    i5_sequence: str | None = None
    i7_sequence: str | None = None
    i5_orientation_convention: str | None = None
    insert_size_mean: int | None = None
    molarity_nm: Decimal | None = None
    concentration_ng_ul: Decimal | None = None
    qc_status: Literal["pass", "warning", "fail"] | None = None
    qc_notes: str | None = None
    sequencing_batch_id: int | None = None
    notes: str | None = None


class LibraryUpdate(BaseModel):
    library_id_external: str | None = None
    prep_kit: str | None = None
    prep_protocol_version: str | None = None
    prep_date: datetime | None = None
    assay_type: str | None = None
    molecule_type: str | None = None
    strandedness: str | None = None
    read_layout: str | None = None
    target_read_length: int | None = None
    index_type: Literal["none", "single", "dual", "udi"] | None = None
    i5_sequence: str | None = None
    i7_sequence: str | None = None
    i5_orientation_convention: str | None = None
    insert_size_mean: int | None = None
    molarity_nm: Decimal | None = None
    concentration_ng_ul: Decimal | None = None
    qc_status: Literal["pass", "warning", "fail"] | None = None
    qc_notes: str | None = None
    sequencing_batch_id: int | None = None
    status: str | None = None
    notes: str | None = None


class LibraryResponse(BaseModel):
    id: int
    organization_id: int
    sample_id: int
    library_id_external: str | None = None
    prep_kit: str | None = None
    prep_protocol_version: str | None = None
    prep_date: datetime | None = None
    assay_type: str | None = None
    molecule_type: str | None = None
    strandedness: str | None = None
    read_layout: str | None = None
    target_read_length: int | None = None
    index_type: str
    i5_sequence: str | None = None
    i7_sequence: str | None = None
    i5_orientation_convention: str | None = None
    insert_size_mean: int | None = None
    molarity_nm: Decimal | None = None
    concentration_ng_ul: Decimal | None = None
    qc_status: str | None = None
    qc_notes: str | None = None
    sequencing_batch_id: int | None = None
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
