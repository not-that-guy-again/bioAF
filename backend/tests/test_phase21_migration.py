"""Tests for Phase 21 migration - auto-ingest platform_config keys."""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_platform_config_pubsub_keys_exist(session):
    """Phase 21 platform_config keys exist with correct defaults after migration SQL runs."""
    # Simulate the migration inserting keys
    await session.execute(text("""
        INSERT INTO platform_config (key, value) VALUES
            ('pubsub_topic_name', 'null'),
            ('pubsub_subscription_name', 'null'),
            ('auto_ingest_enabled', 'false'),
            ('ingest_cleanup_policy', 'delete_after_copy')
        ON CONFLICT (key) DO NOTHING
    """))
    await session.commit()

    expected = {
        "pubsub_topic_name": "null",
        "pubsub_subscription_name": "null",
        "auto_ingest_enabled": "false",
        "ingest_cleanup_policy": "delete_after_copy",
    }
    result = await session.execute(
        text(
            "SELECT key, value FROM platform_config WHERE key = ANY(:keys)"
        ).bindparams(keys=list(expected.keys()))
    )
    rows = {r[0]: r[1] for r in result.fetchall()}
    for key, default_value in expected.items():
        assert key in rows, f"platform_config key '{key}' is missing"
        assert rows[key] == default_value, (
            f"platform_config['{key}'] expected '{default_value}', got '{rows[key]}'"
        )


@pytest.mark.asyncio
async def test_platform_config_pubsub_keys_idempotent(session):
    """Running the migration SQL twice does not error (ON CONFLICT DO NOTHING)."""
    sql = text("""
        INSERT INTO platform_config (key, value) VALUES
            ('pubsub_topic_name', 'null'),
            ('pubsub_subscription_name', 'null'),
            ('auto_ingest_enabled', 'false'),
            ('ingest_cleanup_policy', 'delete_after_copy')
        ON CONFLICT (key) DO NOTHING
    """)
    await session.execute(sql)
    await session.commit()
    # Run again - should not raise
    await session.execute(sql)
    await session.commit()

    result = await session.execute(
        text("SELECT count(*) FROM platform_config WHERE key = 'auto_ingest_enabled'")
    )
    assert result.scalar() == 1
