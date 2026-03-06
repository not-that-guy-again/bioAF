import csv
import io

from app.schemas.sample import SampleCreate

COLUMN_MAP = {
    "sample_id": "sample_id_external",
    "external_id": "sample_id_external",
    "sample_id_external": "sample_id_external",
    "organism": "organism",
    "tissue": "tissue_type",
    "tissue_type": "tissue_type",
    "donor": "donor_source",
    "donor_source": "donor_source",
    "treatment": "treatment_condition",
    "treatment_condition": "treatment_condition",
    "chemistry": "chemistry_version",
    "chemistry_version": "chemistry_version",
    "viability": "viability_pct",
    "viability_pct": "viability_pct",
    "cell_count": "cell_count",
    "prep_notes": "prep_notes",
    "notes": "prep_notes",
    "qc_status": "qc_status",
    "qc_notes": "qc_notes",
}

NUMERIC_FIELDS = {"viability_pct", "cell_count"}


def _detect_encoding(content: bytes) -> str:
    for encoding in ["utf-8", "latin-1"]:
        try:
            content.decode(encoding)
            return encoding
        except (UnicodeDecodeError, ValueError):
            continue
    return "utf-8"


def _detect_delimiter(first_line: str) -> str:
    if "\t" in first_line:
        return "\t"
    return ","


def parse_sample_csv(file_content: bytes, experiment_id: int) -> tuple[list[SampleCreate], list[str]]:
    encoding = _detect_encoding(file_content)
    text = file_content.decode(encoding)

    lines = text.strip().splitlines()
    if not lines:
        return [], ["File is empty"]

    delimiter = _detect_delimiter(lines[0])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    if not reader.fieldnames:
        return [], ["No header row found"]

    # Map headers
    header_map = {}
    for raw_header in reader.fieldnames:
        clean = raw_header.strip().lower().replace(" ", "_")
        if clean in COLUMN_MAP:
            header_map[raw_header] = COLUMN_MAP[clean]

    samples = []
    errors = []

    for row_num, row in enumerate(reader, start=2):
        # Skip empty rows
        if all(not v or not v.strip() for v in row.values()):
            continue

        sample_data = {}
        for raw_header, field_name in header_map.items():
            val = row.get(raw_header, "").strip()
            if not val:
                continue
            if field_name in NUMERIC_FIELDS:
                try:
                    if field_name == "cell_count":
                        sample_data[field_name] = int(val)
                    else:
                        sample_data[field_name] = float(val)
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid numeric value '{val}' for {field_name}")
                    continue
            else:
                sample_data[field_name] = val

        try:
            sample = SampleCreate(**sample_data)
            samples.append(sample)
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    return samples, errors
