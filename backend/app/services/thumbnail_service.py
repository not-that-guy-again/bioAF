"""PDF thumbnail generation and GCS storage.

Renders page 1 of a PDF to a PNG thumbnail and uploads it to a
dedicated _thumbnails/ prefix in the results bucket so the scanner
does not re-index it.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.gcs_storage import GcsStorageService

logger = logging.getLogger("bioaf.thumbnail_service")

THUMBNAIL_PREFIX = "_thumbnails/"
THUMBNAIL_MAX_DIM = 1280
THUMBNAIL_DPI = 150


class ThumbnailService:
    @staticmethod
    def render_pdf_thumbnail(pdf_bytes: bytes) -> bytes | None:
        """Render page 1 of a PDF to a PNG image, fit within THUMBNAIL_MAX_DIM.

        Returns PNG bytes, or None if rendering fails.
        """
        try:
            import fitz

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if doc.page_count == 0:
                doc.close()
                return None

            page = doc[0]
            # Scale so the longest edge fits THUMBNAIL_MAX_DIM
            rect = page.rect
            scale = min(THUMBNAIL_MAX_DIM / rect.width, THUMBNAIL_MAX_DIM / rect.height, THUMBNAIL_DPI / 72.0)
            mat = fitz.Matrix(scale, scale)
            pixmap = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pixmap.tobytes("png")
            doc.close()
            return png_bytes
        except Exception as e:
            logger.warning("Failed to render PDF thumbnail: %s", e)
            return None

    @staticmethod
    async def generate_and_upload(
        session: AsyncSession,
        source_gcs_uri: str,
        plot_entry_id: int,
    ) -> str | None:
        """Download a PDF from GCS, render thumbnail, upload to _thumbnails/.

        Returns the thumbnail GCS URI, or None on failure.
        """
        try:
            from google.cloud import storage as gcs_storage

            credentials = await GcsStorageService.get_credentials(session)
            client = gcs_storage.Client(credentials=credentials)

            # Download the source PDF
            parts = source_gcs_uri.replace("gs://", "").split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1]
            bucket = client.bucket(bucket_name)
            source_blob = bucket.blob(blob_path)
            pdf_bytes = source_blob.download_as_bytes()

            # Render thumbnail
            png_bytes = ThumbnailService.render_pdf_thumbnail(pdf_bytes)
            if not png_bytes:
                return None

            # Upload to _thumbnails/ prefix
            thumb_path = f"{THUMBNAIL_PREFIX}plot_{plot_entry_id}.png"
            thumb_blob = bucket.blob(thumb_path)
            thumb_blob.upload_from_string(png_bytes, content_type="image/png")

            thumb_uri = f"gs://{bucket_name}/{thumb_path}"
            logger.info("Generated thumbnail for plot %d: %s", plot_entry_id, thumb_uri)
            return thumb_uri

        except Exception as e:
            logger.warning("Failed to generate thumbnail for plot %d: %s", plot_entry_id, e)
            return None

    @staticmethod
    async def delete_thumbnail(session: AsyncSession, thumbnail_gcs_uri: str) -> bool:
        """Delete a thumbnail blob from GCS."""
        try:
            from google.cloud import storage as gcs_storage

            credentials = await GcsStorageService.get_credentials(session)
            client = gcs_storage.Client(credentials=credentials)

            parts = thumbnail_gcs_uri.replace("gs://", "").split("/", 1)
            bucket = client.bucket(parts[0])
            blob = bucket.blob(parts[1])
            blob.delete()
            logger.info("Deleted thumbnail: %s", thumbnail_gcs_uri)
            return True
        except Exception as e:
            logger.warning("Failed to delete thumbnail %s: %s", thumbnail_gcs_uri, e)
            return False

    @staticmethod
    async def get_results_bucket(session: AsyncSession) -> str | None:
        """Read results_bucket_name from platform_config."""
        result = await session.execute(text("SELECT value FROM platform_config WHERE key = 'results_bucket_name'"))
        val = result.scalars().first()
        if not val or val == "null":
            return None
        return val
