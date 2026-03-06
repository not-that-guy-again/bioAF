import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def h5ad_file(session, admin_user):
    from app.models.file import File

    f = File(
        organization_id=admin_user.organization_id,
        gcs_uri="gs://test-bucket/dataset.h5ad",
        filename="dataset.h5ad",
        size_bytes=100000,
        file_type="h5ad",
        uploader_user_id=admin_user.id,
    )
    session.add(f)
    await session.flush()
    await session.commit()
    return f


@pytest_asyncio.fixture
async def cellxgene_publication(session, admin_user, h5ad_file):
    from app.models.cellxgene_publication import CellxgenePublication
    from datetime import datetime, timezone

    pub = CellxgenePublication(
        organization_id=admin_user.organization_id,
        file_id=h5ad_file.id,
        dataset_name="Test Dataset",
        status="running",
        stable_url="http://cellxgene.example.com/test-dataset",
        published_by_user_id=admin_user.id,
        published_at=datetime.now(timezone.utc),
    )
    session.add(pub)
    await session.flush()
    await session.commit()
    return pub


@pytest.mark.asyncio
async def test_list_publications(client, admin_token, cellxgene_publication):
    resp = await client.get(
        "/api/cellxgene",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["dataset_name"] == "Test Dataset"


@pytest.mark.asyncio
async def test_get_publication(client, admin_token, cellxgene_publication):
    resp = await client.get(
        f"/api/cellxgene/{cellxgene_publication.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["dataset_name"] == "Test Dataset"
    assert resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_get_publication_not_found(client, admin_token):
    resp = await client.get(
        "/api/cellxgene/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_viewer_cannot_publish(client, viewer_token, h5ad_file):
    resp = await client.post(
        "/api/cellxgene/publish",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"file_id": h5ad_file.id, "dataset_name": "Viewer Dataset"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_viewer_cannot_unpublish(client, viewer_token, cellxgene_publication):
    resp = await client.delete(
        f"/api/cellxgene/{cellxgene_publication.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403
