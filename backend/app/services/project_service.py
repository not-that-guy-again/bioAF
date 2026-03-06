from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experiment import Experiment
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.audit_service import log_action


class ProjectService:
    @staticmethod
    async def create_project(session: AsyncSession, org_id: int, user_id: int, data: ProjectCreate) -> Project:
        project = Project(
            organization_id=org_id,
            name=data.name,
            description=data.description,
            created_by_user_id=user_id,
        )
        session.add(project)
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="project",
            entity_id=project.id,
            action="create",
            details={"name": data.name},
        )
        return project

    @staticmethod
    async def update_project(session: AsyncSession, project_id: int, user_id: int, data: ProjectUpdate) -> Project:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            return None

        previous = {}
        updates = {}
        for field in ["name", "description"]:
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
                action="update",
                details=updates,
                previous_value=previous,
            )
        return project

    @staticmethod
    async def list_projects(session: AsyncSession, org_id: int) -> list[tuple[Project, int]]:
        stmt = (
            select(Project, func.count(Experiment.id).label("experiment_count"))
            .outerjoin(Experiment, Experiment.project_id == Project.id)
            .where(Project.organization_id == org_id)
            .group_by(Project.id)
            .order_by(Project.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.all())

    @staticmethod
    async def get_project(session: AsyncSession, project_id: int, org_id: int) -> Project | None:
        result = await session.execute(
            select(Project).where(Project.id == project_id, Project.organization_id == org_id)
        )
        return result.scalar_one_or_none()
