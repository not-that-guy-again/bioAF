"""Google Sheets column import API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.models.experiment_field_default import DEFAULTABLE_SAMPLE_FIELDS
from app.schemas.sheets_import import (
    ReaderSACreateResponse,
    ReaderSAStatusResponse,
    RecognizedColumn,
    SheetPreviewRequest,
    SheetPreviewResponse,
)
from app.services import sheets_reader_sa_service
from app.services.csv_service import COLUMN_MAP, SAMPLE_FIELDS, _normalize_header
from app.services.google_sheets_service import parse_sheet_url, read_header_row

router = APIRouter(prefix="/api/v1/sheets", tags=["sheets_import"])

# All user-facing sample fields that column headers can be recognized against.
_ALL_SAMPLE_FIELDS = set(SAMPLE_FIELDS)
# The subset that can be configured as experiment-level field defaults.
_DEFAULTABLE_FIELDS = set(DEFAULTABLE_SAMPLE_FIELDS)


@router.get("/reader-sa", response_model=ReaderSAStatusResponse)
async def get_reader_sa_status(
    current_user: dict = require_permission("infrastructure", "view"),
    session: AsyncSession = Depends(get_session),
) -> ReaderSAStatusResponse:
    """Check whether the reader SA exists."""
    status = await sheets_reader_sa_service.get_reader_sa_status(session)
    return ReaderSAStatusResponse(
        exists=bool(status["exists"]),
        email=str(status["email"]) if status["email"] else None,
    )


@router.post("/reader-sa", response_model=ReaderSACreateResponse)
async def create_reader_sa(
    current_user: dict = require_permission("infrastructure", "configure"),
    session: AsyncSession = Depends(get_session),
) -> ReaderSACreateResponse:
    """Create the dedicated reader SA for Google Sheets access."""
    try:
        result = await sheets_reader_sa_service.create_reader_sa(session)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create reader service account: {exc}",
        ) from exc
    return ReaderSACreateResponse(
        email=str(result["email"]),
        message="Reader service account created successfully",
        warning=str(result["warning"]) if result.get("warning") else None,
    )


@router.delete("/reader-sa")
async def delete_reader_sa(
    current_user: dict = require_permission("infrastructure", "configure"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Delete the reader SA and its stored credentials."""
    try:
        await sheets_reader_sa_service.delete_reader_sa(session)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete reader service account: {exc}",
        ) from exc
    return {"message": "Reader service account deleted"}


@router.post("/preview", response_model=SheetPreviewResponse)
async def preview_sheet_headers(
    body: SheetPreviewRequest,
    current_user: dict = require_permission("experiments", "create"),
    session: AsyncSession = Depends(get_session),
) -> SheetPreviewResponse:
    """Read column headers from a Google Sheet and classify them.

    Columns that match known sample fields (via the CSV column map) and
    are part of the defaultable sample fields list are returned as
    ``recognized_columns``.  Everything else lands in ``unknown_columns``.
    """
    # Load reader SA credentials
    try:
        creds = await sheets_reader_sa_service.get_reader_credentials(session)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Parse the sheet URL
    try:
        spreadsheet_id, gid = parse_sheet_url(body.sheet_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Read headers from the sheet
    try:
        headers, sheet_name = read_header_row(creds, spreadsheet_id, gid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        msg = str(exc)
        if "403" in msg or "PERMISSION_DENIED" in msg:
            status = await sheets_reader_sa_service.get_reader_sa_status(session)
            sa_email = status.get("email", "the reader service account")
            # Distinguish "API not enabled" from "sheet not shared"
            if "has not been used" in msg or "it is disabled" in msg or "FORBIDDEN" in msg:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "The Google Sheets API is not enabled in your GCP project. "
                        "Enable it at: https://console.cloud.google.com/apis/library/sheets.googleapis.com"
                    ),
                ) from exc
            raise HTTPException(
                status_code=403,
                detail=(f"Cannot access this spreadsheet. Share it with {sa_email} and try again."),
            ) from exc
        if "404" in msg or "not found" in msg.lower():
            raise HTTPException(
                status_code=404,
                detail="Spreadsheet not found. Check the URL and try again.",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Error reading spreadsheet: {msg}") from exc

    # Classify columns using the existing CSV column map
    recognized: list[RecognizedColumn] = []
    unknown: list[str] = []

    for header in headers:
        normalized = _normalize_header(header)
        mapped_field = COLUMN_MAP.get(normalized)
        if mapped_field and mapped_field in _ALL_SAMPLE_FIELDS:
            recognized.append(
                RecognizedColumn(
                    header=header,
                    mapped_to=mapped_field,
                    defaultable=mapped_field in _DEFAULTABLE_FIELDS,
                )
            )
        else:
            unknown.append(header)

    return SheetPreviewResponse(
        spreadsheet_id=spreadsheet_id,
        sheet_name=sheet_name,
        columns=headers,
        recognized_columns=recognized,
        unknown_columns=unknown,
    )
