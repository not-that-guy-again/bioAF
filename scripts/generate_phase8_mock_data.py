"""
Generate Phase 8 mock data for MINSEQE metadata and pipeline reviews.

Idempotent: deletes and recreates demo data on each run.
Uses deterministic seeded random for reproducibility.

Usage:
  cd backend && python -m scripts.generate_phase8_mock_data
  # or from project root:
  python scripts/generate_phase8_mock_data.py
"""

import asyncio
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "backend")

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.batch import Batch  # noqa: E402
from app.models.controlled_vocabulary import ControlledVocabulary  # noqa: E402
from app.models.experiment import Experiment  # noqa: E402
from app.models.pipeline_run import PipelineRun, PipelineRunSample  # noqa: E402
from app.models.pipeline_run_review import PipelineRunReview  # noqa: E402
from app.models.sample import Sample  # noqa: E402
from app.services.audit_service import log_action  # noqa: E402
from app.services.vocabulary_validator import _derive_instrument_platform  # noqa: E402

SEED = 42
random.seed(SEED)

# Demo tag used for cleanup
DEMO_TAG = "phase8-demo"

NOW = datetime.now(timezone.utc)


async def cleanup(session: AsyncSession):
    """Remove previously generated demo data."""
    # Find demo experiments by name prefix
    result = await session.execute(
        select(Experiment).where(Experiment.name.like("Phase8 Demo%"))
    )
    demo_exps = list(result.scalars().all())

    for exp in demo_exps:
        # Delete reviews for runs in this experiment
        runs_result = await session.execute(
            select(PipelineRun).where(PipelineRun.experiment_id == exp.id)
        )
        for run in runs_result.scalars().all():
            await session.execute(
                delete(PipelineRunReview).where(PipelineRunReview.pipeline_run_id == run.id)
            )
            await session.execute(
                delete(PipelineRunSample).where(PipelineRunSample.pipeline_run_id == run.id)
            )

        await session.execute(delete(PipelineRun).where(PipelineRun.experiment_id == exp.id))
        await session.execute(delete(Sample).where(Sample.experiment_id == exp.id))
        await session.execute(delete(Batch).where(Batch.experiment_id == exp.id))
        await session.execute(delete(Experiment).where(Experiment.id == exp.id))

    await session.flush()
    print(f"Cleaned up {len(demo_exps)} demo experiments.")


async def create_experiments(session: AsyncSession, org_id: int, user_id: int) -> list[Experiment]:
    """Create 3 demo experiments."""
    configs = [
        {"name": "Phase8 Demo: Human PBMC scRNA-seq", "hypothesis": "PBMC cell type proportions vary with treatment"},
        {"name": "Phase8 Demo: Mouse Brain Atlas", "hypothesis": "Novel cell types in developing mouse cortex"},
        {"name": "Phase8 Demo: Human Tumor Microenvironment", "hypothesis": "Immune infiltration patterns in solid tumors"},
    ]

    experiments = []
    for cfg in configs:
        exp = Experiment(
            organization_id=org_id,
            name=cfg["name"],
            hypothesis=cfg["hypothesis"],
            status="pipeline_complete",
            owner_user_id=user_id,
            start_date=(NOW - timedelta(days=30)).date(),
        )
        session.add(exp)
        await session.flush()
        experiments.append(exp)

    return experiments


async def create_samples(
    session: AsyncSession, experiments: list[Experiment], user_id: int
) -> dict[int, list[Sample]]:
    """Create 4-8 samples per experiment with MINSEQE fields."""
    organisms = ["Human", "Human", "Mouse"]
    tissues = ["PBMC", "Brain", "Tumor"]
    molecule_types = ["total RNA", "total RNA", "total RNA", "polyA RNA"]
    library_preps = ["10x Chromium 3' v3.1", "10x Chromium 3' v3.1", "10x Chromium 3' v3"]

    all_samples: dict[int, list[Sample]] = {}

    for i, exp in enumerate(experiments):
        count = random.choice([4, 5, 6, 7, 8])
        samples = []
        for j in range(count):
            s = Sample(
                experiment_id=exp.id,
                sample_id_external=f"S{i+1:02d}-{j+1:03d}",
                organism=organisms[i],
                tissue_type=tissues[i],
                molecule_type=random.choice(molecule_types),
                library_prep_method=random.choice(library_preps),
                library_layout="paired",
                status="pipeline_complete",
                qc_status="pass" if random.random() > 0.15 else "warning",
            )
            session.add(s)
            samples.append(s)

        await session.flush()
        all_samples[exp.id] = samples

    total = sum(len(v) for v in all_samples.values())
    print(f"Created {total} samples across {len(experiments)} experiments.")
    return all_samples


