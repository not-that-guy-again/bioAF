import logging
import re
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.custom_pipeline import CustomPipeline
from app.models.custom_pipeline_variable import CustomPipelineVariable
from app.models.custom_pipeline_version import CustomPipelineVersion
from app.models.environment_version import EnvironmentVersion
from app.models.github_repo import GitHubRepo
from app.models.pipeline_catalog_entry import PipelineCatalogEntry
from app.schemas.custom_pipeline import (
    CustomPipelineCreateRequest,
    CustomPipelineUpdateRequest,
    CustomPipelineVersionCreateRequest,
)
from app.services.audit_service import log_action

logger = logging.getLogger("bioaf.custom_pipeline")


VALID_CODE_SOURCE_TYPES = ("github_repo", "code_blob", "inline")
CPU_PATTERN = re.compile(r"^\d+(\.\d+)?m?$")
MEMORY_PATTERN = re.compile(r"^\d+(Ki|Mi|Gi|Ti|Pi|Ei|K|M|G|T|P|E)?$")


def _slugify(name: str) -> str:
    """Lowercase, replace spaces with hyphens, strip special chars, truncate to 100."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100]


def _validate_resource_strings(cpu_request: str, memory_request: str) -> None:
    if not CPU_PATTERN.match(cpu_request):
        raise ValueError(f"Invalid cpu_request: {cpu_request}")
    if not MEMORY_PATTERN.match(memory_request):
        raise ValueError(f"Invalid memory_request: {memory_request}")


class CustomPipelineService:
    @staticmethod
    async def _generate_unique_pipeline_key(session: AsyncSession, org_id: int, name: str) -> str:
        base = _slugify(name)
        if not base:
            base = "pipeline"
        candidate = base
        suffix = 2
        while True:
            pipeline_existing = await session.execute(
                select(CustomPipeline).where(
                    CustomPipeline.organization_id == org_id,
                    CustomPipeline.pipeline_key == candidate,
                )
            )
            catalog_existing = await session.execute(
                select(PipelineCatalogEntry).where(
                    PipelineCatalogEntry.organization_id == org_id,
                    PipelineCatalogEntry.pipeline_key == candidate,
                )
            )
            if pipeline_existing.scalar_one_or_none() is None and catalog_existing.scalar_one_or_none() is None:
                return candidate
            candidate = f"{base}-{suffix}"[:100]
            suffix += 1

    @staticmethod
    async def create_pipeline(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        data: CustomPipelineCreateRequest,
    ) -> CustomPipeline:
        pipeline_key = await CustomPipelineService._generate_unique_pipeline_key(session, org_id, data.name)

        pipeline = CustomPipeline(
            organization_id=org_id,
            name=data.name,
            description=data.description,
            pipeline_key=pipeline_key,
            created_by_user_id=user_id,
        )
        session.add(pipeline)
        await session.flush()

        catalog_entry = PipelineCatalogEntry(
            organization_id=org_id,
            pipeline_key=pipeline_key,
            name=data.name,
            description=data.description,
            source_type="custom",
            custom_pipeline_id=pipeline.id,
            is_builtin=False,
            enabled=True,
        )
        session.add(catalog_entry)
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="custom_pipeline",
            entity_id=pipeline.id,
            action="create",
            details={"name": data.name, "pipeline_key": pipeline_key},
        )
        return pipeline

    @staticmethod
    async def list_pipelines(session: AsyncSession, org_id: int) -> list[CustomPipeline]:
        result = await session.execute(
            select(CustomPipeline)
            .where(CustomPipeline.organization_id == org_id)
            .options(selectinload(CustomPipeline.created_by))
            .order_by(CustomPipeline.name)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_pipeline(session: AsyncSession, org_id: int, pipeline_id: int) -> CustomPipeline | None:
        result = await session.execute(
            select(CustomPipeline)
            .where(
                CustomPipeline.id == pipeline_id,
                CustomPipeline.organization_id == org_id,
            )
            .options(
                selectinload(CustomPipeline.versions).selectinload(CustomPipelineVersion.variables),
                selectinload(CustomPipeline.created_by),
            )
        )
        pipeline = result.scalar_one_or_none()
        if pipeline is not None:
            pipeline.versions.sort(key=lambda v: v.version_number, reverse=True)
        return pipeline

    @staticmethod
    async def _get_pipeline_unscoped(session: AsyncSession, org_id: int, pipeline_id: int) -> CustomPipeline | None:
        result = await session.execute(
            select(CustomPipeline).where(
                CustomPipeline.id == pipeline_id,
                CustomPipeline.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_pipeline(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        pipeline_id: int,
        data: CustomPipelineUpdateRequest,
    ) -> CustomPipeline:
        pipeline = await CustomPipelineService._get_pipeline_unscoped(session, org_id, pipeline_id)
        if pipeline is None:
            raise ValueError("Custom pipeline not found")

        previous = {"name": pipeline.name, "description": pipeline.description}
        updates: dict = {}

        if data.name is not None and data.name != pipeline.name:
            pipeline.name = data.name
            updates["name"] = data.name
        if data.description is not None and data.description != pipeline.description:
            pipeline.description = data.description
            updates["description"] = data.description

        if updates:
            catalog_result = await session.execute(
                select(PipelineCatalogEntry).where(
                    PipelineCatalogEntry.organization_id == org_id,
                    PipelineCatalogEntry.custom_pipeline_id == pipeline.id,
                )
            )
            catalog_entry = catalog_result.scalar_one_or_none()
            if catalog_entry is not None:
                if "name" in updates:
                    catalog_entry.name = updates["name"]
                if "description" in updates:
                    catalog_entry.description = updates["description"]

            await session.flush()

            await log_action(
                session,
                user_id=user_id,
                entity_type="custom_pipeline",
                entity_id=pipeline.id,
                action="update",
                details=updates,
                previous_value={k: previous[k] for k in updates},
            )
        return pipeline

    @staticmethod
    async def delete_pipeline(session: AsyncSession, org_id: int, user_id: int, pipeline_id: int) -> None:
        pipeline = await CustomPipelineService._get_pipeline_unscoped(session, org_id, pipeline_id)
        if pipeline is None:
            raise ValueError("Custom pipeline not found")

        catalog_result = await session.execute(
            select(PipelineCatalogEntry).where(
                PipelineCatalogEntry.organization_id == org_id,
                PipelineCatalogEntry.custom_pipeline_id == pipeline.id,
            )
        )
        catalog_entry = catalog_result.scalar_one_or_none()
        if catalog_entry is not None:
            catalog_entry.enabled = False
            await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="custom_pipeline",
            entity_id=pipeline.id,
            action="delete",
            details={"pipeline_key": pipeline.pipeline_key, "name": pipeline.name},
        )

    @staticmethod
    async def create_version(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        pipeline_id: int,
        data: CustomPipelineVersionCreateRequest,
    ) -> CustomPipelineVersion:
        pipeline = await CustomPipelineService._get_pipeline_unscoped(session, org_id, pipeline_id)
        if pipeline is None:
            raise ValueError("Custom pipeline not found")

        if data.code_source_type not in VALID_CODE_SOURCE_TYPES:
            raise ValueError(f"Invalid code_source_type: {data.code_source_type}")

        if not data.entrypoint_command or not data.entrypoint_command.strip():
            raise ValueError("entrypoint_command must not be empty")

        _validate_resource_strings(data.cpu_request, data.memory_request)

        if data.log_file_path is not None and not data.log_file_path.startswith("/outputs/"):
            raise ValueError("log_file_path must start with /outputs/")

        if data.code_source_type == "github_repo":
            if data.github_repo_id is None:
                raise ValueError("github_repo_id is required when code_source_type is 'github_repo'")
            repo_result = await session.execute(
                select(GitHubRepo).where(
                    GitHubRepo.id == data.github_repo_id,
                    GitHubRepo.organization_id == org_id,
                )
            )
            if repo_result.scalar_one_or_none() is None:
                raise ValueError("github_repo_id is not valid for this organization")
        else:
            if not data.code_content:
                raise ValueError(f"code_content is required when code_source_type is '{data.code_source_type}'")

        env_version_result = await session.execute(
            select(EnvironmentVersion).where(EnvironmentVersion.id == data.environment_version_id)
        )
        env_version = env_version_result.scalar_one_or_none()
        if env_version is None:
            raise ValueError("environment_version_id is not valid")
        if env_version.status != "ready":
            raise ValueError(f"Environment version must have status 'ready', got '{env_version.status}'")

        max_result = await session.execute(
            select(func.coalesce(func.max(CustomPipelineVersion.version_number), 0)).where(
                CustomPipelineVersion.custom_pipeline_id == pipeline.id
            )
        )
        next_version_number = (max_result.scalar() or 0) + 1

        version = CustomPipelineVersion(
            custom_pipeline_id=pipeline.id,
            version_number=next_version_number,
            code_source_type=data.code_source_type,
            github_repo_id=data.github_repo_id if data.code_source_type == "github_repo" else None,
            code_content=data.code_content if data.code_source_type != "github_repo" else None,
            entrypoint_command=data.entrypoint_command,
            environment_version_id=data.environment_version_id,
            cpu_request=data.cpu_request,
            memory_request=data.memory_request,
            log_file_path=data.log_file_path,
            version_trigger="user",
            status="active",
            created_by_user_id=user_id,
        )
        session.add(version)
        await session.flush()

        for var in data.variables:
            session.add(
                CustomPipelineVariable(
                    custom_pipeline_version_id=version.id,
                    variable_name=var.variable_name,
                    default_value=var.default_value,
                    variable_type=var.variable_type,
                    is_required=var.is_required,
                )
            )
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="custom_pipeline_version",
            entity_id=version.id,
            action="create",
            details={
                "custom_pipeline_id": pipeline.id,
                "version_number": next_version_number,
                "code_source_type": data.code_source_type,
                "environment_version_id": data.environment_version_id,
            },
        )

        # Re-load with variables for return
        result = await session.execute(
            select(CustomPipelineVersion)
            .where(CustomPipelineVersion.id == version.id)
            .options(selectinload(CustomPipelineVersion.variables))
        )
        return result.scalar_one()

    @staticmethod
    async def list_versions(session: AsyncSession, org_id: int, pipeline_id: int) -> list[CustomPipelineVersion]:
        pipeline = await CustomPipelineService._get_pipeline_unscoped(session, org_id, pipeline_id)
        if pipeline is None:
            raise ValueError("Custom pipeline not found")

        result = await session.execute(
            select(CustomPipelineVersion)
            .where(CustomPipelineVersion.custom_pipeline_id == pipeline.id)
            .options(selectinload(CustomPipelineVersion.variables))
            .order_by(CustomPipelineVersion.version_number.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def handle_environment_build_completed(payload: dict[str, Any]) -> None:
        """Event subscriber: cascade new pipeline versions when a pipeline environment is rebuilt."""
        if payload.get("environment_type") != "pipeline":
            return

        environment_id = payload.get("environment_id")
        environment_version_id = payload.get("environment_version_id")
        if environment_id is None or environment_version_id is None:
            logger.warning("ENVIRONMENT_BUILD_COMPLETED missing required fields: %s", payload)
            return

        from app.database import async_session_factory

        async with async_session_factory() as session:
            await CustomPipelineService.cascade_pipeline_versions(
                session,
                environment_id=int(environment_id),
                environment_version_id=int(environment_version_id),
            )
            await session.commit()

    @staticmethod
    async def cascade_pipeline_versions(
        session: AsyncSession,
        environment_id: int,
        environment_version_id: int,
    ) -> list[CustomPipelineVersion]:
        """Create cascade versions of all pipelines whose latest active version uses this environment.

        Returns the list of newly created cascade versions.
        """
        max_active_subq = (
            select(
                CustomPipelineVersion.custom_pipeline_id.label("pipeline_id"),
                func.max(CustomPipelineVersion.version_number).label("max_v"),
            )
            .where(CustomPipelineVersion.status == "active")
            .group_by(CustomPipelineVersion.custom_pipeline_id)
            .subquery()
        )

        affected_result = await session.execute(
            select(CustomPipelineVersion)
            .join(EnvironmentVersion, CustomPipelineVersion.environment_version_id == EnvironmentVersion.id)
            .join(
                max_active_subq,
                and_(
                    CustomPipelineVersion.custom_pipeline_id == max_active_subq.c.pipeline_id,
                    CustomPipelineVersion.version_number == max_active_subq.c.max_v,
                ),
            )
            .where(
                EnvironmentVersion.environment_id == environment_id,
                CustomPipelineVersion.status == "active",
            )
            .options(selectinload(CustomPipelineVersion.variables))
        )
        affected_versions = list(affected_result.scalars().unique().all())

        if not affected_versions:
            return []

        new_env_version_result = await session.execute(
            select(EnvironmentVersion).where(EnvironmentVersion.id == environment_version_id)
        )
        new_env_version = new_env_version_result.scalar_one_or_none()
        if new_env_version is None:
            logger.warning(
                "Cascade skipped: environment_version_id=%d not found",
                environment_version_id,
            )
            return []

        cascade_user_id = new_env_version.created_by_user_id

        created: list[CustomPipelineVersion] = []
        for source in affected_versions:
            if source.environment_version_id == environment_version_id:
                continue

            max_v_result = await session.execute(
                select(func.coalesce(func.max(CustomPipelineVersion.version_number), 0)).where(
                    CustomPipelineVersion.custom_pipeline_id == source.custom_pipeline_id
                )
            )
            next_version_number = (max_v_result.scalar() or 0) + 1

            cascade_version = CustomPipelineVersion(
                custom_pipeline_id=source.custom_pipeline_id,
                version_number=next_version_number,
                code_source_type=source.code_source_type,
                github_repo_id=source.github_repo_id,
                code_content=source.code_content,
                entrypoint_command=source.entrypoint_command,
                environment_version_id=environment_version_id,
                cpu_request=source.cpu_request,
                memory_request=source.memory_request,
                log_file_path=source.log_file_path,
                version_trigger="environment_cascade",
                status="active",
                created_by_user_id=cascade_user_id,
            )
            session.add(cascade_version)
            await session.flush()

            for var in source.variables:
                session.add(
                    CustomPipelineVariable(
                        custom_pipeline_version_id=cascade_version.id,
                        variable_name=var.variable_name,
                        default_value=var.default_value,
                        variable_type=var.variable_type,
                        is_required=var.is_required,
                    )
                )
            await session.flush()

            await log_action(
                session,
                user_id=cascade_user_id,
                entity_type="custom_pipeline_version",
                entity_id=cascade_version.id,
                action="cascade_create",
                details={
                    "custom_pipeline_id": source.custom_pipeline_id,
                    "source_version_id": source.id,
                    "source_version_number": source.version_number,
                    "new_version_number": next_version_number,
                    "environment_version_id": environment_version_id,
                },
            )
            created.append(cascade_version)

        return created

    @staticmethod
    async def deprecate_version(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        pipeline_id: int,
        version_id: int,
    ) -> CustomPipelineVersion:
        pipeline = await CustomPipelineService._get_pipeline_unscoped(session, org_id, pipeline_id)
        if pipeline is None:
            raise ValueError("Custom pipeline not found")

        result = await session.execute(
            select(CustomPipelineVersion).where(
                CustomPipelineVersion.id == version_id,
                CustomPipelineVersion.custom_pipeline_id == pipeline.id,
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise ValueError("Custom pipeline version not found")

        previous_status = version.status
        version.status = "deprecated"
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="custom_pipeline_version",
            entity_id=version.id,
            action="deprecate",
            details={"version_number": version.version_number},
            previous_value={"status": previous_status},
        )
        return version
