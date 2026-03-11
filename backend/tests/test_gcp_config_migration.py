"""Tests for migration 022 - GCP platform_config seed rows.

The test inserts the rows using the same SQL the migration uses
(INSERT ... ON CONFLICT DO NOTHING) and verifies all seven keys
exist with the correct default values.
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_migration_seeds_gcp_config_keys(session):
    """Migration 022 inserts 7 GCP config keys with correct defaults."""
    # Reproduce the migration SQL (ON CONFLICT DO NOTHING = idempotent)
    await session.execute(
        text("""
        INSERT INTO platform_config (key, value) VALUES
            ('gcp_project_id',              ''),
            ('gcp_region',                  'us-central1'),
            ('gcp_zone',                    'us-central1-a'),
            ('org_slug',                    ''),
            ('gcp_credentials_configured',  'false'),
            ('gcp_validation_status',       ''),
            ('gcp_credential_source',       'vm_default')
        ON CONFLICT (key) DO NOTHING
        """)
    )
    await session.commit()

    rows = (
        await session.execute(
            text(
                "SELECT key, value FROM platform_config "
                "WHERE key IN ("
                "  'gcp_project_id','gcp_region','gcp_zone','org_slug',"
                "  'gcp_credentials_configured','gcp_validation_status',"
                "  'gcp_credential_source'"
                ") ORDER BY key"
            )
        )
    ).fetchall()

    config = {r[0]: r[1] for r in rows}

    assert config["gcp_project_id"] == ""
    assert config["gcp_region"] == "us-central1"
    assert config["gcp_zone"] == "us-central1-a"
    assert config["org_slug"] == ""
    assert config["gcp_credentials_configured"] == "false"
    assert config["gcp_validation_status"] == ""
    assert config["gcp_credential_source"] == "vm_default"


@pytest.mark.asyncio
async def test_migration_is_idempotent(session):
    """Running the migration SQL twice does not fail or duplicate rows."""
    seed_sql = text("""
        INSERT INTO platform_config (key, value) VALUES
            ('gcp_project_id',              ''),
            ('gcp_region',                  'us-central1'),
            ('gcp_zone',                    'us-central1-a'),
            ('org_slug',                    ''),
            ('gcp_credentials_configured',  'false'),
            ('gcp_validation_status',       ''),
            ('gcp_credential_source',       'vm_default')
        ON CONFLICT (key) DO NOTHING
    """)
    await session.execute(seed_sql)
    await session.commit()
    # Run again - must not raise
    await session.execute(seed_sql)
    await session.commit()

    count = (
        await session.execute(
            text(
                "SELECT COUNT(*) FROM platform_config "
                "WHERE key LIKE 'gcp_%' OR key = 'org_slug'"
            )
        )
    ).scalar()

    assert count == 7
