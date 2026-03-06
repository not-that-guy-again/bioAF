import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment import Environment, EnvironmentPackage
from app.models.environment_change import EnvironmentChange
from app.services.audit_service import log_action
from app.services.environment_service import EnvironmentService
from app.services.gitops_service import GitOpsService

logger = logging.getLogger("bioaf.package")


class PackageService:
    @staticmethod
    async def _get_env_and_repo(session: AsyncSession, org_id: int, env_name: str):
        """Get environment and repo, raising if not found."""
        env = await EnvironmentService.get_environment(session, org_id, env_name)
        if not env:
            raise ValueError(f"Environment '{env_name}' not found")
        if env.status == "archived":
            raise ValueError(f"Environment '{env_name}' is archived")

        repo = await GitOpsService.get_repo(session, org_id)
        if not repo:
            raise ValueError("GitOps repository not initialized")

        return env, repo

    @staticmethod
    async def install_package(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        environment_name: str,
        package_name: str,
        version: str | None,
        source: str,
        pinned: bool = False,
    ) -> EnvironmentChange:
        env, repo = await PackageService._get_env_and_repo(session, org_id, environment_name)

        # Read current YAML
        yaml_content = await GitOpsService.get_file(org_id, repo.github_repo_name, env.yaml_path)

        # Update YAML
        new_yaml = EnvironmentService.update_conda_yaml(yaml_content, package_name, version, source, "install")

        # Commit to GitOps
        version_str = f"=={version}" if version else ""
        commit_sha = await GitOpsService.commit_and_push(
            session, org_id, user_id,
            files={env.yaml_path: new_yaml},
            message=f"env: install {package_name}{version_str} into {environment_name}",
        )

        # Create change record
        change = EnvironmentChange(
            organization_id=org_id,
            environment_id=env.id,
            user_id=user_id,
            change_type="install",
            package_name=package_name,
            new_version=version,
            git_commit_sha=commit_sha,
            commit_message=f"Install {package_name}{version_str}",
        )
        session.add(change)

        # Add to packages table
        pkg = EnvironmentPackage(
            environment_id=env.id,
            package_name=package_name,
            version=version,
            pinned=pinned,
            source=source,
        )
        session.add(pkg)

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment_package",
            entity_id=env.id,
            action="install",
            details={"package": package_name, "version": version, "source": source, "environment": environment_name},
        )
        await session.flush()
        return change

    @staticmethod
    async def remove_package(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        environment_name: str,
        package_name: str,
        source: str,
    ) -> EnvironmentChange:
        env, repo = await PackageService._get_env_and_repo(session, org_id, environment_name)

        yaml_content = await GitOpsService.get_file(org_id, repo.github_repo_name, env.yaml_path)
        new_yaml = EnvironmentService.update_conda_yaml(yaml_content, package_name, None, source, "remove")

        commit_sha = await GitOpsService.commit_and_push(
            session, org_id, user_id,
            files={env.yaml_path: new_yaml},
            message=f"env: remove {package_name} from {environment_name}",
        )

        change = EnvironmentChange(
            organization_id=org_id,
            environment_id=env.id,
            user_id=user_id,
            change_type="remove",
            package_name=package_name,
            git_commit_sha=commit_sha,
            commit_message=f"Remove {package_name}",
        )
        session.add(change)

        # Remove from packages table
        result = await session.execute(
            select(EnvironmentPackage).where(
                EnvironmentPackage.environment_id == env.id,
                EnvironmentPackage.package_name == package_name,
                EnvironmentPackage.source == source,
            )
        )
        pkg = result.scalar_one_or_none()
        if pkg:
            await session.delete(pkg)

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment_package",
            entity_id=env.id,
            action="remove",
            details={"package": package_name, "source": source, "environment": environment_name},
        )
        await session.flush()
        return change

    @staticmethod
    async def update_package(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        environment_name: str,
        package_name: str,
        new_version: str,
        source: str,
    ) -> EnvironmentChange:
        env, repo = await PackageService._get_env_and_repo(session, org_id, environment_name)

        # Get old version
        result = await session.execute(
            select(EnvironmentPackage).where(
                EnvironmentPackage.environment_id == env.id,
                EnvironmentPackage.package_name == package_name,
                EnvironmentPackage.source == source,
            )
        )
        pkg = result.scalar_one_or_none()
        old_version = pkg.version if pkg else None

        yaml_content = await GitOpsService.get_file(org_id, repo.github_repo_name, env.yaml_path)
        new_yaml = EnvironmentService.update_conda_yaml(yaml_content, package_name, new_version, source, "update")

        commit_sha = await GitOpsService.commit_and_push(
            session, org_id, user_id,
            files={env.yaml_path: new_yaml},
            message=f"env: update {package_name} to {new_version} in {environment_name}",
        )

        change = EnvironmentChange(
            organization_id=org_id,
            environment_id=env.id,
            user_id=user_id,
            change_type="update",
            package_name=package_name,
            old_version=old_version,
            new_version=new_version,
            git_commit_sha=commit_sha,
            commit_message=f"Update {package_name} to {new_version}",
        )
        session.add(change)

        if pkg:
            pkg.version = new_version

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment_package",
            entity_id=env.id,
            action="update",
            details={"package": package_name, "old_version": old_version, "new_version": new_version, "environment": environment_name},
            previous_value={"version": old_version},
        )
        await session.flush()
        return change

    @staticmethod
    async def pin_package(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        environment_name: str,
        package_name: str,
        version: str,
    ) -> EnvironmentChange:
        env, repo = await PackageService._get_env_and_repo(session, org_id, environment_name)

        yaml_content = await GitOpsService.get_file(org_id, repo.github_repo_name, env.yaml_path)
        new_yaml = EnvironmentService.update_conda_yaml(yaml_content, package_name, version, "conda", "update")

        commit_sha = await GitOpsService.commit_and_push(
            session, org_id, user_id,
            files={env.yaml_path: new_yaml},
            message=f"env: pin {package_name}=={version} in {environment_name}",
        )

        change = EnvironmentChange(
            organization_id=org_id,
            environment_id=env.id,
            user_id=user_id,
            change_type="pin",
            package_name=package_name,
            new_version=version,
            git_commit_sha=commit_sha,
            commit_message=f"Pin {package_name} to {version}",
        )
        session.add(change)

        result = await session.execute(
            select(EnvironmentPackage).where(
                EnvironmentPackage.environment_id == env.id,
                EnvironmentPackage.package_name == package_name,
            )
        )
        pkg = result.scalar_one_or_none()
        if pkg:
            pkg.pinned = True
            pkg.version = version

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment_package",
            entity_id=env.id,
            action="pin",
            details={"package": package_name, "version": version, "environment": environment_name},
        )
        await session.flush()
        return change

    @staticmethod
    async def unpin_package(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        environment_name: str,
        package_name: str,
    ) -> EnvironmentChange:
        env, repo = await PackageService._get_env_and_repo(session, org_id, environment_name)

        yaml_content = await GitOpsService.get_file(org_id, repo.github_repo_name, env.yaml_path)
        # Remove version constraint
        new_yaml = EnvironmentService.update_conda_yaml(yaml_content, package_name, None, "conda", "update")

        commit_sha = await GitOpsService.commit_and_push(
            session, org_id, user_id,
            files={env.yaml_path: new_yaml},
            message=f"env: unpin {package_name} in {environment_name}",
        )

        change = EnvironmentChange(
            organization_id=org_id,
            environment_id=env.id,
            user_id=user_id,
            change_type="unpin",
            package_name=package_name,
            git_commit_sha=commit_sha,
            commit_message=f"Unpin {package_name}",
        )
        session.add(change)

        result = await session.execute(
            select(EnvironmentPackage).where(
                EnvironmentPackage.environment_id == env.id,
                EnvironmentPackage.package_name == package_name,
            )
        )
        pkg = result.scalar_one_or_none()
        if pkg:
            pkg.pinned = False

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment_package",
            entity_id=env.id,
            action="unpin",
            details={"package": package_name, "environment": environment_name},
        )
        await session.flush()
        return change
