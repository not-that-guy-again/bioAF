"""Tests for auto-ingest API endpoints (Phase 21).

Tests 16-22: Admin role, storage deployed, enable/disable,
status, audit log, cleanup policy.
"""

import pytest
from sqlalchemy import text


async def _seed_config(session, overrides=None):
    defaults = {
        "storage_deployed": "true",
        "ingest_bucket_name": "bioaf-ingest-testorg",
        "raw_bucket_name": "bioaf-raw-testorg",
        "auto_ingest_enabled": "false",
        "ingest_cleanup_policy": "delete_after_copy",
        "pubsub_topic_name": "bioaf-ingest-events-testorg",
        "pubsub_subscription_name": "bioaf-ingest-worker-testorg",
    }
    if overrides:
        defaults.update(overrides)
    for key, value in defaults.items():
        await session.execute(
            text(
                "INSERT INTO platform_config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ).bindparams(k=key, v=value)
        )
    await session.commit()


@pytest.mark.asyncio
async def test_enable_auto_ingest_requires_admin(client, session, admin_user, viewer_token):
    """Enable auto-ingest requires admin role."""
    await _seed_config(session)
    resp = await client.post(
        "/api/v1/settings/auto-ingest",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_enable_auto_ingest_requires_storage_deployed(client, session, admin_user, admin_token):
    """Enable fails when storage_deployed=false."""
    await _seed_config(session, {"storage_deployed": "false"})
    resp = await client.post(
        "/api/v1/settings/auto-ingest",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "storage" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_enable_auto_ingest_sets_config(client, session, admin_user, admin_token):
    """Enable sets auto_ingest_enabled=true in platform_config."""
    await _seed_config(session)
    resp = await client.post(
        "/api/v1/settings/auto-ingest",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    row = await session.execute(
        text("SELECT value FROM platform_config WHERE key = 'auto_ingest_enabled'")
    )
    assert row.scalar() == "true"


@pytest.mark.asyncio
async def test_disable_auto_ingest_sets_config(client, session, admin_user, admin_token):
    """Disable sets auto_ingest_enabled=false in platform_config."""
    await _seed_config(session, {"auto_ingest_enabled": "true"})
    resp = await client.post(
        "/api/v1/settings/auto-ingest",
        json={"enabled": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    row = await session.execute(
        text("SELECT value FROM platform_config WHERE key = 'auto_ingest_enabled'")
    )
    assert row.scalar() == "false"


@pytest.mark.asyncio
async def test_get_auto_ingest_status(client, session, admin_user, admin_token):
    """GET returns current auto-ingest status including message counts."""
    await _seed_config(session, {"auto_ingest_enabled": "true"})
    resp = await client.get(
        "/api/v1/settings/auto-ingest",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["cleanup_policy"] == "delete_after_copy"
    assert "messages_processed_24h" in data
    assert "messages_failed_24h" in data
    assert data["pubsub_topic"] == "bioaf-ingest-events-testorg"
    assert data["pubsub_subscription"] == "bioaf-ingest-worker-testorg"


@pytest.mark.asyncio
async def test_enable_writes_audit_log(client, session, admin_user, admin_token):
    """Enable auto-ingest writes an audit log entry."""
    await _seed_config(session)
    await client.post(
        "/api/v1/settings/auto-ingest",
        json={"enabled": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    result = await session.execute(
        text(
            "SELECT action FROM audit_log WHERE entity_type = 'auto_ingest' "
            "ORDER BY timestamp DESC LIMIT 1"
        )
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] == "enable"


@pytest.mark.asyncio
async def test_cleanup_policy_update(client, session, admin_user, admin_token):
    """Changing cleanup policy updates platform_config."""
    await _seed_config(session)
    resp = await client.post(
        "/api/v1/settings/auto-ingest",
        json={"enabled": True, "cleanup_policy": "retain_7d"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    row = await session.execute(
        text("SELECT value FROM platform_config WHERE key = 'ingest_cleanup_policy'")
    )
    assert row.scalar() == "retain_7d"
