import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_bootstrap_status_no_org(client: AsyncClient):
    response = await client.get("/api/bootstrap/status")
    assert response.status_code == 200
    assert response.json()["setup_complete"] is False


@pytest.mark.asyncio
async def test_create_admin(client: AsyncClient):
    response = await client.post("/api/bootstrap/create-admin", json={
        "email": "newadmin@test.com",
        "password": "securepassword123",
        "name": "Test Admin",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["message"] == "Admin account created"


@pytest.mark.asyncio
async def test_create_admin_twice_fails(client: AsyncClient):
    # First call
    await client.post("/api/bootstrap/create-admin", json={
        "email": "admin1@test.com",
        "password": "password123",
    })

    # Second call should fail
    response = await client.post("/api/bootstrap/create-admin", json={
        "email": "admin2@test.com",
        "password": "password123",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_full_bootstrap_flow(client: AsyncClient):
    # Step 1: Create admin
    resp = await client.post("/api/bootstrap/create-admin", json={
        "email": "admin@bootstrap.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Configure org
    resp = await client.post("/api/bootstrap/configure-org", json={
        "org_name": "Test Biotech",
    }, headers=headers)
    assert resp.status_code == 200

    # Step 3: Skip SMTP (proceed without configuring)

    # Step 4: Complete setup
    resp = await client.post("/api/bootstrap/complete", headers=headers)
    assert resp.status_code == 200

    # Verify setup is complete
    resp = await client.get("/api/bootstrap/status")
    assert resp.json()["setup_complete"] is True


@pytest.mark.asyncio
async def test_bootstrap_requires_admin_role(client: AsyncClient, viewer_token: str):
    response = await client.post("/api/bootstrap/configure-org", json={
        "org_name": "Test",
    }, headers={"Authorization": f"Bearer {viewer_token}"})
    assert response.status_code == 403
