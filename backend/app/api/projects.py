from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.api.dependencies import require_role
from app.schemas.project import ProjectCreate, ProjectListResponse, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    current_user = request.state.current_user
    org_id = int(current_user["org_id"])

    results = await ProjectService.list_projects(session, org_id)
    projects = [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            experiment_count=count,
            created_by_name=p.created_by.name if p.created_by else None,
            created_at=p.created_at,
        )
        for p, count in results
    ]
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post("", response_model=ProjectResponse)
async def create_project(
    body: ProjectCreate,
    current_user: dict = require_role("admin", "comp_bio"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    user_id = int(current_user["sub"])

    project = await ProjectService.create_project(session, org_id, user_id, body)
    await session.commit()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        experiment_count=0,
        created_by_name=None,
        created_at=project.created_at,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    current_user = request.state.current_user
    org_id = int(current_user["org_id"])

    project = await ProjectService.get_project(session, project_id, org_id)
    if not project:
        raise HTTPException(404, "Project not found")

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        experiment_count=len(project.experiments) if hasattr(project, "experiments") and project.experiments else 0,
        created_by_name=None,
        created_at=project.created_at,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    current_user: dict = require_role("admin", "comp_bio"),
    session: AsyncSession = Depends(get_session),
):
    user_id = int(current_user["sub"])

    project = await ProjectService.update_project(session, project_id, user_id, body)
    if not project:
        raise HTTPException(404, "Project not found")

    await session.commit()
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        experiment_count=0,
        created_by_name=None,
        created_at=project.created_at,
    )
