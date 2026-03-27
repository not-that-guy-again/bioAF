"""Tests for GitHub App integration service and API endpoints."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy import text


@pytest_asyncio.fixture
async def github_credentials(session, admin_user):
    """Seed platform_config with GitHub App credentials for testing."""
    for key, value in [
        ("github_app_id", "12345"),
        ("github_app_installation_id", "67890"),
        ("github_org_name", "test-org"),
        ("github_private_key_secret", "-----BEGIN RSA PRIVATE KEY-----\nfake-key\n-----END RSA PRIVATE KEY-----"),
    ]:
        await session.execute(
            text("INSERT INTO platform_config (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value = :v"),
            {"k": key, "v": value},
        )
    await session.commit()


# -- Service tests --


class TestGitHubServiceConnect:
    @pytest.mark.asyncio
    async def test_connect_stores_credentials(self, session, admin_user):
        from app.services.github_service import GitHubService

        await GitHubService.connect(
            session,
            app_id="12345",
            installation_id="67890",
            org_name="test-org",
            private_key="-----BEGIN RSA PRIVATE KEY-----\nfake-key\n-----END RSA PRIVATE KEY-----",
        )
        await session.commit()

        result = await session.execute(text("SELECT value FROM platform_config WHERE key = 'github_app_id'"))
        assert result.scalar() == "12345"

        result = await session.execute(text("SELECT value FROM platform_config WHERE key = 'github_org_name'"))
        assert result.scalar() == "test-org"

    @pytest.mark.asyncio
    async def test_get_status_connected(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        status = await GitHubService.get_status(session)
        assert status["connected"] is True
        assert status["org_name"] == "test-org"
        assert status["app_id"] == "12345"

    @pytest.mark.asyncio
    async def test_get_status_disconnected(self, session, admin_user):
        from app.services.github_service import GitHubService

        status = await GitHubService.get_status(session)
        assert status["connected"] is False

    @pytest.mark.asyncio
    async def test_disconnect_removes_credentials(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        await GitHubService.disconnect(session)
        await session.commit()

        status = await GitHubService.get_status(session)
        assert status["connected"] is False


class TestGitHubServiceRepoOps:
    @pytest.mark.asyncio
    async def test_create_repo(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "name": "EXP-001-notebooks",
            "full_name": "test-org/EXP-001-notebooks",
            "private": True,
            "clone_url": "https://github.com/test-org/EXP-001-notebooks.git",
            "ssh_url": "git@github.com:test-org/EXP-001-notebooks.git",
        }

        mock_token = AsyncMock(return_value={"Authorization": "token fake", "Accept": "application/vnd.github+json"})
        with patch.object(GitHubService, "_get_installation_headers", mock_token):
            with patch("app.services.github_service.httpx") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.post.return_value = mock_response

                result = await GitHubService.create_repo(session, "EXP-001-notebooks")

        assert result["name"] == "EXP-001-notebooks"
        assert result["private"] is True

    @pytest.mark.asyncio
    async def test_repo_exists_true(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        mock_token = AsyncMock(return_value={"Authorization": "token fake", "Accept": "application/vnd.github+json"})
        with patch.object(GitHubService, "_get_installation_headers", mock_token):
            mock_response = MagicMock()
            mock_response.status_code = 200

            with patch("app.services.github_service.httpx") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.get.return_value = mock_response

                exists = await GitHubService.repo_exists(session, "EXP-001-notebooks")

        assert exists is True

    @pytest.mark.asyncio
    async def test_repo_exists_false(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        mock_token = AsyncMock(return_value={"Authorization": "token fake", "Accept": "application/vnd.github+json"})
        with patch.object(GitHubService, "_get_installation_headers", mock_token):
            mock_response = MagicMock()
            mock_response.status_code = 404

            with patch("app.services.github_service.httpx") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.get.return_value = mock_response

                exists = await GitHubService.repo_exists(session, "nonexistent-repo")

        assert exists is False

    @pytest.mark.asyncio
    async def test_get_clone_url(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        url = await GitHubService.get_clone_url(session, "EXP-001-notebooks")
        assert url == "git@github.com:test-org/EXP-001-notebooks.git"

    @pytest.mark.asyncio
    async def test_list_branches(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "main"},
            {"name": "session/42-alice-2026-03-27"},
        ]

        mock_token = AsyncMock(return_value={"Authorization": "token fake", "Accept": "application/vnd.github+json"})
        with patch.object(GitHubService, "_get_installation_headers", mock_token):
            with patch("app.services.github_service.httpx") as mock_httpx:
                mock_client = AsyncMock()
                mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.get.return_value = mock_response

                branches = await GitHubService.list_branches(session, "EXP-001-notebooks")

        assert len(branches) == 2
        assert branches[0]["name"] == "main"


class TestGitHubServiceInstallationToken:
    @pytest.mark.asyncio
    async def test_get_installation_token(self, session, admin_user, github_credentials):
        from app.services.github_service import GitHubService

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "token": "ghs_fake_installation_token",
            "expires_at": "2026-03-27T12:00:00Z",
        }

        with patch("app.services.github_service.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value = mock_response

            with patch("app.services.github_service.GitHubService._generate_jwt", return_value="fake-jwt"):
                token_data = await GitHubService.get_installation_token(session)

        assert token_data["token"] == "ghs_fake_installation_token"


# -- API endpoint tests --


class TestGitHubSettingsAPI:
    @pytest.mark.asyncio
    async def test_connect_endpoint(self, client: AsyncClient, admin_token: str):
        response = await client.post(
            "/api/v1/settings/github/connect",
            json={
                "app_id": "12345",
                "installation_id": "67890",
                "org_name": "test-org",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_status_endpoint_disconnected(self, client: AsyncClient, admin_token: str):
        response = await client.get(
            "/api/v1/settings/github/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False

    @pytest.mark.asyncio
    async def test_status_endpoint_connected(self, client: AsyncClient, admin_token: str):
        # Connect first
        await client.post(
            "/api/v1/settings/github/connect",
            json={
                "app_id": "12345",
                "installation_id": "67890",
                "org_name": "test-org",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = await client.get(
            "/api/v1/settings/github/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["org_name"] == "test-org"

    @pytest.mark.asyncio
    async def test_disconnect_endpoint(self, client: AsyncClient, admin_token: str):
        # Connect first
        await client.post(
            "/api/v1/settings/github/connect",
            json={
                "app_id": "12345",
                "installation_id": "67890",
                "org_name": "test-org",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = await client.delete(
            "/api/v1/settings/github/disconnect",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200

        # Verify disconnected
        status_resp = await client.get(
            "/api/v1/settings/github/status",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert status_resp.json()["connected"] is False

    @pytest.mark.asyncio
    async def test_connect_requires_admin(self, client: AsyncClient, viewer_token: str):
        response = await client.post(
            "/api/v1/settings/github/connect",
            json={
                "app_id": "12345",
                "installation_id": "67890",
                "org_name": "test-org",
                "private_key": "fake",
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403
