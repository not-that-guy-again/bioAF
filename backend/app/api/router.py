from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.bootstrap import router as bootstrap_router
from app.api.components import router as components_router
from app.api.health import router as health_router
from app.api.terraform import router as terraform_router
from app.api.users import router as users_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(bootstrap_router)
api_router.include_router(users_router)
api_router.include_router(components_router)
api_router.include_router(terraform_router)
