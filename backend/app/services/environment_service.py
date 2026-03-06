import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment import Environment, EnvironmentPackage
from app.models.environment_change import EnvironmentChange
from app.services.audit_service import log_action
from app.services.gitops_service import GitOpsService

logger = logging.getLogger("bioaf.environment")

SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent / "scripts"


class EnvironmentService:
    @staticmethod
    async def initialize_default_environments(session: AsyncSession, org_id: int) -> list[Environment]:
        """Create DB records for built-in environments if they don't exist."""
        created = []

        defaults = [
            {
                "name": "bioaf-scrna",
                "env_type": "conda",
                "yaml_path": "environments/bioaf-scrna.yml",
                "description": "Default scRNA-seq analysis environment (Python/scanpy)",
                "jupyter_kernel_name": "bioaf-scrna",
                "yaml_file": SCRIPTS_DIR / "environments" / "bioaf-scrna.yml",
            },
            {
                "name": "bioaf-rstudio",
                "env_type": "r",
                "yaml_path": "environments/bioaf-rstudio.yml",
                "description": "Default R/Bioconductor analysis environment (Seurat, DESeq2)",
                "jupyter_kernel_name": "bioaf-rstudio",
                "yaml_file": SCRIPTS_DIR / "environments" / "r-bioaf.R",
            },
        ]

        for env_def in defaults:
            result = await session.execute(
                select(Environment).where(
                    Environment.organization_id == org_id,
                    Environment.name == env_def["name"],
                )
            )
            if result.scalar_one_or_none():
                continue

            env = Environment(
                organization_id=org_id,
                name=env_def["name"],
                env_type=env_def["env_type"],
                yaml_path=env_def["yaml_path"],
                is_default=True,
                description=env_def["description"],
                jupyter_kernel_name=env_def["jupyter_kernel_name"],
                status="active",
                last_synced_at=datetime.now(timezone.utc),
            )
            session.add(env)
            await session.flush()

            # Parse packages from YAML
            yaml_file = env_def["yaml_file"]
            if yaml_file.exists():
                content = yaml_file.read_text()
                if env_def["env_type"] == "conda":
                    packages = EnvironmentService._parse_conda_yaml(content)
                else:
                    packages = EnvironmentService._parse_r_script(content)

                for pkg in packages:
                    ep = EnvironmentPackage(
                        environment_id=env.id,
                        package_name=pkg["name"],
                        version=pkg.get("version"),
                        source=pkg["source"],
                    )
                    session.add(ep)

            created.append(env)

        if created:
            await session.flush()
            logger.info("Initialized %d default environments for org %d", len(created), org_id)

        return created

    @staticmethod
    def _parse_conda_yaml(content: str) -> list[dict]:
        """Parse conda YAML to extract package list."""
        data = yaml.safe_load(content)
        if not data or "dependencies" not in data:
            return []

        packages = []
        for dep in data["dependencies"]:
            if isinstance(dep, str):
                name, version = EnvironmentService._parse_conda_dep(dep)
                packages.append({"name": name, "version": version, "source": "conda"})
            elif isinstance(dep, dict) and "pip" in dep:
                for pip_dep in dep["pip"]:
                    name, version = EnvironmentService._parse_conda_dep(pip_dep)
                    packages.append({"name": name, "version": version, "source": "pip"})
        return packages

    @staticmethod
    def _parse_conda_dep(dep_str: str) -> tuple[str, str | None]:
        """Parse 'name>=1.0' or 'name==1.0' or 'name=1.0' into (name, version_spec)."""
        for sep in ["==", ">=", "<=", "!=", "=", ">", "<"]:
            if sep in dep_str:
                parts = dep_str.split(sep, 1)
                return parts[0].strip(), f"{sep}{parts[1].strip()}"
        return dep_str.strip(), None

    @staticmethod
    def _parse_r_script(content: str) -> list[dict]:
        """Parse R install script to extract package names."""
        import re

        packages = []
        # Match strings inside install.packages or BiocManager::install
        pattern = r"(?:install\.packages|BiocManager::install)\s*\(\s*c\s*\((.*?)\)\s*\)"
        for match in re.finditer(pattern, content, re.DOTALL):
            pkg_str = match.group(1)
            for pkg_match in re.finditer(r'"([^"]+)"', pkg_str):
                pkg_name = pkg_match.group(1)
                # Guess source: Bioconductor packages are in BiocManager::install
                source = "bioconductor" if "BiocManager" in match.group(0) else "cran"
                packages.append({"name": pkg_name, "version": None, "source": source})

        # Also match single-package install.packages calls
        for match in re.finditer(r'install\.packages\s*\(\s*"([^"]+)"', content):
            packages.append({"name": match.group(1), "version": None, "source": "cran"})

        return packages

    @staticmethod
    async def list_environments(session: AsyncSession, org_id: int) -> list[dict]:
        """List all environments with package counts."""
        result = await session.execute(
            select(Environment)
            .where(
                Environment.organization_id == org_id,
                Environment.status != "archived",
            )
            .order_by(Environment.is_default.desc(), Environment.name)
        )
        envs = list(result.scalars().all())

        env_list = []
        for env in envs:
            pkg_count = len(env.packages) if env.packages else 0
            env_list.append(
                {
                    "id": env.id,
                    "name": env.name,
                    "env_type": env.env_type,
                    "description": env.description,
                    "is_default": env.is_default,
                    "package_count": pkg_count,
                    "jupyter_kernel_name": env.jupyter_kernel_name,
                    "status": env.status,
                    "last_synced_at": env.last_synced_at,
                    "created_by": {
                        "id": env.created_by.id,
                        "name": env.created_by.name,
                        "email": env.created_by.email,
                    }
                    if env.created_by
                    else None,
                    "created_at": env.created_at,
                }
            )
        return env_list

    @staticmethod
    async def get_environment(session: AsyncSession, org_id: int, env_name: str) -> Environment | None:
        result = await session.execute(
            select(Environment).where(
                Environment.organization_id == org_id,
                Environment.name == env_name,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_custom_environment(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        name: str,
        description: str | None = None,
        clone_from: str | None = None,
    ) -> Environment:
        """Create a custom conda environment."""
        # Check if name already exists
        existing = await EnvironmentService.get_environment(session, org_id, name)
        if existing:
            raise ValueError(f"Environment '{name}' already exists")

        yaml_path = f"environments/custom/{name}.yml"

        if clone_from:
            source_env = await EnvironmentService.get_environment(session, org_id, clone_from)
            if not source_env:
                raise ValueError(f"Source environment '{clone_from}' not found")
            # Read source YAML from GitOps
            repo = await GitOpsService.get_repo(session, org_id)
            if repo:
                yaml_content = await GitOpsService.get_file(org_id, repo.github_repo_name, source_env.yaml_path)
                # Update the name in YAML
                data = yaml.safe_load(yaml_content)
                data["name"] = name
                yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
            else:
                yaml_content = EnvironmentService._generate_minimal_yaml(name)
        else:
            yaml_content = EnvironmentService._generate_minimal_yaml(name)

        env = Environment(
            organization_id=org_id,
            name=name,
            env_type="custom_conda",
            yaml_path=yaml_path,
            is_default=False,
            description=description,
            created_by_user_id=user_id,
            jupyter_kernel_name=name,
            status="syncing",
        )
        session.add(env)
        await session.flush()

        # Commit YAML to GitOps
        repo = await GitOpsService.get_repo(session, org_id)
        if repo:
            commit_sha = await GitOpsService.commit_and_push(
                session,
                org_id,
                user_id,
                files={yaml_path: yaml_content},
                message=f"env: create custom environment {name}",
            )

            # Create change record for reconciliation
            change = EnvironmentChange(
                organization_id=org_id,
                environment_id=env.id,
                user_id=user_id,
                change_type="create",
                git_commit_sha=commit_sha,
                commit_message=f"Create custom environment {name}",
            )
            session.add(change)

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment",
            entity_id=env.id,
            action="create",
            details={"name": name, "clone_from": clone_from},
        )
        await session.flush()
        return env

    @staticmethod
    def _generate_minimal_yaml(name: str) -> str:
        data = {
            "name": name,
            "channels": ["conda-forge", "bioconda", "defaults"],
            "dependencies": ["python=3.11", "jupyterlab", "ipykernel"],
        }
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @staticmethod
    async def archive_environment(
        session: AsyncSession,
        org_id: int,
        user_id: int,
        env_name: str,
    ) -> None:
        env = await EnvironmentService.get_environment(session, org_id, env_name)
        if not env:
            raise ValueError(f"Environment '{env_name}' not found")
        if env.is_default:
            raise ValueError("Cannot archive a default environment")

        env.status = "archived"
        await session.flush()

        await log_action(
            session,
            user_id=user_id,
            entity_type="environment",
            entity_id=env.id,
            action="archive",
            details={"name": env_name},
        )

    @staticmethod
    async def sync_packages_from_yaml(
        session: AsyncSession,
        org_id: int,
        environment_id: int,
        yaml_content: str,
    ) -> None:
        """Parse YAML and sync environment_packages table."""
        result = await session.execute(select(Environment).where(Environment.id == environment_id))
        env = result.scalar_one_or_none()
        if not env:
            return

        if env.env_type in ("conda", "custom_conda"):
            packages = EnvironmentService._parse_conda_yaml(yaml_content)
        else:
            packages = EnvironmentService._parse_r_script(yaml_content)

        # Delete existing packages
        for pkg in list(env.packages):
            await session.delete(pkg)
        await session.flush()

        # Insert new packages
        for pkg in packages:
            ep = EnvironmentPackage(
                environment_id=environment_id,
                package_name=pkg["name"],
                version=pkg.get("version"),
                source=pkg["source"],
            )
            session.add(ep)

        env.last_synced_at = datetime.now(timezone.utc)
        await session.flush()

    @staticmethod
    def update_conda_yaml(yaml_content: str, package_name: str, version: str | None, source: str, action: str) -> str:
        """Update a conda YAML file: add, remove, or update a package."""
        data = yaml.safe_load(yaml_content)
        if not data:
            data = {"name": "env", "channels": ["conda-forge"], "dependencies": []}

        deps = data.get("dependencies", [])

        if source == "pip":
            # Handle pip packages nested under pip key
            pip_section = None
            pip_idx = None
            for i, dep in enumerate(deps):
                if isinstance(dep, dict) and "pip" in dep:
                    pip_section = dep["pip"]
                    pip_idx = i
                    break

            if action == "install":
                pkg_spec = f"{package_name}=={version}" if version else package_name
                if pip_section is None:
                    deps.append({"pip": [pkg_spec]})
                else:
                    # Remove existing entry
                    pip_section[:] = [
                        p for p in pip_section if not p.split("==")[0].split(">=")[0].strip() == package_name
                    ]
                    pip_section.append(pkg_spec)
            elif action == "remove":
                if pip_section:
                    pip_section[:] = [
                        p for p in pip_section if not p.split("==")[0].split(">=")[0].strip() == package_name
                    ]
                    if not pip_section and pip_idx is not None:
                        deps.pop(pip_idx)
            elif action == "update":
                if pip_section:
                    for i, p in enumerate(pip_section):
                        if p.split("==")[0].split(">=")[0].strip() == package_name:
                            pip_section[i] = f"{package_name}=={version}" if version else package_name
                            break
        else:
            # conda packages
            pkg_spec = f"{package_name}=={version}" if version else package_name

            if action == "install":
                # Remove existing entry if present
                deps[:] = [
                    d
                    for d in deps
                    if not (
                        isinstance(d, str) and d.split("==")[0].split(">=")[0].split("=")[0].strip() == package_name
                    )
                ]
                deps.append(pkg_spec)
            elif action == "remove":
                deps[:] = [
                    d
                    for d in deps
                    if not (
                        isinstance(d, str) and d.split("==")[0].split(">=")[0].split("=")[0].strip() == package_name
                    )
                ]
            elif action == "update":
                for i, d in enumerate(deps):
                    if isinstance(d, str) and d.split("==")[0].split(">=")[0].split("=")[0].strip() == package_name:
                        deps[i] = pkg_spec
                        break

        data["dependencies"] = deps
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
