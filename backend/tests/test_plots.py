import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def experiment_for_plots(session, admin_user):
    from app.models.experiment import Experiment

    exp = Experiment(
        organization_id=admin_user.organization_id,
        name="Plot Test Experiment",
        owner_user_id=admin_user.id,
        status="analysis",
    )
    session.add(exp)
    await session.flush()
    await session.commit()
    return exp


@pytest_asyncio.fixture
async def sample_plot(session, admin_user, experiment_for_plots):
    from app.models.file import File
    from app.models.plot_archive_entry import PlotArchiveEntry
    from datetime import datetime, timezone

    f = File(
        organization_id=admin_user.organization_id,
        gcs_uri="gs://test-bucket/plots/umap.png",
        filename="umap.png",
        size_bytes=25000,
        file_type="image",
        uploader_user_id=admin_user.id,
    )
    session.add(f)
    await session.flush()

    plot = PlotArchiveEntry(
        organization_id=admin_user.organization_id,
        file_id=f.id,
        title="UMAP Clustering",
        experiment_id=experiment_for_plots.id,
        tags_json=["umap", "clustering"],
        indexed_at=datetime.now(timezone.utc),
    )
    session.add(plot)
    await session.flush()
    await session.commit()
    return plot


@pytest.mark.asyncio
async def test_search_plots(client, admin_token, sample_plot):
    resp = await client.get(
        "/api/plots",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(p["title"] == "UMAP Clustering" for p in data["plots"])


@pytest.mark.asyncio
async def test_search_plots_with_query(client, admin_token, sample_plot):
    resp = await client.get(
        "/api/plots?query=umap",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_plot(client, admin_token, sample_plot):
    resp = await client.get(
        f"/api/plots/{sample_plot.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "UMAP Clustering"
    assert "umap" in resp.json()["tags"]


@pytest.mark.asyncio
async def test_update_plot(client, admin_token, sample_plot):
    resp = await client.patch(
        f"/api/plots/{sample_plot.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Updated UMAP", "tags": ["umap", "updated"]},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated UMAP"


@pytest.mark.asyncio
async def test_get_thumbnail(client, admin_token, sample_plot):
    resp = await client.get(
        f"/api/plots/{sample_plot.id}/thumbnail",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    # Should return the file's GCS URI as fallback since no thumbnail_gcs_uri set
    assert resp.json()["thumbnail_url"] is not None