async def create_batches(
    session: AsyncSession, experiments: list[Experiment], samples: dict[int, list[Sample]]
) -> list[Batch]:
    """Create 4 batches with instrument metadata."""
    instrument_configs = [
        {"instrument_model": "Illumina NovaSeq 6000", "sequencer_run_id": "230915_A00123_0456_BHKWVTDRX3"},
        {"instrument_model": "Illumina NextSeq 2000", "sequencer_run_id": "231001_VH00234_0078_AACFHGTM5"},
        {"instrument_model": "Illumina NovaSeq 6000", "sequencer_run_id": "231015_A00456_0789_BHJKLNDRX3"},
        {"instrument_model": "Illumina NextSeq 2000", "sequencer_run_id": "231022_VH00567_0123_AACMNOPQ5"},
    ]

    batches = []
    batch_idx = 0
    for exp in experiments:
        exp_samples = samples[exp.id]
        # Split samples into 1-2 batches
        mid = len(exp_samples) // 2
        for batch_samples in [exp_samples[:mid], exp_samples[mid:]]:
            if not batch_samples or batch_idx >= len(instrument_configs):
                continue
            cfg = instrument_configs[batch_idx]
            platform = _derive_instrument_platform(cfg["instrument_model"])
            b = Batch(
                experiment_id=exp.id,
                name=f"Batch-{batch_idx + 1}",
                instrument_model=cfg["instrument_model"],
                instrument_platform=platform,
                quality_score_encoding="Phred+33",
                sequencer_run_id=cfg["sequencer_run_id"],
                prep_date=(NOW - timedelta(days=25 - batch_idx)).date(),
            )
            session.add(b)
            await session.flush()

            for s in batch_samples:
                s.batch_id = b.id
            await session.flush()

            batches.append(b)
            batch_idx += 1

    print(f"Created {len(batches)} batches.")
    return batches


async def create_pipeline_runs(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
    org_id: int,
    user_id: int,
) -> list[PipelineRun]:
    """Create 6 pipeline runs (2 per experiment)."""
    runs = []
    run_configs = [
        {"ref": "GRCh38", "aligner": "STARsolo", "hours_ago": 168, "status": "completed"},
        {"ref": "GRCh38", "aligner": "STARsolo", "hours_ago": 120, "status": "completed"},
        {"ref": "GRCm39", "aligner": "STARsolo", "hours_ago": 72, "status": "completed"},
        {"ref": "GRCm39", "aligner": "CellRanger", "hours_ago": 24, "status": "completed"},
        {"ref": "GRCh38", "aligner": "STARsolo", "hours_ago": 96, "status": "completed"},
        {"ref": "GRCh38", "aligner": "Salmon/Alevin", "hours_ago": 48, "status": "completed"},
    ]

    run_idx = 0
    for exp in experiments:
        for _ in range(2):
            if run_idx >= len(run_configs):
                break
            cfg = run_configs[run_idx]
            completed_at = NOW - timedelta(hours=cfg["hours_ago"])
            run = PipelineRun(
                organization_id=org_id,
                experiment_id=exp.id,
                submitted_by_user_id=user_id,
                pipeline_name="nf-core/scrnaseq",
                pipeline_version="2.5.1",
                parameters_json={"genome": cfg["ref"], "aligner": cfg["aligner"].lower()},
                reference_genome=cfg["ref"],
                alignment_algorithm=cfg["aligner"],
                status=cfg["status"],
                work_dir=f"/data/working/nextflow/demo-run-{run_idx + 1}",
                started_at=completed_at - timedelta(hours=4),
                completed_at=completed_at,
            )
            session.add(run)
            await session.flush()

            # Link samples
            for s in samples[exp.id]:
                link = PipelineRunSample(pipeline_run_id=run.id, sample_id=s.id)
                session.add(link)
            await session.flush()

            runs.append(run)
            run_idx += 1

    print(f"Created {len(runs)} pipeline runs.")
    return runs


