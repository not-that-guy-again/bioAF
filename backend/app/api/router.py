from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.bootstrap import router as bootstrap_router
from app.api.components import router as components_router
from app.api.health import router as health_router
from app.api.terraform import router as terraform_router
from app.api.users import router as users_router
from app.api.experiments import router as experiments_router
from app.api.samples import router as samples_router
from app.api.batches import router as batches_router
from app.api.projects import router as projects_router
from app.api.templates import router as templates_router
from app.api.audit import router as audit_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(bootstrap_router)
api_router.include_router(users_router)
api_router.include_router(components_router)
api_router.include_router(terraform_router)
api_router.include_router(experiments_router)
api_router.include_router(samples_router)
api_router.include_router(batches_router)
api_router.include_router(projects_router)
api_router.include_router(templates_router)
api_router.include_router(audit_router)
