"""Manifest-driven ingest service.

Processes manifest files (md5.txt or CSV) to create SequencingBatch and
ManifestEntry records, resolve filenames to samples via naming profiles,
and prepare for file verification.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.manifest_entry import ManifestEntry
from app.models.sequencing_batch import SequencingBatch
from app.services.manifest_parser import parse_manifest
from app.services.naming_profile_parser import match_filename, resolve_entities
from app.services.naming_profile_service import NamingProfileService

logger = logging.getLogger("bioaf.manifest_ingest")


async def process_manifest_ingest(
    manifest_content: str,
    manifest_format: str,
    org_id: int,
    source_bucket: str,
    db: AsyncSession,
    user_id: int | None = None,
) -> SequencingBatch:
    """Process a manifest file through the 6-step ingest flow.

    Steps:
    1. Parse manifest
    2. Create or find SequencingBatch
    3. Resolve samples from filenames
    4. Create ManifestEntry records (all start as 'pending')
    5. Update batch status
    6. Emit events (deferred to caller)

    Returns the SequencingBatch record.
    """
    # Step 1: Parse manifest
    parse_result = parse_manifest(manifest_content, manifest_format)
    batch_number = parse_result.batch_number or f"UNKNOWN-{org_id}"

    # Step 2: Create or find SequencingBatch
    existing = await db.execute(
        select(SequencingBatch).where(
            SequencingBatch.code == batch_number,
            SequencingBatch.organization_id == org_id,
        )
    )
    seq_batch = existing.scalar_one_or_none()

    if seq_batch and seq_batch.status == "complete":
        logger.warning(
            "Duplicate manifest for completed batch %s (org %d)",
            batch_number,
            org_id,
        )
        return seq_batch

    # If the batch already has manifest entries, this is a redelivery.
    # Return the existing batch to avoid creating duplicate entries.
    if seq_batch:
        existing_entries = await db.execute(
            select(ManifestEntry).where(ManifestEntry.sequencing_batch_id == seq_batch.id).limit(1)
        )
        if existing_entries.scalar_one_or_none():
            logger.info(
                "Manifest redelivery for batch %s (org %d), skipping duplicate entry creation",
                batch_number,
                org_id,
            )
            return seq_batch

    if not seq_batch:
        seq_batch = SequencingBatch(
            organization_id=org_id,
            name=f"Sequencing batch {batch_number}",
            code=batch_number,
            status="ingesting",
            expected_file_count=len(parse_result.entries),
        )
        db.add(seq_batch)
        await db.flush()
    else:
        seq_batch.status = "ingesting"
        seq_batch.expected_file_count = len(parse_result.entries)
        await db.flush()

    # Step 3 & 4: Resolve samples and create ManifestEntry records
    profiles = await NamingProfileService.list_profiles(db, org_id, status_filter="active")

    for entry in parse_result.entries:
        # Resolve via naming profiles
        resolved_sample_id = None
        resolved_experiment_id = None
        resolved_project_id = None

        match_result = match_filename(entry.filename, profiles)
        if match_result.status == "matched" and match_result.parse_result:
            parse = match_result.parse_result
            profile = await NamingProfileService.get_profile(db, parse.profile_id) if parse.profile_id else None
            if profile:
                resolution = await resolve_entities(parse, profile, org_id, db)
                resolved_sample_id = resolution.sample_id
                resolved_experiment_id = resolution.experiment_id
                resolved_project_id = resolution.project_id

            # If naming profile extracted a sample_index but didn't resolve
            # a sample (no sample_id segment), try batch-position lookup
            sample_index_str = parse.segments.get("sample_index")
            if sample_index_str and not resolved_sample_id:
                from app.services.sample_service import SampleService

                sample = await SampleService.resolve_by_batch_position(db, seq_batch.id, int(sample_index_str))
                if sample:
                    resolved_sample_id = sample.id
                    resolved_experiment_id = resolved_experiment_id or sample.experiment_id

        # If we resolved a sample but not its experiment, derive from sample
        if resolved_sample_id and not resolved_experiment_id:
            from app.models.sample import Sample

            sample_result = await db.execute(select(Sample).where(Sample.id == resolved_sample_id))
            sample = sample_result.scalar_one_or_none()
            if sample:
                resolved_experiment_id = sample.experiment_id

        # If we have an experiment but not a project, derive from experiment
        if resolved_experiment_id and not resolved_project_id:
            exp_result = await db.execute(select(Experiment).where(Experiment.id == resolved_experiment_id))
            exp = exp_result.scalar_one_or_none()
            if exp:
                resolved_project_id = exp.project_id

        manifest_entry = ManifestEntry(
            sequencing_batch_id=seq_batch.id,
            expected_filename=entry.filename,
            expected_md5=entry.md5,
            resolved_sample_id=resolved_sample_id,
            resolved_experiment_id=resolved_experiment_id,
            resolved_project_id=resolved_project_id,
            status="pending",
        )
        db.add(manifest_entry)

        # Set sample.sequencing_batch_id if resolved and not already set
        if resolved_sample_id:
            from app.models.sample import Sample

            sample_result = await db.execute(select(Sample).where(Sample.id == resolved_sample_id))
            sample = sample_result.scalar_one_or_none()
            if sample and not sample.sequencing_batch_id:
                sample.sequencing_batch_id = seq_batch.id

    await db.flush()

    # Step 5: Reconcile manifest entries against files already in the database.
    # Files may have been ingested before the manifest arrived.
    from app.models.file import File
    from app.models.sample import sample_files

    entries_result = await db.execute(
        select(ManifestEntry).where(
            ManifestEntry.sequencing_batch_id == seq_batch.id,
            ManifestEntry.status == "pending",
        )
    )
    pending_entries = list(entries_result.scalars().all())

    for me in pending_entries:
        file_result = await db.execute(
            select(File).where(File.original_filename == me.expected_filename).order_by(File.id.desc()).limit(1)
        )
        existing_file = file_result.scalar_one_or_none()
        if not existing_file:
            continue

        me.file_id = existing_file.id
        me.last_check_at = datetime.now(timezone.utc)

        # MD5 verification
        if existing_file.md5_checksum and me.expected_md5:
            if existing_file.md5_checksum == me.expected_md5:
                me.status = "verified"
            else:
                me.status = "checksum_mismatch"
                me.error_message = f"Expected {me.expected_md5}, got {existing_file.md5_checksum}"
        else:
            me.status = "verified"

        # Link file to sample
        if me.resolved_sample_id:
            existing_link = await db.execute(
                sample_files.select().where(
                    sample_files.c.sample_id == me.resolved_sample_id,
                    sample_files.c.file_id == existing_file.id,
                )
            )
            if not existing_link.fetchone():
                await db.execute(
                    sample_files.insert().values(sample_id=me.resolved_sample_id, file_id=existing_file.id)
                )

        # Link file to experiment and batch
        if me.resolved_experiment_id and not existing_file.experiment_id:
            existing_file.experiment_id = me.resolved_experiment_id
        existing_file.sequencing_batch_id = seq_batch.id

        seq_batch.ingested_file_count = (seq_batch.ingested_file_count or 0) + 1

        # Check sample completeness for auto-run triggers
        if me.resolved_sample_id and me.status == "verified":
            try:
                from app.services.auto_run_service import AutoRunService

                await AutoRunService.check_and_queue_auto_runs(
                    db,
                    sample_id=me.resolved_sample_id,
                    sequencing_batch_id=seq_batch.id,
                )
            except Exception:
                logger.exception("Auto-run check failed for manifest entry %d", me.id)

    await db.flush()

    return seq_batch


def is_manifest_filename(filename: str, config_filename: str = "md5.txt") -> bool:
    """Check if a filename matches the configured manifest filename."""
    return filename.strip().lower() == config_filename.strip().lower()


async def read_manifest_config(db: AsyncSession) -> dict[str, str]:
    """Read manifest-related config keys from platform_config."""
    keys = [
        "manifest_filename",
        "manifest_format",
        "manifest_retry_interval_minutes",
        "manifest_max_retries",
    ]
    rows = (
        await db.execute(text("SELECT key, value FROM platform_config WHERE key = ANY(:keys)").bindparams(keys=keys))
    ).fetchall()
    config = {r[0]: r[1] for r in rows}
    return {
        "manifest_filename": config.get("manifest_filename", "md5.txt"),
        "manifest_format": config.get("manifest_format", "md5sum"),
        "manifest_retry_interval_minutes": int(config.get("manifest_retry_interval_minutes", "15")),
        "manifest_max_retries": int(config.get("manifest_max_retries", "48")),
    }