async def create_reviews(
    session: AsyncSession, runs: list[PipelineRun], samples: dict[int, list[Sample]], user_id: int
):
    """Create 4 reviews on runs 0, 1, 2, 5."""
    review_configs = [
        {
            "run_idx": 0,
            "verdict": "approved",
            "notes": "All QC metrics look excellent. Median genes/cell >3000, low doublet rate.",
        },
        {
            "run_idx": 1,
            "verdict": "approved_with_caveats",
            "notes": "Overall good quality. Sample S01-003 has elevated mitochondrial reads (12%). Recommend monitoring in downstream analysis.",
            "flag_sample_idx": 2,
        },
        {
            "run_idx": 2,
            "verdict": "rejected",
            "notes": "Low cell recovery across most samples. Median UMI/cell below 500. Recommend re-sequencing with higher depth.",
        },
        {
            "run_idx": 5,
            "verdict": "revision_requested",
            "notes": "Alignment rates are good but saturation is low (45%). Consider additional sequencing before proceeding to analysis.",
        },
    ]

    for cfg in review_configs:
        run = runs[cfg["run_idx"]]
        exp_samples = samples[run.experiment_id]

        sample_verdicts = None
        recommended_exclusions = None
        if "flag_sample_idx" in cfg and cfg["flag_sample_idx"] < len(exp_samples):
            flagged = exp_samples[cfg["flag_sample_idx"]]
            sample_verdicts = [
                {"sample_id": flagged.id, "verdict": "approved_with_caveats", "notes": "Elevated mito reads"}
            ]
            recommended_exclusions = [flagged.id]

        review = PipelineRunReview(
            pipeline_run_id=run.id,
            reviewer_user_id=user_id,
            verdict=cfg["verdict"],
            notes=cfg["notes"],
            sample_verdicts_json=sample_verdicts,
            recommended_exclusions=recommended_exclusions,
            reviewed_at=run.completed_at + timedelta(hours=12),
        )
        session.add(review)

        await log_action(
            session,
            user_id=user_id,
            entity_type="pipeline_run_review",
            entity_id=run.id,
            action="create_review",
            details={"verdict": cfg["verdict"]},
        )

    await session.flush()
    print(f"Created {len(review_configs)} reviews.")


async def main():
    print("=== Phase 8 Mock Data Generator ===\n")

    async with async_session_factory() as session:
        # Get first org and admin user for ownership
        from app.models.user import User

        user_result = await session.execute(select(User).where(User.role == "admin").limit(1))
        admin = user_result.scalar_one_or_none()
        if not admin:
            print("ERROR: No admin user found. Run the app setup first.")
            return

        org_id = admin.organization_id
        user_id = admin.id
        print(f"Using admin user: {admin.email} (org_id={org_id})\n")

        # Cleanup
        await cleanup(session)

        # Create data
        experiments = await create_experiments(session, org_id, user_id)
        samples = await create_samples(session, experiments, user_id)
        await create_batches(session, experiments, samples)
        runs = await create_pipeline_runs(session, experiments, samples, org_id, user_id)
        await create_reviews(session, runs, samples, user_id)

        await session.commit()
        print("\nAll mock data committed successfully.")
        print(f"  Experiments: {len(experiments)}")
        print(f"  Samples: {sum(len(v) for v in samples.values())}")
        print(f"  Pipeline runs: {len(runs)}")
        print(f"  Reviews: 4 (runs 3, 4 are unreviewed)")


if __name__ == "__main__":
    asyncio.run(main())
