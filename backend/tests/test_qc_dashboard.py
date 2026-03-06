import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def experiment_with_run(session, admin_user):
    from app.models.experiment import Experiment
    from app.models.pipeline_run import PipelineRun

    exp = Experiment(
        organization_id=admin_user.organization_id,
        name="QC Test Experiment",
        owner_user_id=admin_user.id,
        status="processing",
    )
    session.add(exp)
    await session.flush()

    run = PipelineRun(
        organization_id=admin_user.organization_id,
        experiment_id=exp.id,
        submitted_by_user_id=admin_user.id,
        pipeline_name="nf-core/scrnaseq",
        status="completed",
        work_dir="/data/working/nextflow/run-qc",
    )
    session.add(run)
    await session.flush()
    await session.commit()
    return exp, run


@pytest_asyncio.fixture
async def qc_dashboard(session, admin_user, experiment_with_run):
    from app.models.qc_dashboard import QCDashboard
    from datetime import datetime, timezone

    exp, run = experiment_with_run
    d = QCDashboard(
        organization_id=admin_user.organization_id,
        pipeline_run_id=run.id,
        experiment_id=exp.id,
        metrics_json={
            "cell_count": 5000,
            "median_genes_per_cell": 2000,
            "median_umi_per_cell": 8000,
            "mito_pct_median": 3.5,
            "quality_rating": "good",
        },
        summary_text="Good quality dataset with 5000 cells.",
        plots_json=[],
        status="ready",
        generated_at=datetime.now(timezone.utc),
    )
    session.add(d)
    await session.flush()
    await session.commit()
    return d


@pytest.mark.asyncio
async def test_list_qc_dashboards(client, admin_token, qc_dashboard):
    resp = await client.get(
        "/api/qc-dashboards",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["quality_rating"] == "good"


@pytest.mark.asyncio
async def test_get_qc_dashboard(client, admin_token, qc_dashboard):
    resp = await client.get(
        f"/api/qc-dashboards/{qc_dashboard.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metrics"]["cell_count"] == 5000
    assert data["metrics"]["quality_rating"] == "good"
    assert "5000 cells" in data["summary_text"]


@pytest.mark.asyncio
async def test_get_qc_dashboard_by_run(client, admin_token, qc_dashboard, experiment_with_run):
    _, run = experiment_with_run
    resp = await client.get(
        f"/api/qc-dashboards/by-run/{run.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["pipeline_run_id"] == run.id


@pytest.mark.asyncio
async def test_get_qc_dashboard_not_found(client, admin_token):
    resp = await client.get(
        "/api/qc-dashboards/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# --- Service unit tests ---

def test_quality_rating_logic():
    from app.services.qc_dashboard_service import QCDashboardService

    metrics = {
        "cell_count": 10000,
        "median_genes_per_cell": 3000,
        "mito_pct_median": 2.0,
    }
    rating = QCDashboardService._compute_quality_rating(metrics)
    assert rating in ("excellent", "good", "acceptable", "concerning")


def test_quality_rating_high_mito():
    from app.services.qc_dashboard_service import QCDashboardService

    metrics = {
        "cell_count": 5000,
        "median_genes_per_cell": 2000,
        "mito_pct_median": 25.0,
    }
    rating = QCDashboardService._compute_quality_rating(metrics)
    # High mito should not be excellent
    assert rating in ("acceptable", "concerning")
