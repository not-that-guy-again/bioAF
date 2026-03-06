import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def seeded_vocabularies(client, admin_token):
    """Seed some vocabulary values for testing."""
    values = [
        {"field_name": "molecule_type", "allowed_value": "total RNA", "is_default": True, "display_order": 1},
        {"field_name": "molecule_type", "allowed_value": "polyA RNA", "display_order": 2},
        {"field_name": "library_layout", "allowed_value": "paired", "is_default": True, "display_order": 1},
        {"field_name": "library_layout", "allowed_value": "single", "display_order": 2},
    ]
    for val in values:
        await client.post(
            "/api/vocabularies",
            json=val,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    return values


@pytest.mark.asyncio
async def test_list_vocabularies_for_field(client, admin_token, seeded_vocabularies):
    response = await client.get(
        "/api/vocabularies?field=molecule_type",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["field_name"] == "molecule_type"
    assert len(data["values"]) == 2
    assert data["values"][0]["value"] == "total RNA"


@pytest.mark.asyncio
async def test_list_vocabularies_empty_field(client, admin_token):
    response = await client.get(
        "/api/vocabularies?field=nonexistent_field",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["values"] == []


@pytest.mark.asyncio
async def test_list_vocabulary_fields(client, admin_token, seeded_vocabularies):
    response = await client.get(
        "/api/vocabularies/fields",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "molecule_type" in data["fields"]
    assert "library_layout" in data["fields"]


@pytest.mark.asyncio
async def test_create_vocabulary_as_admin(client, admin_token):
    response = await client.post(
        "/api/vocabularies",
        json={"field_name": "reference_genome", "allowed_value": "GRCh38", "display_order": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["field_name"] == "reference_genome"
    assert data["allowed_value"] == "GRCh38"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_vocabulary_as_viewer_forbidden(client, viewer_token):
    response = await client.post(
        "/api/vocabularies",
        json={"field_name": "reference_genome", "allowed_value": "GRCh37"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_duplicate_vocabulary_409(client, admin_token, seeded_vocabularies):
    response = await client.post(
        "/api/vocabularies",
        json={"field_name": "molecule_type", "allowed_value": "total RNA"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_vocabulary(client, admin_token, seeded_vocabularies):
    # Get existing
    resp = await client.get(
        "/api/vocabularies?field=molecule_type",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    vocab_id = resp.json()["values"][0]["id"]

    response = await client.patch(
        f"/api/vocabularies/{vocab_id}",
        json={"display_order": 99, "is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_order"] == 99
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_create_vocabulary_invalid_field_name(client, admin_token):
    response = await client.post(
        "/api/vocabularies",
        json={"field_name": "invalid_field", "allowed_value": "test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
