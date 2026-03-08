"""
Unified POC seed script — populates a fresh bioAF deployment with realistic
demo data for computational-biology audiences.

Idempotent: safe to re-run.  Deletes demo data tagged with known prefixes
before re-inserting.

Creates:
  - 1 organization, 3 users (admin, comp_bio, viewer)
  - 3 experiments with samples, batches, MINSEQE metadata
  - 6 pipeline runs with reviews
  - 6 reference datasets with files
  - 2 GEO-readiness demo experiments (complete + incomplete)
  - 1 cross-experiment project with project samples
  - ~20 analysis snapshots (anndata + seurat)
  - 4 template notebooks
  - 8 notebook sessions (active + historical)
  - 15 SLURM jobs (completed, running, pending)
  - Activity feed entries spanning the last 2 weeks
  - User quotas

Usage (from project root, with DATABASE_URL configured):
    python scripts/seed_poc_data.py

Or inside a running container:
    docker compose -f docker-compose.poc.yml exec backend \
        python scripts/seed_poc_data.py
"""

import asyncio
import hashlib
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, "backend")

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.activity_feed import ActivityFeedEntry  # noqa: E402
from app.models.analysis_snapshot import AnalysisSnapshot  # noqa: E402
from app.models.batch import Batch  # noqa: E402
from app.models.experiment import Experiment  # noqa: E402
from app.models.file import File  # noqa: E402
from app.models.notebook_session import NotebookSession  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.pipeline_run import PipelineRun, PipelineRunSample  # noqa: E402
from app.models.pipeline_run_review import PipelineRunReview  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.project_sample import ProjectSample  # noqa: E402
from app.models.reference_dataset import (  # noqa: E402
    ReferenceDataset,
    ReferenceDatasetFile,
    pipeline_run_references,
)
from app.models.sample import Sample  # noqa: E402
from app.models.slurm_job import SlurmJob  # noqa: E402
from app.models.template_notebook import TemplateNotebook  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_quota import UserQuota  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.services.vocabulary_validator import _derive_instrument_platform  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)

NOW = datetime.now(timezone.utc)
DEMO_PREFIX = "POC Demo"

# Default demo passwords — printed at the end so the deployer knows them
DEMO_PASSWORDS = {
    "maria@bioaf-demo.org": "demo-admin-2026",
    "sarah@bioaf-demo.org": "demo-compbio-2026",
    "alex@bioaf-demo.org": "demo-viewer-2026",
}


def fake_md5(name: str) -> str:
    return hashlib.md5(name.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════════════════════════
async def cleanup(session: AsyncSession) -> None:
    """Remove all POC demo data so the script is idempotent."""
    # Activity feed
    await session.execute(
        delete(ActivityFeedEntry).where(
            ActivityFeedEntry.summary.like(f"%{DEMO_PREFIX}%")
        )
    )

    # Notebook sessions & SLURM jobs (by user email lookup later — nuke all
    # for the demo org instead)
    demo_org = (
        await session.execute(
            select(Organization).where(Organization.name == f"{DEMO_PREFIX} Lab")
        )
    ).scalar_one_or_none()

    if demo_org:
        org_id = demo_org.id

        await session.execute(
            delete(SlurmJob).where(SlurmJob.organization_id == org_id)
        )
        await session.execute(
            delete(NotebookSession).where(NotebookSession.organization_id == org_id)
        )
        await session.execute(
            delete(TemplateNotebook).where(TemplateNotebook.organization_id == org_id)
        )
        await session.execute(
            delete(AnalysisSnapshot).where(AnalysisSnapshot.organization_id == org_id)
        )
        await session.execute(
            delete(UserQuota).where(UserQuota.organization_id == org_id)
        )

        # Projects (and project_samples)
        proj_result = await session.execute(
            select(Project).where(Project.organization_id == org_id)
        )
        for proj in proj_result.scalars().all():
            await session.execute(
                delete(ProjectSample).where(ProjectSample.project_id == proj.id)
            )
            await session.execute(
                delete(PipelineRun).where(PipelineRun.project_id == proj.id)
            )
        await session.execute(
            delete(Project).where(Project.organization_id == org_id)
        )

        # Experiments cascade
        exp_result = await session.execute(
            select(Experiment).where(Experiment.organization_id == org_id)
        )
        for exp in exp_result.scalars().all():
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
                delete(File).where(
                    File.gcs_uri.contains(f"/experiments/{exp.id}/")
                )
            )
            await session.execute(
                delete(Sample).where(Sample.experiment_id == exp.id)
            )
            await session.execute(
                delete(Batch).where(Batch.experiment_id == exp.id)
            )
        await session.execute(
            delete(Experiment).where(Experiment.organization_id == org_id)
        )

        # Reference datasets
        ref_result = await session.execute(
            select(ReferenceDataset).where(
                ReferenceDataset.organization_id == org_id
            )
        )
        demo_refs = list(ref_result.scalars().all())
        for ref in demo_refs:
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
        for ref in demo_refs:
            ref.superseded_by_id = None
        await session.flush()
        for ref in demo_refs:
            await session.execute(
                delete(ReferenceDataset).where(ReferenceDataset.id == ref.id)
            )

        # Users & org
        await session.execute(delete(User).where(User.organization_id == org_id))
        await session.execute(
            delete(Organization).where(Organization.id == org_id)
        )

    await session.flush()
    print("Cleanup complete.")


