"""Tests for the infrastructure components and storage buckets API endpoints."""

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.adapters import registry


@pytest.fixture(autouse=True)
def init_adapters(monkeypatch):
    monkeypatch.setenv("BIOAF_COMPUTE_MODE", "local")
    registry.reset_registry()
    registry.initialize_adapters_sync("kubernetes")
    yield
    registry.reset_registry()


class TestComponentsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_k8s_components_when_kubernetes_stack(self, client, admin_token, session):
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES ('compute_stack', 'kubernetes') "
                "ON CONFLICT (key) DO UPDATE SET value = 'kubernetes'"
            )
        )
        await session.commit()

        response = await client.get(
            "/api/v1/infrastructure/components",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "compute_stack" in data
        assert data["compute_stack"] == "kubernetes"

        keys = [c["key"] for c in data["components"]]
        assert "k8s_pipeline_pool" in keys
        assert "k8s_interactive_pool" in keys

    @pytest.mark.asyncio
    async def test_slurm_listed_as_coming_soon_on_kubernetes(self, client, admin_token, session):
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES ('compute_stack', 'kubernetes') "
                "ON CONFLICT (key) DO UPDATE SET value = 'kubernetes'"
            )
        )
        await session.commit()

        response = await client.get(
            "/api/v1/infrastructure/components",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        slurm = next((c for c in data["components"] if c["key"] == "slurm"), None)
        assert slurm is not None
        assert slurm["status"] == "coming_soon"

        filestore = next((c for c in data["components"] if c["key"] == "filestore"), None)
        assert filestore is not None
        assert filestore["status"] == "coming_soon"

    @pytest.mark.asyncio
    async def test_response_includes_all_expected_categories(self, client, admin_token, session):
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES ('compute_stack', 'kubernetes') "
                "ON CONFLICT (key) DO UPDATE SET value = 'kubernetes'"
            )
        )
        await session.commit()

        response = await client.get(
            "/api/v1/infrastructure/components",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        categories = {c["category"] for c in data["components"]}
        assert "compute" in categories
        assert "pipeline_orchestration" in categories
        assert "analysis" in categories
        assert "visualization" in categories
        assert "search" in categories

    @pytest.mark.asyncio
    async def test_requires_admin_or_comp_bio_role(self, client, viewer_token):
        response = await client.get(
            "/api/v1/infrastructure/components",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_defaults_to_kubernetes_when_not_configured(self, client, admin_token):
        response = await client.get(
            "/api/v1/infrastructure/components",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["compute_stack"] == "kubernetes"
        keys = [c["key"] for c in data["components"]]
        assert "k8s_pipeline_pool" in keys


class TestStorageBucketsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_five_buckets(self, client, admin_token):
        response = await client.get(
            "/api/v1/infrastructure/storage/buckets",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "buckets" in data
        assert len(data["buckets"]) == 5

    @pytest.mark.asyncio
    async def test_ingest_bucket_has_is_ingest_true(self, client, admin_token):
        response = await client.get(
            "/api/v1/infrastructure/storage/buckets",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        ingest = next((b for b in data["buckets"] if b["is_ingest"]), None)
        assert ingest is not None
        assert "ingest" in ingest["name"]

    @pytest.mark.asyncio
    async def test_bucket_names_include_org_slug(self, client, admin_token):
        response = await client.get(
            "/api/v1/infrastructure/storage/buckets",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # All bucket names should follow the bioaf-<type>-<org> pattern
        for bucket in data["buckets"]:
            assert bucket["name"].startswith("bioaf-")

    @pytest.mark.asyncio
    async def test_each_bucket_has_required_fields(self, client, admin_token):
        response = await client.get(
            "/api/v1/infrastructure/storage/buckets",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()

        for bucket in data["buckets"]:
            assert "name" in bucket
            assert "purpose" in bucket
            assert "is_ingest" in bucket
            assert "size_gb" in bucket
            assert "object_count" in bucket

    @pytest.mark.asyncio
    async def test_requires_admin_or_comp_bio_role(self, client, viewer_token):
        response = await client.get(
            "/api/v1/infrastructure/storage/buckets",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert response.status_code == 403
