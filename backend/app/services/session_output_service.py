"""Session output registration service (ADR-040).

Registers files discovered in GCS after a notebook/SSH session shuts down.
Creates File records with source_type=notebook_output and links them to the
session via NotebookSessionFile with access_type=output.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("bioaf.session_outputs")

# System/hidden files to skip during output registration
_EXCLUDED_FILENAMES = {
    ".bash_history",
    ".Rhistory",
    ".bash_logout",
    ".bashrc",
    ".profile",
    ".gitconfig",
    ".DS_Store",
}
_EXCLUDED_PREFIXES = (".git/", "__pycache__/", ".ipynb_checkpoints/", ".cache/", ".local/")


def parse_gsutil_ls_output(raw_output: str) -> list[dict]:
    """Parse gsutil ls -l -r output into a list of {gcs_uri, size_bytes}.

    Each line looks like:
       1234567  2026-04-04T12:00:00Z  gs://bucket/path/to/file.txt
    The final summary line starts with TOTAL: and is skipped.
    """
    files: list[dict] = []
    for line in raw_output.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("TOTAL:"):
            continue
        match = re.match(r"^\s*(\d+)\s+\S+\s+(gs://.+)$", line)
        if match:
            size_bytes = int(match.group(1))
            gcs_uri = match.group(2)
            filename = gcs_uri.rsplit("/", 1)[-1] if "/" in gcs_uri else gcs_uri
            if not filename or filename in _EXCLUDED_FILENAMES:
                continue
            if any(filename.startswith(p.rstrip("/")) for p in _EXCLUDED_PREFIXES):
                continue
            files.append({"gcs_uri": gcs_uri, "size_bytes": size_bytes, "filename": filename})
    return files


def _file_type_from_extension(filename: str) -> str:
    """Derive file_type from filename extension."""
    if filename.lower().endswith(".fastq.gz"):
        return "fastq"
    parts = filename.rsplit(".", 1)
    if len(parts) < 2:
        return "unknown"
    return parts[1].lower()


class SessionOutputService:
    @staticmethod
    async def register_outputs(
        session: AsyncSession,
        session_id: int,
        organization_id: int,
        project_id: int | None,
        experiment_id: int | None,
        user_id: int,
        gcs_files: list[dict],
    ) -> int:
        """Register output files from a completed session.

        Creates File records with source_type=notebook_output and
        NotebookSessionFile records with access_type=output.

        Returns the number of files registered.
        """
        from app.models.file import File
        from app.models.notebook_session_file import NotebookSessionFile

        registered = 0
        for f in gcs_files:
            filename = f["filename"]
            # Skip excluded files
            if filename in _EXCLUDED_FILENAMES or filename.startswith("."):
                if filename in _EXCLUDED_FILENAMES:
                    continue
                base = filename.lstrip(".")
                if not base or "." not in base:
                    continue
            if any(filename.startswith(p.rstrip("/")) for p in _EXCLUDED_PREFIXES):
                continue

            file_record = File(
                organization_id=organization_id,
                gcs_uri=f["gcs_uri"],
                filename=filename,
                size_bytes=f.get("size_bytes"),
                file_type=_file_type_from_extension(filename),
                experiment_id=experiment_id,
                project_id=project_id,
                source_type="notebook_output",
                source_notebook_session_id=session_id,
                uploader_user_id=user_id,
            )
            session.add(file_record)
            await session.flush()

            session.add(
                NotebookSessionFile(
                    session_id=session_id,
                    file_id=file_record.id,
                    access_type="output",
                )
            )
            registered += 1

        if registered:
            logger.info("Registered %d output files for session %d", registered, session_id)

        return registered
