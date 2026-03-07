"""
Generate Phase 9 mock data for GEO export and reference data management.

Idempotent: deletes and recreates demo data on each run.
Uses deterministic seeded random for reproducibility.

Extends Phase 8 mock data with:
- Mock reference datasets (genomes, annotations, indices, custom markers)
- Pipeline run -> reference linkages
- Experiments with complete/incomplete GEO export metadata
- Files with checksums for GEO export demonstration

Usage:
  cd backend && python -m scripts.generate_phase9_mock_data
  # or from project root:
  python scripts/generate_phase9_mock_data.py
"""

import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "backend")

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.batch import Batch  # noqa: E402
from app.models.experiment import Experiment  # noqa: E402
from app.models.file import File  # noqa: E402
from app.models.pipeline_run import PipelineRun, PipelineRunSample  # noqa: E402
from app.models.pipeline_run_review import PipelineRunReview  # noqa: E402
from app.models.reference_dataset import (  # noqa: E402
    ReferenceDataset,
    ReferenceDatasetFile,
    pipeline_run_references,
)
from app.models.sample import Sample  # noqa: E402
from app.services.vocabulary_validator import _derive_instrument_platform  # noqa: E402

SEED = 99
random.seed(SEED)

DEMO_PREFIX = "Phase9 Demo"
NOW = datetime.now(timezone.utc)


def fake_md5(name: str) -> str:
    """Deterministic fake MD5 from a string."""
    return hashlib.md5(name.encode()).hexdigest()


async def cleanup(session: AsyncSession):
    """Remove previously generated Phase 9 demo data."""
    # Clean up reference datasets
    result = await session.execute(
        select(ReferenceDataset).where(ReferenceDataset.name.like(f"{DEMO_PREFIX}%"))
    )
    demo_refs = list(result.scalars().all())
    for ref in demo_refs:
        # Remove pipeline_run_references links
        await session.execute(
            pipeline_run_references.delete().where(
                pipeline_run_references.c.reference_dataset_id == ref.id
            )
        )
        await session.execute(
            delete(ReferenceDatasetFile).where(
                ReferenceDatasetFile.reference_dataset_id == ref.id
            )
        )
    # Clear superseded_by before deleting (to avoid FK constraint)
    for ref in demo_refs:
        ref.superseded_by_id = None
    await session.flush()
    for ref in demo_refs:
        await session.execute(
            delete(ReferenceDataset).where(ReferenceDataset.id == ref.id)
        )

    # Clean up demo experiments
    result = await session.execute(
        select(Experiment).where(Experiment.name.like(f"{DEMO_PREFIX}%"))
    )
    demo_exps = list(result.scalars().all())
    for exp in demo_exps:
        runs_result = await session.execute(
            select(PipelineRun).where(PipelineRun.experiment_id == exp.id)
        )
        for run in runs_result.scalars().all():
            await session.execute(
                delete(PipelineRunReview).where(
                    PipelineRunReview.pipeline_run_id == run.id
                )
            )
            await session.execute(
                delete(PipelineRunSample).where(
                    PipelineRunSample.pipeline_run_id == run.id
                )
            )
            await session.execute(
                pipeline_run_references.delete().where(
                    pipeline_run_references.c.pipeline_run_id == run.id
                )
            )
        await session.execute(
            delete(PipelineRun).where(PipelineRun.experiment_id == exp.id)
        )
        await session.execute(
            delete(File).where(File.gcs_uri.contains(f"/experiments/{exp.id}/"))
        )
        await session.execute(delete(Sample).where(Sample.experiment_id == exp.id))
        await session.execute(delete(Batch).where(Batch.experiment_id == exp.id))
        await session.execute(delete(Experiment).where(Experiment.id == exp.id))

    await session.flush()
    print(
        f"Cleaned up {len(demo_refs)} reference datasets, {len(demo_exps)} experiments."
    )