# ═══════════════════════════════════════════════════════════════════════════
# Organization & Users
# ═══════════════════════════════════════════════════════════════════════════
async def create_org_and_users(
    session: AsyncSession,
) -> tuple[int, dict[str, "User"]]:
    org = Organization(name=f"{DEMO_PREFIX} Lab", setup_complete=True)
    session.add(org)
    await session.flush()

    users = {}
    user_configs = [
        ("Maria Chen", "maria@bioaf-demo.org", "admin"),
        ("Sarah Kim", "sarah@bioaf-demo.org", "comp_bio"),
        ("Alex Rivera", "alex@bioaf-demo.org", "viewer"),
    ]
    for name, email, role in user_configs:
        u = User(
            organization_id=org.id,
            email=email,
            name=name,
            password_hash=AuthService.hash_password(DEMO_PASSWORDS[email]),
            role=role,
            status="active",
        )
        session.add(u)
        users[role] = u
    await session.flush()

    # Quotas
    first_of_month = NOW.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for role, u in users.items():
        limit = {"admin": 500, "comp_bio": 200, "viewer": 50}[role]
        used = {"admin": Decimal("12.5"), "comp_bio": Decimal("87.3"), "viewer": Decimal("0")}[role]
        q = UserQuota(
            user_id=u.id,
            organization_id=org.id,
            cpu_hours_monthly_limit=limit,
            cpu_hours_used_current_month=used,
            quota_reset_at=first_of_month + timedelta(days=32),
        )
        session.add(q)
    await session.flush()

    print(f"Created org '{org.name}' (id={org.id}) with {len(users)} users.")
    return org.id, users


# ═══════════════════════════════════════════════════════════════════════════
# Experiments, Samples, Batches
# ═══════════════════════════════════════════════════════════════════════════
async def create_experiments(
    session: AsyncSession, org_id: int, admin: User, comp_bio: User
) -> tuple[list[Experiment], dict[int, list[Sample]]]:
    exp_configs = [
        {
            "name": f"{DEMO_PREFIX}: Human PBMC scRNA-seq",
            "hypothesis": "PBMC cell type proportions vary with treatment",
            "description": "Single-cell RNA-seq of human PBMCs under drug treatment with complete MINSEQE metadata.",
            "status": "analysis",
            "owner": comp_bio,
            "days_ago": 45,
        },
        {
            "name": f"{DEMO_PREFIX}: Mouse Brain Atlas",
            "hypothesis": "Novel cell types in developing mouse cortex",
            "description": "Spatial transcriptomics atlas of developing mouse cortex P0-P14.",
            "status": "pipeline_complete",
            "owner": comp_bio,
            "days_ago": 30,
        },
        {
            "name": f"{DEMO_PREFIX}: Human Tumor Microenvironment",
            "hypothesis": "Immune infiltration patterns in solid tumors",
            "description": "Multi-sample tumor microenvironment profiling across 3 tumor types.",
            "status": "reviewed",
            "owner": admin,
            "days_ago": 60,
        },
    ]

    organisms = ["Homo sapiens", "Mus musculus", "Homo sapiens"]
    tissues = ["PBMC", "Brain", "Tumor"]
    sample_counts = [6, 5, 8]

    experiments = []
    all_samples: dict[int, list[Sample]] = {}

    for i, cfg in enumerate(exp_configs):
        exp = Experiment(
            organization_id=org_id,
            name=cfg["name"],
            hypothesis=cfg["hypothesis"],
            description=cfg["description"],
            status=cfg["status"],
            owner_user_id=cfg["owner"].id,
            start_date=(NOW - timedelta(days=cfg["days_ago"])).date(),
        )
        session.add(exp)
        await session.flush()
        experiments.append(exp)

        # Samples
        samples = []
        treatments = [
            ["Control", "Drug_A_10uM", "Drug_A_50uM", "Drug_B_10uM", "Drug_B_50uM", "Combo"],
            ["P0_Rep1", "P0_Rep2", "P7_Rep1", "P7_Rep2", "P14_Rep1"],
            ["GBM_01", "GBM_02", "NSCLC_01", "NSCLC_02", "CRC_01", "CRC_02", "Healthy_01", "Healthy_02"],
        ]
        for j in range(sample_counts[i]):
            s = Sample(
                experiment_id=exp.id,
                sample_id_external=f"S{i+1:02d}-{j+1:03d}",
                organism=organisms[i],
                tissue_type=tissues[i],
                treatment_condition=treatments[i][j] if j < len(treatments[i]) else None,
                molecule_type="total RNA",
                library_prep_method="10x Chromium 3' v3.1",
                library_layout="paired",
                chemistry_version="v3.1",
                status=cfg["status"],
                qc_status="pass" if random.random() > 0.15 else "warning",
                cell_count=random.randint(4000, 12000),
            )
            session.add(s)
            samples.append(s)
        await session.flush()
        all_samples[exp.id] = samples

        # Batches — split samples into 2 batches
        instruments = [
            ("Illumina NovaSeq 6000", "230915_A00123_0456_BHKWVTDRX3"),
            ("Illumina NextSeq 2000", "231001_VH00234_0078_AACFHGTM5"),
        ]
        mid = len(samples) // 2
        for b_idx, batch_samples in enumerate([samples[:mid], samples[mid:]]):
            if not batch_samples:
                continue
            model, run_id = instruments[b_idx % 2]
            b = Batch(
                experiment_id=exp.id,
                name=f"Batch-{i+1}{chr(65+b_idx)}",
                instrument_model=model,
                instrument_platform=_derive_instrument_platform(model),
                quality_score_encoding="Phred+33",
                sequencer_run_id=run_id,
                prep_date=(NOW - timedelta(days=cfg["days_ago"] - 5 + b_idx)).date(),
            )
            session.add(b)
            await session.flush()
            for s in batch_samples:
                s.batch_id = b.id
            await session.flush()

    total_samples = sum(len(v) for v in all_samples.values())
    print(f"Created {len(experiments)} experiments with {total_samples} samples.")
    return experiments, all_samples


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline Runs & Reviews
# ═══════════════════════════════════════════════════════════════════════════
async def create_pipeline_runs(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
    org_id: int,
    comp_bio: User,
    admin: User,
) -> list[PipelineRun]:
    run_configs = [
        {"ref": "GRCh38", "aligner": "STARsolo", "hours_ago": 168, "status": "completed"},
        {"ref": "GRCh38", "aligner": "STARsolo", "hours_ago": 120, "status": "completed"},
        {"ref": "GRCm39", "aligner": "STARsolo", "hours_ago": 72, "status": "completed"},
        {"ref": "GRCm39", "aligner": "CellRanger", "hours_ago": 24, "status": "completed"},
        {"ref": "GRCh38", "aligner": "STARsolo", "hours_ago": 96, "status": "completed"},
        {"ref": "GRCh38", "aligner": "Salmon/Alevin", "hours_ago": 48, "status": "completed"},
    ]

    runs = []
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
                submitted_by_user_id=comp_bio.id,
                pipeline_name="nf-core/scrnaseq",
                pipeline_version="2.7.1",
                parameters_json={"genome": cfg["ref"], "aligner": cfg["aligner"].lower()},
                reference_genome=cfg["ref"],
                alignment_algorithm=cfg["aligner"],
                status=cfg["status"],
                work_dir=f"/data/working/nextflow/poc-run-{run_idx+1}",
                slurm_job_id=f"{100000 + run_idx}",
                cost_estimate=Decimal(str(round(random.uniform(2.0, 18.0), 2))),
                started_at=completed_at - timedelta(hours=random.randint(3, 8)),
                completed_at=completed_at,
            )
            session.add(run)
            await session.flush()
            for s in samples[exp.id]:
                session.add(PipelineRunSample(pipeline_run_id=run.id, sample_id=s.id))
            await session.flush()
            runs.append(run)
            run_idx += 1

    # Reviews on runs 0, 1, 2, 5
    review_configs = [
        {"run_idx": 0, "verdict": "approved",
         "notes": "All QC metrics look excellent. Median genes/cell >3000, low doublet rate."},
        {"run_idx": 1, "verdict": "approved_with_caveats",
         "notes": "Overall good quality. Sample S01-003 has elevated mitochondrial reads (12%)."},
        {"run_idx": 2, "verdict": "rejected",
         "notes": "Low cell recovery across most samples. Median UMI/cell below 500. Recommend re-sequencing."},
        {"run_idx": 5, "verdict": "revision_requested",
         "notes": "Alignment rates good but saturation low (45%). Consider additional sequencing."},
    ]
    for cfg in review_configs:
        run = runs[cfg["run_idx"]]
        review = PipelineRunReview(
            pipeline_run_id=run.id,
            reviewer_user_id=admin.id,
            verdict=cfg["verdict"],
            notes=cfg["notes"],
            reviewed_at=run.completed_at + timedelta(hours=12),
        )
        session.add(review)
    await session.flush()

    print(f"Created {len(runs)} pipeline runs with 4 reviews.")
    return runs


