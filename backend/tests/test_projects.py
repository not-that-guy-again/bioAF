import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_create_project(client, admin_token, session):
    response = await client.post(
        "/api/projects",
        json={"name": "Cancer Genomics", "description": "Cancer research project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Cancer Genomics"
    assert data["experiment_count"] == 0

    # Verify audit
    result = await session.execute(text("SELECT * FROM audit_log WHERE entity_type = 'project' AND action = 'create'"))
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_list_projects(client, admin_token):
    await client.post(
        "/api/projects",
        json={"name": "Project A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/projects",
        json={"name": "Project B"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_update_project(client, admin_token, session):
    resp = await client.post(
        "/api/projects",
        json={"name": "Old Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = resp.json()["id"]

    response = await client.patch(
        f"/api/projects/{project_id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

    # Verify audit
    result = await session.execute(text("SELECT * FROM audit_log WHERE entity_type = 'project' AND action = 'update'"))
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_project_experiment_count(client, admin_token):
    resp = await client.post(
        "/api/projects",
        json={"name": "Count Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = resp.json()["id"]

    # Create experiment in this project
    await client.post(
        "/api/experiments",
        json={"name": "Proj Experiment", "project_id": project_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    projects = response.json()["projects"]
    matching = [p for p in projects if p["id"] == project_id]
    assert len(matching) == 1
    assert matching[0]["experiment_count"] >= 1


@pytest.mark.asyncio
async def test_viewer_cannot_create_project(client, viewer_token):
    response = await client.post(
        "/api/projects",
        json={"name": "Should Fail"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
