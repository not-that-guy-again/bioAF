import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def searchable_data(session, admin_user):
    from app.models.experiment import Experiment
    from app.models.file import File
    from app.models.document import Document

    exp = Experiment(
        organization_id=admin_user.organization_id,
        name="Searchable RNA-seq Experiment",
        owner_user_id=admin_user.id,
        status="analysis",
        hypothesis="Test single-cell RNA sequencing of kidney tissue",
    )
    session.add(exp)
    await session.flush()

    f = File(
        organization_id=admin_user.organization_id,
        gcs_uri="gs://test-bucket/protocol.pdf",
        filename="kidney_protocol.pdf",
        size_bytes=50000,
        file_type="document",
        uploader_user_id=admin_user.id,
    )
    session.add(f)
    await session.flush()

    doc = Document(
        organization_id=admin_user.organization_id,
        file_id=f.id,
        title="Kidney Tissue Protocol",
        extracted_text="Protocol for processing kidney tissue samples for single-cell RNA sequencing.",
    )
    session.add(doc)
    await session.flush()
    await session.commit()
    return exp, doc


@pytest.mark.asyncio
async def test_unified_search(client, admin_token, searchable_data):
    resp = await client.get(
        "/api/search?query=kidney",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    # Should find at least the experiment or document
    types_found = {hit["entity_type"] for hit in data["hits"]}
    assert len(types_found) >= 1


@pytest.mark.asyncio
async def test_unified_search_empty_query(client, admin_token):
    resp = await client.get(
        "/api/search?query=",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_unified_search_no_results(client, admin_token):
    resp = await client.get(
        "/api/search?query=xyznonexistent",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