# ═══════════════════════════════════════════════════════════════════════════
# Reference Datasets
# ═══════════════════════════════════════════════════════════════════════════
async def create_reference_datasets(
    session: AsyncSession, org_id: int, admin: User
) -> list[ReferenceDataset]:
    configs = [
        {
            "name": f"{DEMO_PREFIX}: GRCh38 GENCODE", "category": "genome",
            "scope": "public", "version": "v43",
            "source_url": "https://www.gencodegenes.org/human/release_43.html",
            "gcs_prefix": "gs://bioaf-references/GRCh38/gencode_v43/",
            "total_size_bytes": 3_200_000_000, "file_count": 4, "status": "active",
            "files": [
                ("GRCh38.primary_assembly.genome.fa", "fasta", 3_000_000_000),
                ("GRCh38.primary_assembly.genome.fa.fai", "fai", 500_000),
                ("gencode.v43.annotation.gtf", "gtf", 180_000_000),
                ("gencode.v43.annotation.gff3", "gff3", 200_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: GRCh38 GENCODE", "category": "genome",
            "scope": "public", "version": "v44",
            "source_url": "https://www.gencodegenes.org/human/release_44.html",
            "gcs_prefix": "gs://bioaf-references/GRCh38/gencode_v44/",
            "total_size_bytes": 3_250_000_000, "file_count": 4, "status": "active",
            "files": [
                ("GRCh38.primary_assembly.genome.fa", "fasta", 3_000_000_000),
                ("GRCh38.primary_assembly.genome.fa.fai", "fai", 500_000),
                ("gencode.v44.annotation.gtf", "gtf", 185_000_000),
                ("gencode.v44.annotation.gff3", "gff3", 205_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: GRCm39 GENCODE", "category": "genome",
            "scope": "public", "version": "M33",
            "gcs_prefix": "gs://bioaf-references/GRCm39/gencode_M33/",
            "total_size_bytes": 2_800_000_000, "file_count": 3, "status": "active",
            "files": [
                ("GRCm39.primary_assembly.genome.fa", "fasta", 2_700_000_000),
                ("GRCm39.primary_assembly.genome.fa.fai", "fai", 400_000),
                ("gencode.vM33.annotation.gtf", "gtf", 120_000_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: STARsolo GRCh38 Index", "category": "index",
            "scope": "internal", "version": "2.7.11a-v43",
            "gcs_prefix": "gs://bioaf-references/indices/star/GRCh38_v43/",
            "total_size_bytes": 32_000_000_000, "file_count": 8, "status": "active",
            "files": [
                ("Genome", "star_index", 3_200_000_000),
                ("SA", "star_index", 24_000_000_000),
                ("SAindex", "star_index", 1_500_000_000),
                ("chrName.txt", "txt", 1_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: Custom Markers", "category": "markers",
            "scope": "internal", "version": "v2",
            "gcs_prefix": "gs://bioaf-references/custom/markers_v2/",
            "total_size_bytes": 500_000, "file_count": 2, "status": "deprecated",
            "deprecation_note": "Superseded by v3 with updated PBMC markers.",
            "files": [
                ("cell_markers_v2.csv", "csv", 250_000),
                ("marker_metadata_v2.json", "json", 50_000),
            ],
        },
        {
            "name": f"{DEMO_PREFIX}: Custom Markers", "category": "markers",
            "scope": "internal", "version": "v3",
            "gcs_prefix": "gs://bioaf-references/custom/markers_v3/",
            "total_size_bytes": 600_000, "file_count": 2, "status": "active",
            "files": [
                ("cell_markers_v3.csv", "csv", 300_000),
                ("marker_metadata_v3.json", "json", 60_000),
            ],
        },
    ]

    refs = []
    for cfg in configs:
        files_data = cfg.pop("files")
        ref = ReferenceDataset(
            organization_id=org_id,
            uploaded_by_user_id=admin.id,
            name=cfg["name"],
            category=cfg["category"],
            scope=cfg["scope"],
            version=cfg["version"],
            source_url=cfg.get("source_url"),
            gcs_prefix=cfg["gcs_prefix"],
            total_size_bytes=cfg.get("total_size_bytes"),
            file_count=cfg.get("file_count"),
            status=cfg["status"],
            deprecation_note=cfg.get("deprecation_note"),
        )
        session.add(ref)
        await session.flush()
        for fname, ftype, fsize in files_data:
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

    # markers v2 superseded by v3
    refs[4].superseded_by_id = refs[5].id
    await session.flush()

    print(f"Created {len(refs)} reference datasets.")
    return refs


# ═══════════════════════════════════════════════════════════════════════════
# GEO Files (for export demo)
# ═══════════════════════════════════════════════════════════════════════════
async def create_geo_files(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
    org_id: int,
) -> None:
    count = 0
    for exp in experiments[:2]:
        for s in samples[exp.id]:
            ext_id = s.sample_id_external
            for read in ["R1", "R2"]:
                fname = f"{ext_id}_{read}.fastq.gz"
                f = File(
                    organization_id=org_id,
                    gcs_uri=f"gs://bioaf-data/experiments/{exp.id}/fastq/{fname}",
                    filename=fname,
                    size_bytes=random.randint(2_000_000_000, 5_000_000_000),
                    md5_checksum=fake_md5(fname),
                    file_type="fastq.gz",
                )
                session.add(f)
                count += 1
            matrix = f"{ext_id}_filtered_feature_bc_matrix.h5"
            f = File(
                organization_id=org_id,
                gcs_uri=f"gs://bioaf-data/experiments/{exp.id}/processed/{matrix}",
                filename=matrix,
                size_bytes=random.randint(50_000_000, 200_000_000),
                md5_checksum=fake_md5(matrix),
                file_type="h5",
            )
            session.add(f)
            count += 1
    await session.flush()
    print(f"Created {count} file records for GEO export.")


# ═══════════════════════════════════════════════════════════════════════════
# Cross-experiment Project
# ═══════════════════════════════════════════════════════════════════════════
async def create_project(
    session: AsyncSession,
    experiments: list[Experiment],
    samples: dict[int, list[Sample]],
    org_id: int,
    comp_bio: User,
) -> Project:
    project = Project(
        organization_id=org_id,
        name=f"{DEMO_PREFIX}: GBM vs. Healthy Integration Atlas",
        description="Cross-experiment analysis comparing tumor samples with healthy controls",
        hypothesis="Tumor microenvironment differs significantly from healthy controls in immune cell composition",
        status="active",
        owner_user_id=comp_bio.id,
        created_by_user_id=comp_bio.id,
    )
    session.add(project)
    await session.flush()

    count = 0
    for exp in experiments[:2]:
        for s in samples[exp.id][:4]:
            ps = ProjectSample(
                project_id=project.id,
                sample_id=s.id,
                added_by_user_id=comp_bio.id,
                notes=f"Added from experiment {exp.id}",
            )
            session.add(ps)
            count += 1
    await session.flush()

    print(f"Created project '{project.name}' with {count} samples.")
    return project


# ═══════════════════════════════════════════════════════════════════════════
# Analysis Snapshots
# ═══════════════════════════════════════════════════════════════════════════
async def create_snapshots(
    session: AsyncSession,
    experiments: list[Experiment],
    project: Project,
    org_id: int,
    comp_bio: User,
    notebook_sessions: list[NotebookSession],
) -> None:
    exp_snapshots = [
        # Experiment 1: anndata pipeline
        [
            {"label": "Post-QC: 9200 cells, 22000 genes", "object_type": "anndata",
             "cell_count": 9200, "gene_count": 22000,
             "parameters_json": {}, "embeddings_json": {}, "clusterings_json": {},
             "layers_json": ["counts"]},
            {"label": "Filtered: 8432 cells, 18291 genes", "object_type": "anndata",
             "cell_count": 8432, "gene_count": 18291,
             "parameters_json": {"filter": {"params": {"min_genes": 200, "max_pct_mt": 20}}},
             "embeddings_json": {}, "clusterings_json": {},
             "layers_json": ["counts", "log1p"]},
            {"label": "leiden_0.5_no_correction", "object_type": "anndata",
             "cell_count": 8432, "gene_count": 18291,
             "parameters_json": {
                 "neighbors": {"params": {"n_neighbors": 15, "method": "umap"}},
                 "leiden": {"params": {"resolution": 0.5}},
             },
             "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
             "clusterings_json": {"leiden": {"n_clusters": 9, "distribution": {
                 "0": 1200, "1": 980, "2": 850, "3": 720, "4": 650,
                 "5": 580, "6": 510, "7": 480, "8": 462}}},
             "layers_json": ["counts", "log1p"],
             "starred": True, "notes": "Clean separation of major cell types"},
            {"label": "DE complete: 2847 significant genes", "object_type": "anndata",
             "cell_count": 8432, "gene_count": 18291,
             "parameters_json": {
                 "neighbors": {"params": {"n_neighbors": 15}},
                 "leiden": {"params": {"resolution": 0.5}},
                 "rank_genes_groups": {"params": {"method": "wilcoxon", "groupby": "leiden"}},
             },
             "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
             "clusterings_json": {"leiden": {"n_clusters": 9, "distribution": {
                 "0": 1200, "1": 980, "2": 850, "3": 720, "4": 650,
                 "5": 580, "6": 510, "7": 480, "8": 462}}},
             "layers_json": ["counts", "log1p"]},
        ],
        # Experiment 2: anndata with harmony
        [
            {"label": "Post-QC: 6100 cells", "object_type": "anndata",
             "cell_count": 6100, "gene_count": 19500,
             "parameters_json": {}, "embeddings_json": {}, "clusterings_json": {},
             "layers_json": ["counts"]},
            {"label": "leiden_0.5_harmony", "object_type": "anndata",
             "cell_count": 5980, "gene_count": 17200,
             "parameters_json": {
                 "neighbors": {"params": {"n_neighbors": 20}},
                 "leiden": {"params": {"resolution": 0.5}},
                 "harmony": {"params": {"theta": 2.0, "sigma": 0.1}},
             },
             "embeddings_json": {"X_pca": {"n_components": 50}, "X_harmony": {"n_components": 50}, "X_umap": {"n_components": 2}},
             "clusterings_json": {"leiden": {"n_clusters": 7, "distribution": {
                 "0": 1100, "1": 950, "2": 900, "3": 800, "4": 750, "5": 530, "6": 450}}},
             "layers_json": ["counts", "log1p"],
             "starred": True, "notes": "Harmony batch correction resolves batch effect cleanly"},
        ],
        # Experiment 3: seurat
        [
            {"label": "Post-QC: 8102 cells", "object_type": "seurat",
             "cell_count": 8102, "gene_count": 20100,
             "parameters_json": {}, "embeddings_json": {}, "clusterings_json": {},
             "command_log_json": [{"name": "CreateSeuratObject", "params": {"min.cells": 3, "min.features": 200}}]},
            {"label": "sct_leiden_0.5", "object_type": "seurat",
             "cell_count": 8102, "gene_count": 20100,
             "parameters_json": {
                 "FindNeighbors": {"params": {"dims": "1:30"}},
                 "FindClusters": {"params": {"resolution": 0.5}},
             },
             "embeddings_json": {"pca": {"n_components": 50}, "umap": {"n_components": 2}},
             "clusterings_json": {"seurat_clusters": {"n_clusters": 8, "distribution": {
                 "0": 1400, "1": 1200, "2": 1100, "3": 900, "4": 850, "5": 800, "6": 500, "7": 352}}},
             "command_log_json": [
                 {"name": "CreateSeuratObject", "params": {"min.cells": 3, "min.features": 200}},
                 {"name": "NormalizeData", "params": {"assay": "RNA"}},
                 {"name": "FindVariableFeatures", "params": {"assay": "RNA", "nfeatures": 2000}},
                 {"name": "ScaleData", "params": {"assay": "RNA"}},
                 {"name": "RunPCA", "params": {"assay": "RNA", "npcs": 50}},
                 {"name": "FindNeighbors", "params": {"reduction": "pca", "dims": "1:30"}},
                 {"name": "FindClusters", "params": {"resolution": 0.5}},
                 {"name": "RunUMAP", "params": {"reduction": "pca", "dims": "1:30"}},
             ],
             "starred": True, "notes": "Standard SCTransform workflow"},
        ],
    ]

    # Project-level snapshots
    project_snaps = [
        {"label": "Integrated: no batch correction", "object_type": "anndata",
         "cell_count": 14412, "gene_count": 16800,
         "parameters_json": {"neighbors": {"params": {"n_neighbors": 15}}, "leiden": {"params": {"resolution": 0.5}}},
         "embeddings_json": {"X_pca": {"n_components": 50}, "X_umap": {"n_components": 2}},
         "clusterings_json": {"leiden": {"n_clusters": 12, "distribution": {str(i): max(200, 1800 - i * 140) for i in range(12)}}},
         "layers_json": ["counts", "log1p"], "notes": "Batch effect visible in UMAP"},
        {"label": "Integrated: scVI batch corrected", "object_type": "anndata",
         "cell_count": 14410, "gene_count": 16800,
         "parameters_json": {"neighbors": {"params": {"n_neighbors": 15}}, "leiden": {"params": {"resolution": 0.5}},
                             "scvi": {"params": {"n_latent": 30, "n_layers": 2, "batch_key": "experiment"}}},
         "embeddings_json": {"X_pca": {"n_components": 50}, "X_scVI": {"n_components": 30}, "X_umap": {"n_components": 2}},
         "clusterings_json": {"leiden": {"n_clusters": 10, "distribution": {str(i): max(300, 2000 - i * 180) for i in range(10)}}},
         "layers_json": ["counts", "log1p"], "notes": "Batch effect resolved, clean integration"},
    ]

    count = 0
    # Link first few snapshots to notebook sessions if available
    ns_idx = 0
    for i, snap_list in enumerate(exp_snapshots):
        if i >= len(experiments):
            break
        for snap_data in snap_list:
            starred = snap_data.pop("starred", False)
            notes = snap_data.pop("notes", None)
            ns_id = None
            if ns_idx < len(notebook_sessions):
                ns_id = notebook_sessions[ns_idx].id
            snapshot = AnalysisSnapshot(
                organization_id=org_id,
                experiment_id=experiments[i].id,
                user_id=comp_bio.id,
                starred=starred,
                notes=notes,
                notebook_session_id=ns_id,
                **snap_data,
            )
            session.add(snapshot)
            count += 1
        ns_idx += 1

    for snap_data in project_snaps:
        notes = snap_data.pop("notes", None)
        snapshot = AnalysisSnapshot(
            organization_id=org_id,
            project_id=project.id,
            user_id=comp_bio.id,
            notes=notes,
            **snap_data,
        )
        session.add(snapshot)
        count += 1

    await session.flush()
    print(f"Created {count} analysis snapshots.")


# ═══════════════════════════════════════════════════════════════════════════
# Template Notebooks
# ═══════════════════════════════════════════════════════════════════════════
async def create_template_notebooks(
    session: AsyncSession, org_id: int
) -> list[TemplateNotebook]:
    configs = [
        {
            "name": "Standard scRNA-seq QC",
            "description": "Quality control workflow: doublet detection, ambient RNA removal, cell/gene filtering, QC metric visualization.",
            "category": "qc",
            "notebook_path": "/templates/scanpy_qc.ipynb",
            "parameters_json": {"min_genes": 200, "max_pct_mt": 20, "min_cells": 3},
            "compatible_with": "anndata",
            "sort_order": 1,
        },
        {
            "name": "Differential Expression Analysis",
            "description": "Wilcoxon rank-sum test across clusters. Generates volcano plots, heatmaps, and marker gene tables.",
            "category": "analysis",
            "notebook_path": "/templates/de_analysis.ipynb",
            "parameters_json": {"method": "wilcoxon", "groupby": "leiden", "n_genes": 100},
            "compatible_with": "anndata,seurat",
            "sort_order": 2,
        },
        {
            "name": "Integration & Batch Correction",
            "description": "Multi-sample integration using Harmony, scVI, or BBKNN. Includes batch effect assessment before/after.",
            "category": "integration",
            "notebook_path": "/templates/integration.ipynb",
            "parameters_json": {"methods": ["harmony", "scvi"], "batch_key": "batch"},
            "compatible_with": "anndata",
            "sort_order": 3,
        },
        {
            "name": "Cell Type Annotation",
            "description": "Automated cell type annotation using marker gene databases. Supports celltypist and manual marker scoring.",
            "category": "annotation",
            "notebook_path": "/templates/cell_annotation.ipynb",
            "parameters_json": {"reference": "celltypist_immune", "min_score": 0.5},
            "compatible_with": "anndata,seurat",
            "sort_order": 4,
        },
    ]

    templates = []
    for cfg in configs:
        t = TemplateNotebook(organization_id=org_id, is_builtin=True, **cfg)
        session.add(t)
        templates.append(t)
    await session.flush()

    print(f"Created {len(templates)} template notebooks.")
    return templates


# ═══════════════════════════════════════════════════════════════════════════
# Notebook Sessions
# ═══════════════════════════════════════════════════════════════════════════
async def create_notebook_sessions(
    session: AsyncSession,
    experiments: list[Experiment],
    project: Project,
    org_id: int,
    comp_bio: User,
    admin: User,
) -> list[NotebookSession]:
    configs = [
        # Active sessions
        {"user": comp_bio, "type": "jupyter", "exp": experiments[0], "proj": None,
         "profile": "medium", "cpu": 4, "mem": 16, "status": "running",
         "slurm": "200001", "hours_ago_start": 2, "idle": None},
        {"user": comp_bio, "type": "jupyter", "exp": None, "proj": project,
         "profile": "large", "cpu": 8, "mem": 32, "status": "running",
         "slurm": "200002", "hours_ago_start": 0.5, "idle": None},
        {"user": admin, "type": "jupyter", "exp": experiments[2], "proj": None,
         "profile": "small", "cpu": 2, "mem": 8, "status": "idle",
         "slurm": "200003", "hours_ago_start": 5, "idle": 1},
        # Historical sessions
        {"user": comp_bio, "type": "jupyter", "exp": experiments[0], "proj": None,
         "profile": "medium", "cpu": 4, "mem": 16, "status": "stopped",
         "slurm": "199990", "hours_ago_start": 72, "stopped_hours_ago": 68},
        {"user": comp_bio, "type": "jupyter", "exp": experiments[1], "proj": None,
         "profile": "large", "cpu": 8, "mem": 32, "status": "stopped",
         "slurm": "199991", "hours_ago_start": 48, "stopped_hours_ago": 44},
        {"user": admin, "type": "jupyter", "exp": experiments[0], "proj": None,
         "profile": "small", "cpu": 2, "mem": 8, "status": "stopped",
         "slurm": "199992", "hours_ago_start": 120, "stopped_hours_ago": 116},
        {"user": comp_bio, "type": "jupyter", "exp": experiments[2], "proj": None,
         "profile": "medium", "cpu": 4, "mem": 16, "status": "stopped",
         "slurm": "199993", "hours_ago_start": 168, "stopped_hours_ago": 160},
        {"user": comp_bio, "type": "jupyter", "exp": None, "proj": project,
         "profile": "large", "cpu": 8, "mem": 32, "status": "stopped",
         "slurm": "199994", "hours_ago_start": 200, "stopped_hours_ago": 192},
    ]

    sessions = []
    for cfg in configs:
        started_at = NOW - timedelta(hours=cfg["hours_ago_start"])
        ns = NotebookSession(
            user_id=cfg["user"].id,
            organization_id=org_id,
            session_type=cfg["type"],
            experiment_id=cfg["exp"].id if cfg["exp"] else None,
            project_id=cfg["proj"].id if cfg["proj"] else None,
            slurm_job_id=cfg["slurm"],
            resource_profile=cfg["profile"],
            cpu_cores=cfg["cpu"],
            memory_gb=cfg["mem"],
            status=cfg["status"],
            started_at=started_at,
            idle_since=(NOW - timedelta(hours=cfg["idle"])) if cfg.get("idle") else None,
            stopped_at=(NOW - timedelta(hours=cfg["stopped_hours_ago"])) if cfg.get("stopped_hours_ago") else None,
            proxy_url=f"http://jupyter-{cfg['slurm']}.internal:8888" if cfg["status"] in ("running", "idle") else None,
        )
        session.add(ns)
        sessions.append(ns)
    await session.flush()

    print(f"Created {len(sessions)} notebook sessions.")
    return sessions


# ═══════════════════════════════════════════════════════════════════════════
# SLURM Jobs
# ═══════════════════════════════════════════════════════════════════════════
async def create_slurm_jobs(
    session: AsyncSession,
    experiments: list[Experiment],
    org_id: int,
    comp_bio: User,
    admin: User,
) -> None:
    job_configs = [
        # Completed jobs (pipeline runs)
        {"user": comp_bio, "slurm_id": "100000", "name": "nf-scrnaseq-pbmc-run1",
         "partition": "compute", "status": "completed", "exp": experiments[0],
         "cpu_req": 16, "mem_req": 64, "cpu_used": 14, "mem_used": 52, "exit_code": 0,
         "cost": "8.50", "hours_ago_submit": 180, "hours_ago_start": 179, "hours_ago_end": 173},
        {"user": comp_bio, "slurm_id": "100001", "name": "nf-scrnaseq-pbmc-run2",
         "partition": "compute", "status": "completed", "exp": experiments[0],
         "cpu_req": 16, "mem_req": 64, "cpu_used": 15, "mem_used": 58, "exit_code": 0,
         "cost": "9.20", "hours_ago_submit": 130, "hours_ago_start": 128, "hours_ago_end": 122},
        {"user": comp_bio, "slurm_id": "100002", "name": "nf-scrnaseq-brain-run1",
         "partition": "compute", "status": "completed", "exp": experiments[1],
         "cpu_req": 32, "mem_req": 128, "cpu_used": 28, "mem_used": 96, "exit_code": 0,
         "cost": "15.80", "hours_ago_submit": 80, "hours_ago_start": 78, "hours_ago_end": 70},
        {"user": comp_bio, "slurm_id": "100003", "name": "nf-scrnaseq-brain-run2",
         "partition": "compute", "status": "completed", "exp": experiments[1],
         "cpu_req": 16, "mem_req": 64, "cpu_used": 16, "mem_used": 60, "exit_code": 0,
         "cost": "7.40", "hours_ago_submit": 32, "hours_ago_start": 30, "hours_ago_end": 24},
        {"user": admin, "slurm_id": "100004", "name": "nf-scrnaseq-tumor-run1",
         "partition": "compute", "status": "completed", "exp": experiments[2],
         "cpu_req": 16, "mem_req": 64, "cpu_used": 14, "mem_used": 48, "exit_code": 0,
         "cost": "6.30", "hours_ago_submit": 108, "hours_ago_start": 106, "hours_ago_end": 98},
        {"user": admin, "slurm_id": "100005", "name": "nf-scrnaseq-tumor-run2",
         "partition": "compute", "status": "completed", "exp": experiments[2],
         "cpu_req": 16, "mem_req": 64, "cpu_used": 15, "mem_used": 55, "exit_code": 0,
         "cost": "11.10", "hours_ago_submit": 56, "hours_ago_start": 54, "hours_ago_end": 48},
        # Completed notebook sessions
        {"user": comp_bio, "slurm_id": "199990", "name": "jupyter-pbmc-qc",
         "partition": "interactive", "status": "completed", "exp": experiments[0],
         "cpu_req": 4, "mem_req": 16, "cpu_used": 3, "mem_used": 12, "exit_code": 0,
         "cost": "1.20", "hours_ago_submit": 72, "hours_ago_start": 72, "hours_ago_end": 68},
        {"user": comp_bio, "slurm_id": "199991", "name": "jupyter-brain-analysis",
         "partition": "interactive", "status": "completed", "exp": experiments[1],
         "cpu_req": 8, "mem_req": 32, "cpu_used": 6, "mem_used": 24, "exit_code": 0,
         "cost": "2.80", "hours_ago_submit": 48, "hours_ago_start": 48, "hours_ago_end": 44},
        # A failed job
        {"user": comp_bio, "slurm_id": "199995", "name": "nf-scrnaseq-failed-oom",
         "partition": "compute", "status": "failed", "exp": experiments[1],
         "cpu_req": 8, "mem_req": 32, "cpu_used": 8, "mem_used": 32, "exit_code": 137,
         "cost": "0.90", "hours_ago_submit": 96, "hours_ago_start": 95, "hours_ago_end": 94},
        # Currently running jobs (notebook sessions)
        {"user": comp_bio, "slurm_id": "200001", "name": "jupyter-pbmc-de",
         "partition": "interactive", "status": "running", "exp": experiments[0],
         "cpu_req": 4, "mem_req": 16, "cpu_used": None, "mem_used": None, "exit_code": None,
         "cost": None, "hours_ago_submit": 2, "hours_ago_start": 2, "hours_ago_end": None},
        {"user": comp_bio, "slurm_id": "200002", "name": "jupyter-integration",
         "partition": "interactive", "status": "running", "exp": None,
         "cpu_req": 8, "mem_req": 32, "cpu_used": None, "mem_used": None, "exit_code": None,
         "cost": None, "hours_ago_submit": 0.5, "hours_ago_start": 0.5, "hours_ago_end": None},
        {"user": admin, "slurm_id": "200003", "name": "jupyter-tumor-review",
         "partition": "interactive", "status": "running", "exp": experiments[2],
         "cpu_req": 2, "mem_req": 8, "cpu_used": None, "mem_used": None, "exit_code": None,
         "cost": None, "hours_ago_submit": 5, "hours_ago_start": 5, "hours_ago_end": None},
        # Pending / queued jobs
        {"user": comp_bio, "slurm_id": "200010", "name": "nf-scrnaseq-rerun-brain",
         "partition": "compute", "status": "pending", "exp": experiments[1],
         "cpu_req": 32, "mem_req": 128, "cpu_used": None, "mem_used": None, "exit_code": None,
         "cost": None, "hours_ago_submit": 0.25, "hours_ago_start": None, "hours_ago_end": None},
        {"user": comp_bio, "slurm_id": "200011", "name": "cellranger-count-pbmc",
         "partition": "compute", "status": "pending", "exp": experiments[0],
         "cpu_req": 16, "mem_req": 64, "cpu_used": None, "mem_used": None, "exit_code": None,
         "cost": None, "hours_ago_submit": 0.1, "hours_ago_start": None, "hours_ago_end": None},
        {"user": admin, "slurm_id": "200012", "name": "jupyter-admin-debug",
         "partition": "interactive", "status": "pending", "exp": None,
         "cpu_req": 2, "mem_req": 8, "cpu_used": None, "mem_used": None, "exit_code": None,
         "cost": None, "hours_ago_submit": 0.05, "hours_ago_start": None, "hours_ago_end": None},
    ]

    for cfg in job_configs:
        j = SlurmJob(
            organization_id=org_id,
            user_id=cfg["user"].id,
            slurm_job_id=cfg["slurm_id"],
            job_name=cfg["name"],
            partition=cfg["partition"],
            status=cfg["status"],
            experiment_id=cfg["exp"].id if cfg["exp"] else None,
            cpu_requested=cfg["cpu_req"],
            memory_gb_requested=cfg["mem_req"],
            cpu_used=cfg["cpu_used"],
            memory_gb_used=cfg["mem_used"],
            exit_code=cfg["exit_code"],
            stdout_path=f"/data/logs/{cfg['slurm_id']}.out" if cfg["status"] != "pending" else None,
            stderr_path=f"/data/logs/{cfg['slurm_id']}.err" if cfg["status"] != "pending" else None,
            cost_estimate=Decimal(cfg["cost"]) if cfg["cost"] else None,
            submitted_at=NOW - timedelta(hours=cfg["hours_ago_submit"]),
            started_at=(NOW - timedelta(hours=cfg["hours_ago_start"])) if cfg["hours_ago_start"] is not None else None,
            completed_at=(NOW - timedelta(hours=cfg["hours_ago_end"])) if cfg["hours_ago_end"] is not None else None,
        )
        session.add(j)
    await session.flush()

    print(f"Created {len(job_configs)} SLURM jobs.")


# ═══════════════════════════════════════════════════════════════════════════
# Activity Feed
# ═══════════════════════════════════════════════════════════════════════════
async def create_activity_feed(
    session: AsyncSession,
    experiments: list[Experiment],
    project: Project,
    org_id: int,
    users: dict[str, User],
) -> None:
    entries = [
        {"user": "admin", "event_type": "experiment.created", "entity_type": "experiment",
         "entity_id": experiments[2].id, "hours_ago": 336,
         "summary": f"{DEMO_PREFIX}: Maria created experiment 'Human Tumor Microenvironment'"},
        {"user": "comp_bio", "event_type": "experiment.created", "entity_type": "experiment",
         "entity_id": experiments[0].id, "hours_ago": 312,
         "summary": f"{DEMO_PREFIX}: Sarah created experiment 'Human PBMC scRNA-seq'"},
        {"user": "comp_bio", "event_type": "experiment.created", "entity_type": "experiment",
         "entity_id": experiments[1].id, "hours_ago": 288,
         "summary": f"{DEMO_PREFIX}: Sarah created experiment 'Mouse Brain Atlas'"},
        {"user": "comp_bio", "event_type": "pipeline_run.completed", "entity_type": "pipeline_run",
         "entity_id": None, "hours_ago": 173,
         "summary": f"{DEMO_PREFIX}: Pipeline nf-core/scrnaseq completed for PBMC experiment"},
        {"user": "admin", "event_type": "review.submitted", "entity_type": "pipeline_run_review",
         "entity_id": None, "hours_ago": 161,
         "summary": f"{DEMO_PREFIX}: Maria approved pipeline run for PBMC experiment"},
        {"user": "comp_bio", "event_type": "pipeline_run.completed", "entity_type": "pipeline_run",
         "entity_id": None, "hours_ago": 70,
         "summary": f"{DEMO_PREFIX}: Pipeline nf-core/scrnaseq completed for Brain Atlas"},
        {"user": "admin", "event_type": "review.submitted", "entity_type": "pipeline_run_review",
         "entity_id": None, "hours_ago": 58,
         "summary": f"{DEMO_PREFIX}: Maria rejected pipeline run for Brain Atlas — low cell recovery"},
        {"user": "comp_bio", "event_type": "project.created", "entity_type": "project",
         "entity_id": project.id, "hours_ago": 50,
         "summary": f"{DEMO_PREFIX}: Sarah created project 'GBM vs. Healthy Integration Atlas'"},
        {"user": "comp_bio", "event_type": "snapshot.created", "entity_type": "analysis_snapshot",
         "entity_id": None, "hours_ago": 40,
         "summary": f"{DEMO_PREFIX}: Sarah saved analysis snapshot 'leiden_0.5_no_correction' for PBMC experiment"},
        {"user": "comp_bio", "event_type": "notebook.launched", "entity_type": "notebook_session",
         "entity_id": None, "hours_ago": 2,
         "summary": f"{DEMO_PREFIX}: Sarah launched Jupyter notebook for PBMC DE analysis"},
        {"user": "comp_bio", "event_type": "job.submitted", "entity_type": "slurm_job",
         "entity_id": None, "hours_ago": 0.25,
         "summary": f"{DEMO_PREFIX}: Sarah submitted pipeline rerun for Brain Atlas"},
        {"user": "admin", "event_type": "notebook.launched", "entity_type": "notebook_session",
         "entity_id": None, "hours_ago": 0.05,
         "summary": f"{DEMO_PREFIX}: Maria requested notebook session for admin debugging"},
    ]

    for e in entries:
        entry = ActivityFeedEntry(
            organization_id=org_id,
            user_id=users[e["user"]].id,
            event_type=e["event_type"],
            entity_type=e["entity_type"],
            entity_id=e["entity_id"],
            summary=e["summary"],
            metadata_json={},
        )
        # Manually set created_at via column_property isn't easy with server_default,
        # so we set it after flush. For now the ordering is fine.
        session.add(entry)
    await session.flush()

    print(f"Created {len(entries)} activity feed entries.")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
async def main() -> None:
    print("=" * 60)
    print("  bioAF POC Data Seeder")
    print("=" * 60)
    print()

    async with async_session_factory() as session:
        session: AsyncSession

        await cleanup(session)

        org_id, users = await create_org_and_users(session)
        admin = users["admin"]
        comp_bio = users["comp_bio"]

        experiments, samples = await create_experiments(
            session, org_id, admin, comp_bio
        )
        runs = await create_pipeline_runs(
            session, experiments, samples, org_id, comp_bio, admin
        )
        refs = await create_reference_datasets(session, org_id, admin)

        # Link some pipeline runs to references
        if len(runs) >= 2 and len(refs) >= 4:
            for run in runs[:2]:
                await session.execute(
                    pipeline_run_references.insert().values(
                        pipeline_run_id=run.id, reference_dataset_id=refs[1].id
                    )
                )
                await session.execute(
                    pipeline_run_references.insert().values(
                        pipeline_run_id=run.id, reference_dataset_id=refs[3].id
                    )
                )
            await session.flush()

        await create_geo_files(session, experiments, samples, org_id)

        project = await create_project(
            session, experiments, samples, org_id, comp_bio
        )

        notebook_sessions = await create_notebook_sessions(
            session, experiments, project, org_id, comp_bio, admin
        )

        await create_template_notebooks(session, org_id)

        await create_snapshots(
            session, experiments, project, org_id, comp_bio, notebook_sessions
        )

        await create_slurm_jobs(
            session, experiments, org_id, comp_bio, admin
        )

        await create_activity_feed(
            session, experiments, project, org_id, users
        )

        await session.commit()

    print()
    print("=" * 60)
    print("  Seed complete!")
    print("=" * 60)
    print()
    print("Demo accounts:")
    print(f"  Admin:    maria@bioaf-demo.org / {DEMO_PASSWORDS['maria@bioaf-demo.org']}")
    print(f"  Comp Bio: sarah@bioaf-demo.org / {DEMO_PASSWORDS['sarah@bioaf-demo.org']}")
    print(f"  Viewer:   alex@bioaf-demo.org  / {DEMO_PASSWORDS['alex@bioaf-demo.org']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
