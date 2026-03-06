import asyncio
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

    # Start background tasks
    background_tasks = []
    background_tasks.append(asyncio.create_task(_job_status_sync_loop()))
    background_tasks.append(asyncio.create_task(_idle_session_check_loop()))
    background_tasks.append(asyncio.create_task(_quota_reset_loop()))
    background_tasks.append(asyncio.create_task(_pipeline_monitor_loop()))
    logger.info("Background tasks started")

    yield

    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    await asyncio.gather(*background_tasks, return_exceptions=True)

    # Shutdown
    await engine.dispose()
    logger.info("bioAF backend shut down")


async def _job_status_sync_loop():
    """Sync SLURM job statuses every 60 seconds."""
    from app.database import async_session_factory
    from app.services.slurm_service import SlurmService

    while True:
        try:
            await asyncio.sleep(60)
            async with async_session_factory() as session:
                await SlurmService.sync_job_statuses(session)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Job status sync error: %s", e)


async def _idle_session_check_loop():
    """Check for idle notebook sessions every 5 minutes."""
    from app.database import async_session_factory
    from app.services.notebook_service import NotebookService

    while True:
        try:
            await asyncio.sleep(300)
            async with async_session_factory() as session:
                await NotebookService.check_idle_sessions(session)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Idle session check error: %s", e)


async def _quota_reset_loop():
    """Check for monthly quota resets every hour."""
    from app.database import async_session_factory
    from app.services.quota_service import QuotaService

    while True:
        try:
            await asyncio.sleep(3600)
            async with async_session_factory() as session:
                await QuotaService.reset_monthly_quotas(session)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Quota reset error: %s", e)


async def _pipeline_monitor_loop():
    """Sync pipeline run statuses every 30 seconds."""
    from app.database import async_session_factory
    from app.services.pipeline_monitor_service import PipelineMonitorService

    while True:
        try:
            await asyncio.sleep(30)
            async with async_session_factory() as session:
                await PipelineMonitorService.sync_run_statuses(session)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Pipeline monitor error: %s", e)


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
