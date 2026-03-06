import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import engine
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("bioaf")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("bioAF backend starting up (env=%s)", settings.environment)

    # Fetch secrets from Secret Manager in production
    if settings.use_secret_manager:
        from app.services.secrets_service import SecretsService

        try:
            secrets_service = SecretsService(settings.gcp_project_id)
            secrets = secrets_service.fetch_all()
            # Update settings from secrets
            if "bioaf-db-app-password" in secrets:
                settings.database_url = settings.database_url.replace("password", secrets["bioaf-db-app-password"])
            if "bioaf-jwt-signing-key" in secrets:
                settings.jwt_secret_key = secrets["bioaf-jwt-signing-key"]
            if "bioaf-smtp-credentials" in secrets:
                import json

                smtp_config = json.loads(secrets["bioaf-smtp-credentials"])
                if smtp_config.get("host"):
                    settings.smtp_host = smtp_config["host"]
                    settings.smtp_port = smtp_config.get("port", 587)
                    settings.smtp_username = smtp_config.get("username", "")
                    settings.smtp_password = smtp_config.get("password", "")
                    settings.smtp_from_address = smtp_config.get("from_address", "")
                    settings.smtp_configured = True
            logger.info("Secrets fetched from Secret Manager")
        except Exception as e:
            logger.error("Failed to fetch secrets from Secret Manager: %s", e)
            raise RuntimeError(f"Secret Manager unreachable: {e}") from e

    # Verify database connection
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    logger.info("bioAF backend started successfully")
    yield

    # Shutdown
    await engine.dispose()
    logger.info("bioAF backend shut down")


app = FastAPI(
    title="bioAF API",
    version=settings.app_version,
    lifespan=lifespan,
)

# Middleware (applied in reverse order)
app.add_middleware(AuthMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Include routers
from app.api.router import api_router  # noqa: E402

app.include_router(api_router)
