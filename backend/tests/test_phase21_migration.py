"""Tests for Phase 21 migration - auto-ingest platform_config keys."""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_platform_config_pubsub_keys_exist(session):
    """Phase 21 platform_config keys exist with correct defaults."""
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
