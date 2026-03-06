import logging

import yaml
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment import Environment
from app.models.environment_change import EnvironmentChange
from app.services.audit_service import log_action
from app.services.gitops_service import GitOpsService

logger = logging.getLogger("bioaf.environment_history")


class EnvironmentHistoryService:
    @staticmethod
    async def get_change_timeline(
        session: AsyncSession,
        org_id: int,
        environment_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[EnvironmentChange], int]:
        """Get paginated change timeline for an environment."""
        # Count total
        count_result = await session.execute(
            select(func.count()).select_from(EnvironmentChange).where(
                EnvironmentChange.organization_id == org_id,
                EnvironmentChange.environment_id == environment_id,
            )
        )
        total = count_result.scalar() or 0

        # Get page
        result = await session.execute(
            select(EnvironmentChange)
            .where(
                EnvironmentChange.organization_id == org_id,
                EnvironmentChange.environment_id == environment_id,
            )
            .order_by(EnvironmentChange.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        changes = list(result.scalars().all())
        return changes, total

    @staticmethod
    async def get_change_detail(
        session: AsyncSession, org_id: int, change_id: int,
    ) -> EnvironmentChange | None:
        result = await session.execute(
            select(EnvironmentChange).where(
                EnvironmentChange.id == change_id,
                EnvironmentChange.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def rollback_environment(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        environment_id: int,
        target_change_id: int,
    ) -> EnvironmentChange:
        """Rollback an environment to the state at a given change."""
        # Get the target change
        target = await EnvironmentHistoryService.get_change_detail(session, org_id, target_change_id)
        if not target:
            raise ValueError(f"Change {target_change_id} not found")
        if target.environment_id != environment_id:
            raise ValueError("Change does not belong to this environment")
        if not target.git_commit_sha:
            raise ValueError("Target change has no git commit reference")

        # Get environment
        result = await session.execute(
            select(Environment).where(Environment.id == environment_id)
        )
        env = result.scalar_one_or_none()
        if not env:
            raise ValueError(f"Environment {environment_id} not found")

        # Get repo
        repo = await GitOpsService.get_repo(session, org_id)
        if not repo:
            raise ValueError("GitOps repo not initialized")

        # Read the YAML at the target commit
        old_content = await GitOpsService.get_file(
            org_id, repo.github_repo_name, env.yaml_path, ref=target.git_commit_sha,
        )

        # Commit as new version
        short_sha = target.git_commit_sha[:8]
        commit_sha = await GitOpsService.commit_and_push(
            session, org_id, user_id,
            files={env.yaml_path: old_content},
            message=f"env: rollback {env.name} to commit {short_sha}",
        )

        # Create change record
        change = EnvironmentChange(
            organization_id=org_id,
            environment_id=environment_id,
            user_id=user_id,
            change_type="rollback",
            git_commit_sha=commit_sha,
            commit_message=f"Rollback to commit {short_sha}",
        )
        session.add(change)

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment",
            entity_id=environment_id,
            action="rollback",
            details={
                "target_change_id": target_change_id,
                "target_commit": target.git_commit_sha,
                "new_commit": commit_sha,
            },
        )
        await session.flush()
        return change

    @staticmethod
    async def compare_environments(
        session: AsyncSession,
        org_id: int,
        env_name: str,
        sha1: str,
        sha2: str,
    ) -> dict:
        """Compare two versions of an environment YAML."""
        env = await session.execute(
            select(Environment).where(
                Environment.organization_id == org_id,
                Environment.name == env_name,
            )
        )
        env_obj = env.scalar_one_or_none()
        if not env_obj:
            raise ValueError(f"Environment '{env_name}' not found")

        repo = await GitOpsService.get_repo(session, org_id)
        if not repo:
            raise ValueError("GitOps repo not initialized")

        content1 = await GitOpsService.get_file(org_id, repo.github_repo_name, env_obj.yaml_path, ref=sha1)
        content2 = await GitOpsService.get_file(org_id, repo.github_repo_name, env_obj.yaml_path, ref=sha2)

        from app.services.environment_service import EnvironmentService

        pkgs1 = {p["name"]: p for p in EnvironmentService._parse_conda_yaml(content1)}
        pkgs2 = {p["name"]: p for p in EnvironmentService._parse_conda_yaml(content2)}

        added = [name for name in pkgs2 if name not in pkgs1]
        removed = [name for name in pkgs1 if name not in pkgs2]
        changed = []
        for name in pkgs1:
            if name in pkgs2 and pkgs1[name].get("version") != pkgs2[name].get("version"):
                changed.append({
                    "name": name,
                    "old_version": pkgs1[name].get("version"),
                    "new_version": pkgs2[name].get("version"),
                })

        return {"added": added, "removed": removed, "changed": changed}
