"""
Generate Phase 10a mock data for cross-experiment projects.

Extends existing mock data with:
- 1 cross-experiment project: "GBM vs. Healthy Integration Atlas"
- Project samples from experiments 1 and 2
- 1 project-scoped pipeline run
- Pipeline run -> reference linkage for the project-scoped run

Usage:
  cd backend && python -m scripts.generate_phase10a_mock_data
  # or from project root:
  python scripts/generate_phase10a_mock_data.py
"""

import asyncio
import sys

sys.path.insert(0, "backend")

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.database import async_session_factory  # noqa: E402
from app.models.experiment import Experiment  # noqa: E402
from app.models.pipeline_run import PipelineRun  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.project_sample import ProjectSample  # noqa: E402
from app.models.reference_dataset import pipeline_run_references  # noqa: E402
from app.models.sample import Sample  # noqa: E402
from app.models.user import User  # noqa: E402


async def generate() -> None:
    async with async_session_factory() as session:
        session: AsyncSession

        # Clean up any existing phase 10a mock data
        existing = await session.execute(
            select(Project).where(Project.name == "GBM vs. Healthy Integration Atlas")
        )
        old_project = existing.scalar_one_or_none()
        if old_project:
            await session.execute(
                delete(ProjectSample).where(ProjectSample.project_id == old_project.id)
            )
            await session.execute(
                delete(PipelineRun).where(PipelineRun.project_id == old_project.id)
            )
            await session.delete(old_project)
            await session.flush()

        # Find comp_bio user (Sarah) or fallback to any user
        comp_bio_result = await session.execute(
            select(User).where(User.role == "comp_bio").limit(1)
        )
        comp_bio_user = comp_bio_result.scalar_one_or_none()
        if not comp_bio_user:
            user_result = await session.execute(select(User).limit(1))
            comp_bio_user = user_result.scalar_one()

        # Get first two experiments
        exp_result = await session.execute(
            select(Experiment).order_by(Experiment.id).limit(2)
        )
        experiments = list(exp_result.scalars().all())
        if len(experiments) < 2:
            print("Need at least 2 experiments. Run earlier phase mock data first.")
            return

        exp1, exp2 = experiments[0], experiments[1]

        # Get samples from each experiment (up to 4)
        s1_result = await session.execute(
            select(Sample).where(Sample.experiment_id == exp1.id).limit(4)
        )
        s2_result = await session.execute(
            select(Sample).where(Sample.experiment_id == exp2.id).limit(4)
        )
        samples_exp1 = list(s1_result.scalars().all())
        samples_exp2 = list(s2_result.scalars().all())

        if not samples_exp1 or not samples_exp2:
            print("Need samples in both experiments. Run earlier phase mock data first.")
            return

        # Create the project
        project = Project(
            organization_id=comp_bio_user.organization_id,
            name="GBM vs. Healthy Integration Atlas",
            description="Cross-experiment analysis comparing tumor samples with healthy controls",
            hypothesis="Tumor microenvironment differs significantly from healthy controls in immune cell composition",
            status="active",
            owner_user_id=comp_bio_user.id,
            created_by_user_id=comp_bio_user.id,
        )
        session.add(project)
        await session.flush()
        print(f"Created project: {project.name} (id={project.id})")

        # Add samples from both experiments
        all_samples = samples_exp1 + samples_exp2
        for sample in all_samples:
            ps = ProjectSample(
                project_id=project.id,
                sample_id=sample.id,
                added_by_user_id=comp_bio_user.id,
                notes=f"Added from experiment {sample.experiment_id}",
            )
            session.add(ps)
        await session.flush()
        print(f"Added {len(all_samples)} samples to project")

        # Create a project-scoped pipeline run
        run = PipelineRun(
            organization_id=comp_bio_user.organization_id,
            experiment_id=exp1.id,
            project_id=project.id,
            submitted_by_user_id=comp_bio_user.id,
            pipeline_name="nf-core/scrnaseq",
            pipeline_version="2.7.1",
            status="completed",
            parameters_json={
                "genome": "GRCh38",
                "protocol": "10XV3",
                "aligner": "star",
            },
        )
        session.add(run)
        await session.flush()
        print(f"Created project-scoped pipeline run (id={run.id})")

        # Link a reference dataset if one exists
        from app.models.reference_dataset import ReferenceDataset

        ref_result = await session.execute(select(ReferenceDataset).limit(1))
        ref = ref_result.scalar_one_or_none()
        if ref:
            await session.execute(
                pipeline_run_references.insert().values(
                    pipeline_run_id=run.id,
                    reference_dataset_id=ref.id,
                )
            )
            print(f"Linked reference dataset '{ref.name}' to project run")

        await session.commit()
        print("Phase 10a mock data generation complete!")


if __name__ == "__main__":
    asyncio.run(generate())
