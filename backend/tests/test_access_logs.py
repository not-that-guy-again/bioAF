import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_access_logs_empty(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/access-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["logs"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_access_logs_forbidden_for_viewer(client: AsyncClient, viewer_token: str):
    response = await client.get(
        "/api/access-logs",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_access_logs_with_data(client: AsyncClient, admin_token: str, admin_user, session):
    from app.services.access_log_service import AccessLogService

    await AccessLogService.log_access(
        session, admin_user.organization_id, admin_user.id,
        "file", "123", "download", {"filename": "data.csv"},
    )
    await AccessLogService.log_access(
        session, admin_user.organization_id, admin_user.id,
        "notebook", "456", "session", {"notebook_name": "analysis.ipynb"},
    )
    await session.commit()

    response = await client.get(
        "/api/access-logs",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_filter_access_logs_by_resource_type(client: AsyncClient, admin_token: str, admin_user, session):
    from app.services.access_log_service import AccessLogService

    await AccessLogService.log_access(
        session, admin_user.organization_id, admin_user.id,
        "file", "1", "download",
    )
    await AccessLogService.log_access(
        session, admin_user.organization_id, admin_user.id,
        "notebook", "2", "session",
    )
    await session.commit()

    response = await client.get(
        "/api/access-logs?resource_type=file",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    for log in response.json()["logs"]:
        assert log["resource_type"] == "file"
