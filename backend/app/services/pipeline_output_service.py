"""Register pipeline output files as File records in the database."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.models.pipeline_run import PipelineRun, PipelineRunSample
from app.services.file_service import FileService
from app.services.file_type_utils import classify_artifact_type, detect_file_type

logger = logging.getLogger("bioaf.pipeline_output_service")


class PipelineOutputService:
    @staticmethod
    async def register_outputs(
        session: AsyncSession,
        run: PipelineRun,
        collected_files: list[dict],
    ) -> list[File]:
        """Create File records for pipeline outputs and link to the run's samples.

        Args:
            session: DB session (caller commits).
            run: The completed PipelineRun.
            collected_files: Dicts from storage_adapter.collect_outputs()
                with keys: filename, gcs_uri, size_bytes, md5_hash.

        Returns:
            List of newly created File records.
        """
        if not collected_files:
            return []

        # Find samples linked to this run
        result = await session.execute(
            select(PipelineRunSample.sample_id).where(
                PipelineRunSample.pipeline_run_id == run.id
            )
        )
        sample_ids = [row[0] for row in result.all()]

        # Collect existing gcs_uris to skip duplicates
        uris = [f["gcs_uri"] for f in collected_files]
        existing = await session.execute(
            select(File.gcs_uri).where(File.gcs_uri.in_(uris))
        )
        existing_uris: set[str] = {row[0] for row in existing.all()}

        created: list[File] = []

        for file_dict in collected_files:
            gcs_uri = file_dict["gcs_uri"]
            if gcs_uri in existing_uris:
                logger.debug("Skipping duplicate gcs_uri: %s", gcs_uri)
                continue

            filename = file_dict["filename"]
            file_type = detect_file_type(filename)
            artifact_type = classify_artifact_type(filename)

            file_record = await FileService.create_file_record(
                session,
                org_id=run.organization_id,
                user_id=run.submitted_by_user_id,
                filename=filename,
                gcs_uri=gcs_uri,
                size_bytes=file_dict.get("size_bytes"),
                md5_checksum=file_dict.get("md5_hash"),
                file_type=file_type,
                experiment_id=run.experiment_id,
                source_type="pipeline_output",
                source_pipeline_run_id=run.id,
                artifact_type=artifact_type,
            )

            for sample_id in sample_ids:
                await FileService.link_file_to_sample(session, file_record.id, sample_id)

            created.append(file_record)

        logger.info(
            "Registered %d output files for pipeline run %d (skipped %d duplicates)",
            len(created),
            run.id,
            len(collected_files) - len(created),
        )
        return created
