import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_components(client: AsyncClient, admin_token: str):
    response = await client.get("/api/components", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["components"]) > 0
    keys = [c["key"] for c in data["components"]]
    assert "slurm" in keys
    assert "jupyter" in keys
    assert "cellxgene" in keys


@pytest.mark.asyncio
async def test_get_component_detail(client: AsyncClient, admin_token: str):
    response = await client.get("/api/components/slurm", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "slurm"
    assert data["name"] == "SLURM HPC Cluster"
    assert data["dependencies"] == []


@pytest.mark.asyncio
async def test_get_nonexistent_component(client: AsyncClient, admin_token: str):
    response = await client.get("/api/components/nonexistent", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enable_component_missing_deps(client: AsyncClient, admin_token: str, session):
    """JupyterHub requires SLURM and Filestore — should fail without them."""
    # Initialize component states
    from app.services.component_service import ComponentService
    await ComponentService.initialize_states(session)
    await session.commit()

    response = await client.post("/api/components/jupyter/enable", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert response.status_code == 400
    assert "dependencies" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_viewer_can_list_components(client: AsyncClient, viewer_token: str):
    response = await client.get("/api/components", headers={
        "Authorization": f"Bearer {viewer_token}",
    })
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_enable_components(client: AsyncClient, viewer_token: str):
    response = await client.post("/api/components/cellxgene/enable", headers={
        "Authorization": f"Bearer {viewer_token}",
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_component_dependencies_enforced(client: AsyncClient, admin_token: str):
    # Filestore depends on SLURM
    response = await client.get("/api/components/filestore", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    data = response.json()
    assert "slurm" in data["dependencies"]