async def create_reference_datasets(
    session: AsyncSession, org_id: int, user_id: int
) -> list[ReferenceDataset]:
    """Create mock reference datasets: genomes, annotations, indices, markers."""
    configs = [
        {
            "name": f"{DEMO_PREFIX}: GRCh38 GENCODE",
            "category": "genome",
            "scope": "public",
            "version": "v43",
            "source_url": "https://www.gencodegenes.org/human/release_43.html",
            "gcs_prefix": "gs://bioaf-references/GRCh38/gencode_v43/",
            "total_size_bytes": 3_200_000_000,
            "file_count": 4,
            "status": "active",
            "files": [
                ("GRCh38.primary_assembly.genome.fa", "fasta", 3_000_000_000),
                ("GRCh38.primary_assembly.genome.fa.fai", "fai", 500_000),
                ("gencode.v43.annotation.gtf", "gtf", 180_000_000),
                ("gencode.v43.annotation.gff3", "gff3", 200_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: GRCh38 GENCODE",
            "category": "genome",
            "scope": "public",
            "version": "v44",
            "source_url": "https://www.gencodegenes.org/human/release_44.html",
            "gcs_prefix": "gs://bioaf-references/GRCh38/gencode_v44/",
            "total_size_bytes": 3_250_000_000,
            "file_count": 4,
            "status": "active",
            "files": [
                ("GRCh38.primary_assembly.genome.fa", "fasta", 3_000_000_000),
                ("GRCh38.primary_assembly.genome.fa.fai", "fai", 500_000),
                ("gencode.v44.annotation.gtf", "gtf", 185_000_000),
                ("gencode.v44.annotation.gff3", "gff3", 205_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: GRCm39 GENCODE",
            "category": "genome",
            "scope": "public",
            "version": "M33",
            "source_url": "https://www.gencodegenes.org/mouse/release_M33.html",
            "gcs_prefix": "gs://bioaf-references/GRCm39/gencode_M33/",
            "total_size_bytes": 2_800_000_000,
            "file_count": 3,
            "status": "active",
            "files": [
                ("GRCm39.primary_assembly.genome.fa", "fasta", 2_700_000_000),
                ("GRCm39.primary_assembly.genome.fa.fai", "fai", 400_000),
                ("gencode.vM33.annotation.gtf", "gtf", 120_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: STARsolo GRCh38 Index",
            "category": "index",
            "scope": "internal",
            "version": "2.7.11a-v43",
            "gcs_prefix": "gs://bioaf-references/indices/star/GRCh38_v43/",
            "total_size_bytes": 32_000_000_000,
            "file_count": 8,
            "status": "active",
            "files": [
                ("Genome", "star_index", 3_200_000_000),
                ("SA", "star_index", 24_000_000_000),
                ("SAindex", "star_index", 1_500_000_000),
                ("chrName.txt", "txt", 1_000),
                ("chrLength.txt", "txt", 500),
                ("chrStart.txt", "txt", 500),
                ("genomeParameters.txt", "txt", 200),
                ("sjdbList.fromGTF.out.tab", "txt", 5_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: Custom Markers",
            "category": "markers",
            "scope": "internal",
            "version": "v2",
            "gcs_prefix": "gs://bioaf-references/custom/markers_v2/",
            "total_size_bytes": 500_000,
            "file_count": 2,
            "status": "deprecated",
            "deprecation_note": "Superseded by v3 with updated PBMC markers.",
            "files": [
                ("cell_markers_v2.csv", "csv", 250_000),
                ("marker_metadata_v2.json", "json", 50_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: Custom Markers",
            "category": "markers",
            "scope": "internal",
            "version": "v3",
            "gcs_prefix": "gs://bioaf-references/custom/markers_v3/",
            "total_size_bytes": 600_000,
            "file_count": 2,
            "status": "active",
            "files": [
                ("cell_markers_v3.csv", "csv", 300_000),
                ("marker_metadata_v3.json", "json", 60_000),
            ],
        },
    ]

    refs = []
    for cfg in configs:
        ref = ReferenceDataset(
            organization_id=org_id,
            name=cfg["name"],
            category=cfg["category"],
            scope=cfg["scope"],
            version=cfg["version"],
            source_url=cfg.get("source_url"),
            gcs_prefix=cfg["gcs_prefix"],
            total_size_bytes=cfg.get("total_size_bytes"),
            file_count=cfg.get("file_count"),
            uploaded_by_user_id=user_id,
            status=cfg["status"],
            deprecation_note=cfg.get("deprecation_note"),
        )
        session.add(ref)
        await session.flush()

        # Create files
        for fname, ftype, fsize in cfg["files"]:
            gcs_uri = f"{cfg['gcs_prefix']}{fname}"
            rdf = ReferenceDatasetFile(
                reference_dataset_id=ref.id,
                filename=fname,
                gcs_uri=gcs_uri,
                size_bytes=fsize,
                md5_checksum=fake_md5(gcs_uri),
                file_type=ftype,
            )
            session.add(rdf)

        await session.flush()
        refs.append(ref)

    # Link superseded: markers v2 -> v3
    markers_v2 = refs[4]  # Custom Markers v2
    markers_v3 = refs[5]  # Custom Markers v3
    markers_v2.superseded_by_id = markers_v3.id
    await session.flush()

    print(f"Created {len(refs)} reference datasets.")
    return refs


async def create_geo_experiments(
    session: AsyncSession, org_id: int, user_id: int
) -> list[Experiment]:
    """Create 2 experiments: one GEO-ready, one with missing fields."""
    configs = [
        {
            "name": f"{DEMO_PREFIX}: Complete PBMC scRNA-seq",
            "hypothesis": "Treatment alters CD8+ T cell proportions in PBMCs",
            "description": "Single-cell RNA-seq of human PBMCs under drug treatment. "
            "This experiment has complete metadata for GEO submission.",
            "status": "analysis_complete",
        },
        {
            "name": f"{DEMO_PREFIX}: Incomplete Tumor Dataset",
            "hypothesis": "Tumor microenvironment shifts with therapy",
            "description": "Incomplete metadata — missing organism, library info on some samples.",
            "status": "pipeline_complete",
        },
    ]

    experiments = []
    for cfg in configs:
        exp = Experiment(
            organization_id=org_id,
            name=cfg["name"],
            hypothesis=cfg["hypothesis"],
            description=cfg["description"],
            status=cfg["status"],
            owner_user_id=user_id,
            start_date=(NOW - timedelta(days=60)).date(),
        )
        session.add(exp)
        await session.flush()
        experiments.append(exp)

    print(f"Created {len(experiments)} GEO demo experiments.")
    return experiments


async def create_geo_samples(
    session: AsyncSession, experiments: list[Experiment]
) -> dict[int, list[Sample]]:
    """Create samples: exp[0] fully populated, exp[1] missing fields."""
    all_samples: dict[int, list[Sample]] = {}

    # Experiment 0: Complete samples
    exp_complete = experiments[0]
    complete_samples = []
    treatments = [
        "Control",
        "Drug_A_10uM",
        "Drug_A_50uM",
        "Drug_B_10uM",
        "Drug_B_50uM",
        "Combo",
    ]
    for j, treatment in enumerate(treatments):
        s = Sample(
            experiment_id=exp_complete.id,
            sample_id_external=f"PBMC-{j + 1:03d}",
            organism="Homo sapiens",
            tissue_type="PBMC",
            donor_source="Healthy donor",
            treatment_condition=treatment,
            molecule_type="total RNA",
            library_prep_method="10x Chromium 3' v3.1",
            library_layout="paired",
            chemistry_version="v3.1",
            status="analysis_complete",
            qc_status="pass",
            cell_count=random.randint(5000, 12000),
        )
        session.add(s)
        complete_samples.append(s)
    await session.flush()
    all_samples[exp_complete.id] = complete_samples

    # Experiment 1: Incomplete samples (missing organism, library info on some)
    exp_incomplete = experiments[1]
    incomplete_samples = []
    for j in range(4):
        s = Sample(
            experiment_id=exp_incomplete.id,
            sample_id_external=f"TUM-{j + 1:03d}",
            organism="Homo sapiens" if j < 2 else None,  # Missing organism
            tissue_type="Tumor" if j < 3 else None,
            molecule_type="total RNA" if j < 2 else None,  # Missing molecule_type
            library_prep_method="10x Chromium 3' v3.1"
            if j == 0
            else None,  # Mostly missing
            library_layout="paired" if j < 2 else None,
            status="pipeline_complete",
            qc_status="pass" if j < 3 else "fail",
        )
        session.add(s)
        incomplete_samples.append(s)
    await session.flush()
    all_samples[exp_incomplete.id] = incomplete_samples

    total = sum(len(v) for v in all_samples.values())
    print(
        f"Created {total} samples ({len(complete_samples)} complete, {len(incomplete_samples)} incomplete)."
    )
    return all_samples


async def create_geo_batches(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
) -> list[Batch]:
    """Create batches with instrument metadata."""
    batches = []

    # Complete experiment: 2 batches
    exp_complete = experiments[0]
    exp_samples = samples[exp_complete.id]
    for batch_idx, (start, end) in enumerate([(0, 3), (3, 6)]):
        platform = _derive_instrument_platform("Illumina NovaSeq 6000")
        b = Batch(
            experiment_id=exp_complete.id,
            name=f"PBMC-Batch-{batch_idx + 1}",
            instrument_model="Illumina NovaSeq 6000",
            instrument_platform=platform,
            quality_score_encoding="Phred+33",
            sequencer_run_id=f"240101_A00{batch_idx + 1}23_0456_BHKWVTDRX3",
            prep_date=(NOW - timedelta(days=45 - batch_idx)).date(),
        )
        session.add(b)
        await session.flush()
        for s in exp_samples[start:end]:
            s.batch_id = b.id
        await session.flush()
        batches.append(b)

    # Incomplete experiment: 1 batch
    exp_incomplete = experiments[1]
    inc_samples = samples[exp_incomplete.id]
    b = Batch(
        experiment_id=exp_incomplete.id,
        name="Tumor-Batch-1",
        instrument_model="Illumina NextSeq 2000",
        instrument_platform=_derive_instrument_platform("Illumina NextSeq 2000"),
        sequencer_run_id="240210_VH00234_0078_AACFHGTM5",
        prep_date=(NOW - timedelta(days=30)).date(),
    )
    session.add(b)
    await session.flush()
    for s in inc_samples:
        s.batch_id = b.id
    await session.flush()
    batches.append(b)

    print(f"Created {len(batches)} batches.")
    return batches


async def create_geo_pipeline_runs(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
    refs: list[ReferenceDataset],
    org_id: int,
    user_id: int,
) -> list[PipelineRun]:
    """Create pipeline runs and link to reference datasets."""
    runs = []

    # Complete experiment: 1 reviewed+approved run
    exp_complete = experiments[0]
    completed_at = NOW - timedelta(hours=48)
    run1 = PipelineRun(
        organization_id=org_id,
        experiment_id=exp_complete.id,
        submitted_by_user_id=user_id,
        pipeline_name="nf-core/scrnaseq",
        pipeline_version="2.7.0",
        parameters_json={
            "genome": "GRCh38",
            "aligner": "starsolo",
            "reference_path": "/data/references/GRCh38/gencode_v44/",
            "index_path": "/data/references/indices/star/GRCh38_v43/",
        },
        reference_genome="GRCh38",
        alignment_algorithm="STARsolo",
        status="completed",
        work_dir="/data/working/nextflow/geo-demo-run-1",
        started_at=completed_at - timedelta(hours=6),
        completed_at=completed_at,
    )
    session.add(run1)
    await session.flush()

    # Link samples
    for s in samples[exp_complete.id]:
        session.add(PipelineRunSample(pipeline_run_id=run1.id, sample_id=s.id))
    await session.flush()

    # Link references: GRCh38 v44 genome + STARsolo index
    grch38_v44 = refs[1]  # GRCh38 GENCODE v44
    star_index = refs[3]  # STARsolo GRCh38 Index
    await session.execute(
        pipeline_run_references.insert().values(
            pipeline_run_id=run1.id, reference_dataset_id=grch38_v44.id
        )
    )
    await session.execute(
        pipeline_run_references.insert().values(
            pipeline_run_id=run1.id, reference_dataset_id=star_index.id
        )
    )

    # Create review: approved
    review = PipelineRunReview(
        pipeline_run_id=run1.id,
        reviewer_user_id=user_id,
        verdict="approved",
        notes="All QC metrics excellent. Ready for GEO submission.",
        reviewed_at=completed_at + timedelta(hours=12),
    )
    session.add(review)
    await session.flush()
    runs.append(run1)

    # Incomplete experiment: 1 completed (no review)
    exp_incomplete = experiments[1]
    completed_at2 = NOW - timedelta(hours=24)
    run2 = PipelineRun(
        organization_id=org_id,
        experiment_id=exp_incomplete.id,
        submitted_by_user_id=user_id,
        pipeline_name="nf-core/scrnaseq",
        pipeline_version="2.7.0",
        parameters_json={
            "genome": "GRCh38",
            "aligner": "starsolo",
        },
        reference_genome="GRCh38",
        alignment_algorithm="STARsolo",
        status="completed",
        work_dir="/data/working/nextflow/geo-demo-run-2",
        started_at=completed_at2 - timedelta(hours=5),
        completed_at=completed_at2,
    )
    session.add(run2)
    await session.flush()
    for s in samples[exp_incomplete.id]:
        session.add(PipelineRunSample(pipeline_run_id=run2.id, sample_id=s.id))
    await session.flush()
    runs.append(run2)

    print(f"Created {len(runs)} pipeline runs with reference linkages and reviews.")
    return runs


async def create_geo_files(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
    org_id: int,
) -> list[File]:
    """Create file records for GEO export (raw FASTQs + processed files)."""
    files = []

    # Complete experiment: FASTQs + processed for each sample
    exp_complete = experiments[0]
    for s in samples[exp_complete.id]:
        ext_id = s.sample_id_external
        for read in ["R1", "R2"]:
            fname = f"{ext_id}_{read}.fastq.gz"
            f = File(
                organization_id=org_id,
                gcs_uri=f"gs://bioaf-data/experiments/{exp_complete.id}/fastq/{fname}",
                filename=fname,
                size_bytes=random.randint(2_000_000_000, 5_000_000_000),
                md5_checksum=fake_md5(fname),
                file_type="fastq.gz",
            )
            session.add(f)
            files.append(f)

        # Processed: filtered matrix
        matrix_name = f"{ext_id}_filtered_feature_bc_matrix.h5"
        f = File(
            organization_id=org_id,
            gcs_uri=f"gs://bioaf-data/experiments/{exp_complete.id}/processed/{matrix_name}",
            filename=matrix_name,
            size_bytes=random.randint(50_000_000, 200_000_000),
            md5_checksum=fake_md5(matrix_name),
            file_type="h5",
        )
        session.add(f)
        files.append(f)

    # Incomplete experiment: only some files, some missing checksums
    exp_incomplete = experiments[1]
    for i, s in enumerate(samples[exp_incomplete.id][:2]):
        ext_id = s.sample_id_external
        fname = f"{ext_id}_R1.fastq.gz"
        f = File(
            organization_id=org_id,
            gcs_uri=f"gs://bioaf-data/experiments/{exp_incomplete.id}/fastq/{fname}",
            filename=fname,
            size_bytes=random.randint(2_000_000_000, 4_000_000_000),
            md5_checksum=fake_md5(fname)
            if i == 0
            else None,  # Second file missing checksum
            file_type="fastq.gz",
        )
        session.add(f)
        files.append(f)

    await session.flush()
    print(f"Created {len(files)} file records for GEO export.")
    return files


async def main():
    print("=== Phase 9 Mock Data Generator ===\n")

    async with async_session_factory() as session:
        from app.models.user import User

        user_result = await session.execute(
            select(User).where(User.role == "admin").limit(1)
        )
        admin = user_result.scalar_one_or_none()
        if not admin:
            print("ERROR: No admin user found. Run the app setup first.")
            return

        org_id = admin.organization_id
        user_id = admin.id
        print(f"Using admin user: {admin.email} (org_id={org_id})\n")

        # Cleanup
        await cleanup(session)

        # Create reference datasets
        refs = await create_reference_datasets(session, org_id, user_id)

        # Create GEO demo experiments
        experiments = await create_geo_experiments(session, org_id, user_id)
        samples = await create_geo_samples(session, experiments)
        await create_geo_batches(session, experiments, samples)
        runs = await create_geo_pipeline_runs(
            session, experiments, samples, refs, org_id, user_id
        )
        files = await create_geo_files(session, experiments, samples, org_id)

        await session.commit()
        print("\nAll Phase 9 mock data committed successfully.")
        print(f"  Reference datasets: {len(refs)} (1 deprecated, 5 active)")
        print(f"  Experiments: {len(experiments)} (1 GEO-ready, 1 incomplete)")
        print(f"  Samples: {sum(len(v) for v in samples.values())}")
        print(f"  Pipeline runs: {len(runs)} (1 reviewed+approved, 1 unreviewed)")
        print(f"  Files: {len(files)}")
        print("\nGEO export tips:")
        print(
            f"  Complete experiment ID: {experiments[0].id} — should validate all-green"
        )
        print(
            f"  Incomplete experiment ID: {experiments[1].id} — should show validation warnings"
        )


if __name__ == "__main__":
    asyncio.run(main())
