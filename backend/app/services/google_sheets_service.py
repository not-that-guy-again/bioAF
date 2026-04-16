"""Google Sheets integration for reading spreadsheet headers.

Uses the Google Sheets API v4 to read column headers from a shared
spreadsheet.  The caller is responsible for providing credentials
scoped to ``spreadsheets.readonly``.
"""

import re

from googleapiclient import discovery as google_discovery

_SHEET_URL_RE = re.compile(
    r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)"
)
_GID_RE = re.compile(r"[#&]gid=(\d+)")

# Patchable alias for tests
discovery_build = google_discovery.build


def parse_sheet_url(url: str) -> tuple[str, int | None]:
    """Extract spreadsheet ID and optional gid from a Google Sheets URL.

    Returns ``(spreadsheet_id, gid_or_none)``.
    Raises ``ValueError`` for unrecognised formats.
    """
    m = _SHEET_URL_RE.search(url)
    if not m:
        raise ValueError("Not a valid Google Sheets URL")
    spreadsheet_id = m.group(1)
    gid_match = _GID_RE.search(url)
    gid = int(gid_match.group(1)) if gid_match else None
    return spreadsheet_id, gid


def get_sheet_names(
    credentials: object,
    spreadsheet_id: str,
) -> list[str]:
    """Return the list of sheet/tab names in a spreadsheet."""
    service = discovery_build(
        "sheets", "v4", credentials=credentials, cache_discovery=False
    )
    meta = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties"
    ).execute()
    return [s["properties"]["title"] for s in meta.get("sheets", [])]


def _resolve_sheet_name(
    service: object,
    spreadsheet_id: str,
    gid: int | None,
) -> str:
    """Resolve a gid to a sheet title, or return the first sheet's title."""
    meta = service.spreadsheets().get(  # type: ignore[union-attr]
        spreadsheetId=spreadsheet_id, fields="sheets.properties"
    ).execute()
    sheets = meta.get("sheets", [])
    if not sheets:
        raise ValueError("Spreadsheet has no sheets")
    if gid is not None:
        for s in sheets:
            if s["properties"].get("sheetId") == gid:
                return s["properties"]["title"]
        raise ValueError(f"No sheet found with gid={gid}")
    return sheets[0]["properties"]["title"]


def read_header_row(
    credentials: object,
    spreadsheet_id: str,
    gid: int | None = None,
) -> tuple[list[str], str]:
    """Read the first row of the specified sheet and return column headers.

    If *gid* is ``None`` the first sheet is used.

    Returns ``(headers, sheet_name)``.
    """
    service = discovery_build(
        "sheets", "v4", credentials=credentials, cache_discovery=False
    )
    sheet_name = _resolve_sheet_name(service, spreadsheet_id, gid)
    result = service.spreadsheets().values().get(  # type: ignore[union-attr]
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_name}'!1:1",
    ).execute()
    values = result.get("values", [])
    if not values or not values[0]:
        raise ValueError("The first row is empty -- ensure row 1 contains column headers")
    headers = [str(v).strip() for v in values[0] if str(v).strip()]
    return headers, sheet_name
