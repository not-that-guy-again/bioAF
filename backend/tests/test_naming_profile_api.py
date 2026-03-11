"""Tests for naming profile API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_profile(client, admin_token):
    response = await client.post(
        "/api/naming-profiles",
        json={
            "name": "CRO Standard",
            "description": "Standard CRO naming",
            "delimiter": "_",
            "strip_extension": True,
            "segments": [
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
            ],
            "project_code_mappings": {"PRJX": "1"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CRO Standard"
    assert data["status"] == "active"
    assert len(data["segments"]) == 2


@pytest.mark.asyncio
async def test_list_profiles(client, admin_token):
    # Create one first
    await client.post(
        "/api/naming-profiles",
        json={
            "name": "List Test",
            "segments": [{"position": 0, "field": "project_code", "required": True}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.get(
        "/api/naming-profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_get_profile(client, admin_token):
    resp = await client.post(
        "/api/naming-profiles",
        json={
            "name": "Get Test",
            "segments": [{"position": 0, "field": "project_code", "required": True}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    profile_id = resp.json()["id"]
    response = await client.get(
        f"/api/naming-profiles/{profile_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test"


@pytest.mark.asyncio
async def test_update_profile(client, admin_token):
    resp = await client.post(
        "/api/naming-profiles",
        json={
            "name": "Before Update",
            "segments": [{"position": 0, "field": "project_code", "required": True}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    profile_id = resp.json()["id"]
    response = await client.put(
        f"/api/naming-profiles/{profile_id}",
        json={"name": "After Update"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "After Update"


@pytest.mark.asyncio
async def test_delete_profile_soft_deactivates(client, admin_token):
    resp = await client.post(
        "/api/naming-profiles",
        json={
            "name": "To Deactivate",
            "segments": [{"position": 0, "field": "project_code", "required": True}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    profile_id = resp.json()["id"]
    response = await client.delete(
        f"/api/naming-profiles/{profile_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


@pytest.mark.asyncio
async def test_test_profiles_endpoint(client, admin_token):
    # Create a profile first
    await client.post(
        "/api/naming-profiles",
        json={
            "name": "Parser Test Profile",
            "segments": [
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/naming-profiles/test",
        json={"filenames": ["2026-03-10_ProjectX.txt", "unknown.txt"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["match_status"] == "matched"
    assert results[1]["match_status"] == "unmatched"


@pytest.mark.asyncio
async def test_viewer_denied_access(client, viewer_token):
    """Viewer role should be denied access to naming profiles."""
    response = await client.get(
        "/api/naming-profiles",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_with_invalid_data(client, admin_token):
    """Empty segments should fail validation."""
    response = await client.post(
        "/api/naming-profiles",
        json={"name": "Bad", "segments": []},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
