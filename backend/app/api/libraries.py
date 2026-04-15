from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.database import get_session
from app.models.library import Library
from app.schemas.library import LibraryCreate, LibraryResponse, LibraryUpdate
from app.services.library_service import LibraryService

router = APIRouter(tags=["libraries"])


def _response(lib: Library) -> LibraryResponse:
    return LibraryResponse.model_validate(lib)


@router.post("/api/libraries", response_model=LibraryResponse)
async def create_library(
    body: LibraryCreate,
    current_user: dict = require_permission("libraries", "create"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    user_id = int(current_user["sub"])
    lib = await LibraryService.create_library(session, org_id, body, user_id=user_id)
    await session.commit()
    return _response(lib)


@router.get("/api/libraries/{library_id}", response_model=LibraryResponse)
async def get_library(
    library_id: int,
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    lib = await LibraryService.get_library(session, org_id, library_id)
    return _response(lib)


@router.patch("/api/libraries/{library_id}", response_model=LibraryResponse)
async def update_library(
    library_id: int,
    body: LibraryUpdate,
    current_user: dict = require_permission("libraries", "edit"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    user_id = int(current_user["sub"])
    lib = await LibraryService.update_library(session, org_id, library_id, body, user_id=user_id)
    await session.commit()
    return _response(lib)


@router.get("/api/samples/{sample_id}/libraries", response_model=list[LibraryResponse])
async def list_libraries_for_sample(
    sample_id: int,
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    libs = await LibraryService.list_libraries_for_sample(session, org_id, sample_id)
    return [_response(lib) for lib in libs]


@router.get(
    "/api/experiments/{experiment_id}/libraries",
    response_model=list[LibraryResponse],
)
async def list_libraries_for_experiment(
    experiment_id: int,
    current_user: dict = require_permission("libraries", "view"),
    session: AsyncSession = Depends(get_session),
):
    org_id = int(current_user["org_id"])
    libs = await LibraryService.list_libraries_for_experiment(session, org_id, experiment_id)
    return [_response(lib) for lib in libs]


@router.post("/api/libraries/{library_id}/files/{file_id}", response_model=LibraryResponse)
async def attach_file(
    library_id: int,
    file_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    _: dict = require_permission("libraries", "edit"),
):
    current_user = request.state.current_user
    org_id = int(current_user["org_id"])
    user_id = int(current_user["sub"])
    # Files permission is additionally enforced so users without file edit can't mutate file rows.
    from app.services import role_service

    if not await role_service.has_permission(session, int(current_user["role_id"]), "files", "edit"):
        from fastapi import HTTPException

        raise HTTPException(403, "Insufficient permissions")

    lib = await LibraryService.attach_file(session, org_id, library_id, file_id, user_id=user_id)
    await session.commit()
    return _response(lib)
