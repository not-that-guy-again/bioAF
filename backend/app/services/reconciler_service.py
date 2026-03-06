import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment import Environment
from app.models.environment_change import EnvironmentChange
from app.services.environment_service import EnvironmentService
from app.services.gitops_service import GitOpsService

logger = logging.getLogger("bioaf.reconciler")


class ReconcilerService:
    @staticmethod
    async def process_pending(session: AsyncSession) -> None:
        """Process all unreconciled environment changes."""
        result = await session.execute(
            select(EnvironmentChange)
            .where(
                EnvironmentChange.reconciled == False,  # noqa: E712
                EnvironmentChange.error_message.is_(None),
            )
            .order_by(EnvironmentChange.created_at)
            .limit(5)
        )
        changes = list(result.scalars().all())

        for change in changes:
            try:
                await ReconcilerService._reconcile_change(session, change)
                change.reconciled = True
                change.reconciled_at = datetime.now(timezone.utc)
                logger.info("Reconciled change %d for environment %d", change.id, change.environment_id)
            except Exception as e:
                change.error_message = str(e)
                logger.error("Reconciliation failed for change %d: %s", change.id, e)

            await session.commit()

    @staticmethod
    async def _reconcile_change(session: AsyncSession, change: EnvironmentChange) -> None:
        """Apply a single environment change to the SLURM cluster."""
        # Get environment info
        result = await session.execute(select(Environment).where(Environment.id == change.environment_id))
        env = result.scalar_one_or_none()
        if not env:
            raise ValueError(f"Environment {change.environment_id} not found")

        # Get repo info
        repo = await GitOpsService.get_repo(session, change.organization_id)
        if not repo:
            raise ValueError("GitOps repo not found")

        # Read current YAML from GitOps
        yaml_content = await GitOpsService.get_file(
            change.organization_id,
            repo.github_repo_name,
            env.yaml_path,
        )

        # SSH into SLURM controller and apply changes
        if change.change_type == "create":
            await ReconcilerService._create_environment(env, yaml_content)
        elif env.env_type in ("conda", "custom_conda"):
            await ReconcilerService._update_conda_env(env, yaml_content)
        elif env.env_type == "r":
            await ReconcilerService._update_r_env(env, yaml_content)

        # Sync package list from YAML to DB
        await EnvironmentService.sync_packages_from_yaml(
            session,
            change.organization_id,
            env.id,
            yaml_content,
        )

        # Update environment status
        env.status = "active"

    @staticmethod
    async def _create_environment(env: Environment, yaml_content: str) -> None:
        """Create a new conda environment on SLURM via SSH."""
        commands = [
            f"cat > /tmp/{env.name}.yml << 'ENVEOF'\n{yaml_content}\nENVEOF",
            f"conda env create -f /tmp/{env.name}.yml",
            f"conda run -n {env.name} python -m ipykernel install --name {env.name} --display-name 'bioAF: {env.name}'",
            f"rm /tmp/{env.name}.yml",
        ]
        await ReconcilerService._ssh_execute_commands(env.organization_id, commands)

    @staticmethod
    async def _update_conda_env(env: Environment, yaml_content: str) -> None:
        """Update an existing conda environment on SLURM via SSH."""
        commands = [
            f"cat > /tmp/{env.name}.yml << 'ENVEOF'\n{yaml_content}\nENVEOF",
            f"conda env update -f /tmp/{env.name}.yml --prune",
            f"rm /tmp/{env.name}.yml",
        ]
        await ReconcilerService._ssh_execute_commands(env.organization_id, commands)

    @staticmethod
    async def _update_r_env(env: Environment, yaml_content: str) -> None:
        """Update R packages on SLURM via SSH."""
        commands = [
            f"cat > /tmp/{env.name}_install.R << 'REOF'\n{yaml_content}\nREOF",
            f"Rscript /tmp/{env.name}_install.R",
            f"rm /tmp/{env.name}_install.R",
        ]
        await ReconcilerService._ssh_execute_commands(env.organization_id, commands)

    @staticmethod
    async def _ssh_execute_commands(org_id: int, commands: list[str]) -> tuple[str, str, int]:
        """Execute commands on the SLURM controller via SSH."""
        try:
            import asyncssh

            ssh_key = await ReconcilerService._get_slurm_ssh_key()
            controller_ip = await ReconcilerService._get_slurm_controller_ip(org_id)

            key = asyncssh.import_private_key(ssh_key)
            async with asyncssh.connect(
                controller_ip,
                username="bioaf",
                client_keys=[key],
                known_hosts=None,
            ) as conn:
                full_command = " && ".join(commands)
                result = await conn.run(full_command, check=True)
                return result.stdout or "", result.stderr or "", result.exit_status or 0
        except ImportError:
            logger.warning("asyncssh not available, skipping SSH execution")
            return "", "asyncssh not available", 1
        except Exception as e:
            raise RuntimeError(f"SSH execution failed: {e}") from e

    @staticmethod
    async def _get_slurm_ssh_key() -> str:
        """Fetch SLURM SSH key from Secret Manager."""
        from app.config import settings

        if settings.use_secret_manager:
            from app.services.secrets_service import SecretsService

            svc = SecretsService(settings.gcp_project_id)
            secrets = svc.fetch_all()
            key = secrets.get("bioaf-slurm-ssh-key")
            if not key:
                raise ValueError("SLURM SSH key not found in Secret Manager")
            return key

        import os

        return os.environ.get("BIOAF_SLURM_SSH_KEY", "")

    @staticmethod
    async def _get_slurm_controller_ip(org_id: int) -> str:
        """Get the SLURM controller IP. In production, read from component state."""
        import os

        return os.environ.get("BIOAF_SLURM_CONTROLLER_IP", "10.0.0.2")
