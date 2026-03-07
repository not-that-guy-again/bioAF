from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis_snapshot import AnalysisSnapshot
from app.models.experiment import Experiment
from app.models.pipeline_run import PipelineRun
from app.models.project import Project
from app.models.project_sample import ProjectSample
from app.models.sample import Sample
from app.schemas.project import ProjectCreate, ProjectSamplesAdd, ProjectUpdate
from app.services.audit_service import log_action


class ProjectService:
    @staticmethod
    async def create_project(
        session: AsyncSession, org_id: int, user_id: int, data: ProjectCreate
    ) -> Project:
        # Validate sample_ids if provided
        if data.sample_ids:
            result = await session.execute(
                select(Sample.id).where(Sample.id.in_(data.sample_ids))
            )
            found_ids = {row[0] for row in result.all()}
            missing = set(data.sample_ids) - found_ids
            if missing:
                raise HTTPException(404, f"Samples not found: {sorted(missing)}")

        project = Project(
            organization_id=org_id,
            name=data.name,
            description=data.description,
            hypothesis=data.hypothesis,
            owner_user_id=user_id,
            created_by_user_id=user_id,
        )
        session.add(project)
        await session.flush()

        # Add initial samples if provided
        if data.sample_ids:
            for sid in data.sample_ids:
                ps = ProjectSample(
                    project_id=project.id,
                    sample_id=sid,
                    added_by_user_id=user_id,
                )
                session.add(ps)
            await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="project",
            entity_id=project.id,
            action="created",
            details={"name": data.name, "sample_ids": data.sample_ids},
        )
        return project

    @staticmethod
    async def update_project(
        session: AsyncSession, project_id: int, user_id: int, data: ProjectUpdate
    ) -> Project | None:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return None

        previous = {}
        updates = {}
        for field in ["name", "description", "hypothesis", "status"]:
            new_val = getattr(data, field, None)
            if new_val is not None:
                previous[field] = getattr(project, field)
                setattr(project, field, new_val)
                updates[field] = new_val

        if updates:
            await session.flush()
            await log_action(
                session,
                user_id=user_id,
                entity_type="project",
                entity_id=project.id,
                action="updated",
                details=updates,
                previous_value=previous,
            )
        return project

    @staticmethod
    async def list_projects(
        session: AsyncSession,
        org_id: int,
        status: str | None = None,
        owner_user_id: int | None = None,
        search: str | None = None,
    ) -> list[dict]:
        # Base query for projects
        stmt = (
            select(
                Project,
                func.count(func.distinct(ProjectSample.id)).label("sample_count"),
                func.count(func.distinct(Sample.experiment_id)).label("experiment_count"),
            )
            .outerjoin(ProjectSample, ProjectSample.project_id == Project.id)
            .outerjoin(Sample, Sample.id == ProjectSample.sample_id)
            .options(selectinload(Project.owner))
            .where(Project.organization_id == org_id)
            .group_by(Project.id)
            .order_by(Project.created_at.desc())
        )

        if status:
            stmt = stmt.where(Project.status == status)
        if owner_user_id:
            stmt = stmt.where(Project.owner_user_id == owner_user_id)
        if search:
            stmt = stmt.where(Project.name.ilike(f"%{search}%"))

        result = await session.execute(stmt)
        rows = result.all()

        # Get pipeline run and snapshot counts
        project_ids = [row[0].id for row in rows]
        run_counts = {}
        snap_counts = {}
        if project_ids:
            run_result = await session.execute(
                select(PipelineRun.project_id, func.count(PipelineRun.id))
                .where(PipelineRun.project_id.in_(project_ids))
                .group_by(PipelineRun.project_id)
            )
            run_counts = dict(run_result.all())

            snap_result = await session.execute(
                select(AnalysisSnapshot.project_id, func.count(AnalysisSnapshot.id))
                .where(AnalysisSnapshot.project_id.in_(project_ids))
                .group_by(AnalysisSnapshot.project_id)
            )
            snap_counts = dict(snap_result.all())

        projects = []
        for project, sample_count, experiment_count in rows:
            projects.append({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "hypothesis": project.hypothesis,
                "status": project.status,
                "owner_user_id": project.owner_user_id,
                "owner_name": project.owner.name if project.owner else None,
                "sample_count": sample_count,
                "experiment_count": experiment_count,
                "pipeline_run_count": run_counts.get(project.id, 0),
                "snapshot_count": snap_counts.get(project.id, 0),
                "created_at": project.created_at,
            })
        return projects

    @staticmethod
    async def get_project(session: AsyncSession, project_id: int, org_id: int) -> Project | None:
        result = await session.execute(
            select(Project)
            .options(selectinload(Project.owner))
            .where(Project.id == project_id, Project.organization_id == org_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_project_detail(session: AsyncSession, project_id: int, org_id: int) -> dict | None:
        project = await ProjectService.get_project(session, project_id, org_id)
        if not project:
            return None

        # Get samples grouped by experiment (single JOIN query)
        sample_stmt = (
            select(ProjectSample, Sample, Experiment)
            .join(Sample, Sample.id == ProjectSample.sample_id)
            .join(Experiment, Experiment.id == Sample.experiment_id)
            .where(ProjectSample.project_id == project_id)
            .order_by(Experiment.name, Sample.sample_id_external)
        )
        sample_result = await session.execute(sample_stmt)
        sample_rows = sample_result.all()

        # Load added_by user names
        user_ids = {ps.added_by_user_id for ps, _, _ in sample_rows}
        user_names = {}
        if user_ids:
            from app.models.user import User
            user_result = await session.execute(
                select(User.id, User.name).where(User.id.in_(user_ids))
            )
            user_names = dict(user_result.all())

        # Group by experiment
        groups: dict[int, dict] = {}
        for ps, sample, experiment in sample_rows:
            if experiment.id not in groups:
                groups[experiment.id] = {
                    "experiment_id": experiment.id,
                    "experiment_name": experiment.name,
                    "samples": [],
                }
            groups[experiment.id]["samples"].append({
                "sample_id": sample.id,
                "sample_id_external": sample.sample_id_external,
                "organism": sample.organism,
                "tissue_type": sample.tissue_type,
                "qc_status": sample.qc_status,
                "added_by": user_names.get(ps.added_by_user_id),
                "added_at": ps.added_at,
                "notes": ps.notes,
            })

        # Get pipeline runs
        run_result = await session.execute(
            select(PipelineRun)
            .where(PipelineRun.project_id == project_id)
            .order_by(PipelineRun.created_at.desc())
        )
        runs = run_result.scalars().all()

        # Counts
        sample_count = len(sample_rows)
        experiment_count = len(groups)
        snap_result = await session.execute(
            select(func.count(AnalysisSnapshot.id))
            .where(AnalysisSnapshot.project_id == project_id)
        )
        snapshot_count = snap_result.scalar() or 0

        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "hypothesis": project.hypothesis,
            "status": project.status,
            "owner_user_id": project.owner_user_id,
            "owner_name": project.owner.name if project.owner else None,
            "sample_count": sample_count,
            "experiment_count": experiment_count,
            "pipeline_run_count": len(runs),
            "snapshot_count": snapshot_count,
            "created_at": project.created_at,
            "samples": list(groups.values()),
            "pipeline_runs": [
                {
                    "id": r.id,
                    "pipeline_name": r.pipeline_name,
                    "pipeline_version": r.pipeline_version,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in runs
            ],
        }

    @staticmethod
    async def add_samples(
        session: AsyncSession,
        project_id: int,
        user_id: int,
        data: ProjectSamplesAdd,
    ) -> list[ProjectSample]:
        # Validate all sample_ids exist
        result = await session.execute(
            select(Sample.id).where(Sample.id.in_(data.sample_ids))
        )
        found_ids = {row[0] for row in result.all()}
        missing = set(data.sample_ids) - found_ids
        if missing:
            raise HTTPException(404, f"Samples not found: {sorted(missing)}")

        # Check for duplicates
        existing = await session.execute(
            select(ProjectSample.sample_id).where(
                ProjectSample.project_id == project_id,
                ProjectSample.sample_id.in_(data.sample_ids),
            )
        )
        dupes = {row[0] for row in existing.all()}
        if dupes:
            raise HTTPException(409, f"Samples already in project: {sorted(dupes)}")

        added = []
        for sid in data.sample_ids:
            ps = ProjectSample(
                project_id=project_id,
                sample_id=sid,
                added_by_user_id=user_id,
                notes=data.notes,
            )
            session.add(ps)
            added.append(ps)

            await log_action(
                session,
                user_id=user_id,
                entity_type="project_sample",
                entity_id=project_id,
                action="sample_added",
                details={"sample_id": sid, "notes": data.notes},
            )

        await session.flush()
        return added

    @staticmethod
    async def remove_sample(
        session: AsyncSession,
        project_id: int,
        sample_id: int,
        user_id: int,
    ) -> None:
        result = await session.execute(
            select(ProjectSample).where(
                ProjectSample.project_id == project_id,
                ProjectSample.sample_id == sample_id,
            )
        )
        ps = result.scalar_one_or_none()
        if not ps:
            raise HTTPException(404, "Sample not in project")

        await session.delete(ps)
        await log_action(
            session,
            user_id=user_id,
            entity_type="project_sample",
            entity_id=project_id,
            action="sample_removed",
            details={"sample_id": sample_id},
        )
        await session.flush()
