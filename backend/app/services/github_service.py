"""GitHub App integration service.

Manages GitHub App credentials in platform_config and provides
repo operations (create, check existence, list branches) and
installation token generation for notebook git integration.
"""

import logging
import time

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("bioaf.github")

GITHUB_API_BASE = "https://api.github.com"

_GITHUB_CONFIG_KEYS = [
    "github_app_id",
    "github_app_installation_id",
    "github_org_name",
    "github_private_key_secret",
]


class GitHubService:
    @staticmethod
    async def _get_config(session: AsyncSession) -> dict[str, str]:
        result = await session.execute(
            text("SELECT key, value FROM platform_config WHERE key = ANY(:keys)"),
            {"keys": _GITHUB_CONFIG_KEYS},
        )
        return {row[0]: row[1] for row in result.fetchall()}

    @staticmethod
    async def _upsert_config(session: AsyncSession, key: str, value: str) -> None:
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": key, "v": value},
        )

    @staticmethod
    async def connect(
        session: AsyncSession,
        app_id: str,
        installation_id: str,
        org_name: str,
        private_key: str,
    ) -> dict:
        """Store GitHub App credentials in platform_config."""
        for key, value in [
            ("github_app_id", app_id),
            ("github_app_installation_id", installation_id),
            ("github_org_name", org_name),
            ("github_private_key_secret", private_key),
        ]:
            await GitHubService._upsert_config(session, key, value)

        logger.info("GitHub App connected for org %s", org_name)
        return {"status": "ok", "org_name": org_name}

    @staticmethod
    async def get_status(session: AsyncSession) -> dict:
        """Return GitHub connection status."""
        config = await GitHubService._get_config(session)
        app_id = config.get("github_app_id", "")
        org_name = config.get("github_org_name", "")
        installation_id = config.get("github_app_installation_id", "")

        connected = bool(app_id and org_name and installation_id)
        return {
            "connected": connected,
            "app_id": app_id if connected else None,
            "org_name": org_name if connected else None,
            "installation_id": installation_id if connected else None,
        }

    @staticmethod
    async def disconnect(session: AsyncSession) -> dict:
        """Remove GitHub App credentials from platform_config."""
        await session.execute(
            text("DELETE FROM platform_config WHERE key = ANY(:keys)"),
            {"keys": _GITHUB_CONFIG_KEYS},
        )
        logger.info("GitHub App disconnected")
        return {"status": "ok"}

    @staticmethod
    async def _get_installation_headers(session: AsyncSession) -> dict[str, str]:
        """Build headers using an installation access token."""
        token_data = await GitHubService.get_installation_token(session)
        return {
            "Authorization": f"token {token_data['token']}",
            "Accept": "application/vnd.github+json",
        }

    @staticmethod
    async def create_repo(session: AsyncSession, name: str) -> dict:
        """Create a private repo in the connected GitHub org."""
        config = await GitHubService._get_config(session)
        org_name = config.get("github_org_name", "")

        headers = await GitHubService._get_installation_headers(session)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_BASE}/orgs/{org_name}/repos",
                json={
                    "name": name,
                    "private": True,
                    "auto_init": True,
                    "description": f"bioAF notebook repository: {name}",
                },
                headers=headers,
            )

        if response.status_code not in (200, 201):
            logger.error("Failed to create repo %s: %s", name, response.text)
            raise ValueError(f"Failed to create GitHub repo: {response.status_code}")

        return response.json()

    @staticmethod
    async def repo_exists(session: AsyncSession, name: str) -> bool:
        """Check if a repo exists in the connected GitHub org."""
        config = await GitHubService._get_config(session)
        org_name = config.get("github_org_name", "")

        headers = await GitHubService._get_installation_headers(session)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{org_name}/{name}",
                headers=headers,
            )

        return response.status_code == 200

    @staticmethod
    async def get_clone_url(session: AsyncSession, name: str) -> str:
        """Return the SSH clone URL for a repo."""
        config = await GitHubService._get_config(session)
        org_name = config.get("github_org_name", "")
        return f"git@github.com:{org_name}/{name}.git"

    @staticmethod
    async def list_branches(session: AsyncSession, name: str) -> list[dict]:
        """List branches for a repo."""
        config = await GitHubService._get_config(session)
        org_name = config.get("github_org_name", "")

        headers = await GitHubService._get_installation_headers(session)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{org_name}/{name}/branches",
                headers=headers,
            )

        if response.status_code != 200:
            logger.warning("Failed to list branches for %s: %s", name, response.status_code)
            return []

        return response.json()

    @staticmethod
    def _generate_jwt(app_id: str, private_key: str) -> str:
        """Generate a JWT for GitHub App authentication."""
        import jwt

        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": app_id,
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    @staticmethod
    async def get_installation_token(session: AsyncSession) -> dict:
        """Generate a short-lived installation access token."""
        config = await GitHubService._get_config(session)
        app_id = config.get("github_app_id", "")
        installation_id = config.get("github_app_installation_id", "")
        private_key = config.get("github_private_key_secret", "")

        if not all([app_id, installation_id, private_key]):
            raise ValueError("GitHub App is not configured")

        jwt_token = GitHubService._generate_jwt(app_id, private_key)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )

        if response.status_code not in (200, 201):
            logger.error("Failed to get installation token: %s", response.text)
            raise ValueError(f"Failed to get installation token: {response.status_code}")

        return response.json()
