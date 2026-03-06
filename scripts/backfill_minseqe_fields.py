"""
Backfill MINSEQE metadata fields from existing data.

Best-effort migration that populates:
  - pipeline_runs.reference_genome from parameters_json
  - pipeline_runs.alignment_algorithm from parameters_json
  - batches.instrument_model from sequencer_run_id

Usage:
  python scripts/backfill_minseqe_fields.py [--dry-run]
"""

import asyncio
import logging
import sys

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Add the backend directory to the path so we can import app modules
sys.path.insert(0, "backend")

from app.database import async_session_factory  # noqa: E402
from app.models.batch import Batch  # noqa: E402
from app.models.pipeline_run import PipelineRun  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Reference genome mappings (lowercase key -> canonical value)
GENOME_MAPPINGS = {
    "grch38": "GRCh38",
    "hg38": "GRCh38",
    "grch37": "GRCh37",
    "hg19": "GRCh37",
    "grcm39": "GRCm39",
    "mm39": "GRCm39",
    "grcm38": "GRCm38",
    "mm10": "GRCm38",
    "t2t-chm13": "T2T-CHM13",
}

# Alignment algorithm mappings (lowercase key -> canonical value)
ALIGNER_MAPPINGS = {
    "star": "STARsolo",
    "starsolo": "STARsolo",
    "cellranger": "CellRanger",
    "salmon": "Salmon/Alevin",
    "alevin": "Salmon/Alevin",
    "kallisto": "Kallisto-Bustools",
    "kb": "Kallisto-Bustools",
}

# Illumina instrument prefixes in sequencer_run_id (first field after splitting by _)
INSTRUMENT_PREFIXES = {
    "A": "Illumina NovaSeq 6000",
    "LH": "Illumina NovaSeq X",
    "M": "Illumina MiSeq",
    "N": "Illumina NextSeq 500",
    "VH": "Illumina NextSeq 2000",
    "D": "Illumina HiSeq 2500",
    "J": "Illumina HiSeq 3000",
    "K": "Illumina HiSeq 4000",
}

# Parameter keys to check for genome references
GENOME_PARAM_KEYS = ["genome", "reference", "fasta", "genomeDir", "ref_genome"]

# Parameter keys to check for aligner
ALIGNER_PARAM_KEYS = ["aligner", "alignment_algorithm", "mapper"]


def _extract_genome(params: dict) -> str | None:
    """Try to extract a canonical genome name from pipeline parameters."""
    for key in GENOME_PARAM_KEYS:
        val = params.get(key)
        if val and isinstance(val, str):
            # Check direct mapping
            canonical = GENOME_MAPPINGS.get(val.lower())
            if canonical:
                return canonical
            # Check if any known genome name appears in the value
            for pattern, mapped in GENOME_MAPPINGS.items():
                if pattern in val.lower():
                    return mapped
    return None


def _extract_aligner(params: dict) -> str | None:
    """Try to extract a canonical aligner name from pipeline parameters."""
    for key in ALIGNER_PARAM_KEYS:
        val = params.get(key)
        if val and isinstance(val, str):
            canonical = ALIGNER_MAPPINGS.get(val.lower())
            if canonical:
                return canonical
    return None


def _extract_instrument_from_run_id(run_id: str) -> str | None:
    """Parse Illumina sequencer_run_id to infer instrument model.

    Illumina run IDs typically follow: YYMMDD_<InstrumentID>_<RunNumber>_<Flowcell>
    The instrument ID prefix indicates the instrument type.
    """
    parts = run_id.split("_")
    if len(parts) < 2:
        return None

    instrument_id = parts[1]
    # Try matching longest prefixes first
    for prefix in sorted(INSTRUMENT_PREFIXES.keys(), key=len, reverse=True):
        if instrument_id.startswith(prefix):
            return INSTRUMENT_PREFIXES[prefix]
    return None


async def backfill_pipeline_runs(session: AsyncSession, dry_run: bool) -> tuple[int, int]:
    """Backfill reference_genome and alignment_algorithm from parameters_json."""
    result = await session.execute(
        select(PipelineRun).where(
            (PipelineRun.reference_genome.is_(None)) | (PipelineRun.alignment_algorithm.is_(None))
        )
    )
    runs = list(result.scalars().all())

    updated = 0
    skipped = 0

    for run in runs:
        params = run.parameters_json or {}
        changes = {}

        if run.reference_genome is None:
            genome = _extract_genome(params)
            if genome:
                changes["reference_genome"] = genome

        if run.alignment_algorithm is None:
            aligner = _extract_aligner(params)
            if aligner:
                changes["alignment_algorithm"] = aligner

        if changes:
            if not dry_run:
                await session.execute(
                    update(PipelineRun).where(PipelineRun.id == run.id).values(**changes)
                )
            logger.info("Run %d: %s", run.id, changes)
            updated += 1
        else:
            logger.debug("Run %d: no mappable fields found, skipping", run.id)
            skipped += 1

    return updated, skipped


async def backfill_batches(session: AsyncSession, dry_run: bool) -> tuple[int, int]:
    """Backfill instrument_model from sequencer_run_id."""
    result = await session.execute(
        select(Batch).where(
            Batch.instrument_model.is_(None),
            Batch.sequencer_run_id.isnot(None),
        )
    )
    batches = list(result.scalars().all())

    updated = 0
    skipped = 0

    for batch in batches:
        instrument = _extract_instrument_from_run_id(batch.sequencer_run_id)
        if instrument:
            if not dry_run:
                await session.execute(
                    update(Batch).where(Batch.id == batch.id).values(instrument_model=instrument)
                )
            logger.info("Batch %d: instrument_model = %s (from %s)", batch.id, instrument, batch.sequencer_run_id)
            updated += 1
        else:
            logger.debug("Batch %d: could not infer instrument from '%s'", batch.id, batch.sequencer_run_id)
            skipped += 1

    return updated, skipped


async def main(dry_run: bool = False):
    mode = "DRY RUN" if dry_run else "LIVE"
    logger.info("Starting MINSEQE backfill (%s)", mode)

    async with async_session_factory() as session:
        pr_updated, pr_skipped = await backfill_pipeline_runs(session, dry_run)
        logger.info("Pipeline runs: %d updated, %d skipped", pr_updated, pr_skipped)

        b_updated, b_skipped = await backfill_batches(session, dry_run)
        logger.info("Batches: %d updated, %d skipped", b_updated, b_skipped)

        if not dry_run:
            await session.commit()
            logger.info("Changes committed.")
        else:
            logger.info("Dry run complete. No changes were made.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run))
