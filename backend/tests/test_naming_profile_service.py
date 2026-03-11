"""Tests for NamingProfileService CRUD operations."""

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.schemas.naming_profile import NamingProfileCreate, NamingProfileUpdate, SegmentDefinition
from app.services.naming_profile_service import NamingProfileService


@pytest_asyncio.fixture
async def org_user_ids(client, admin_token, session):
    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()
    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user = result.fetchone()
    return org.id, user.id


@pytest_asyncio.fixture
async def sample_profile(session, org_user_ids):
    org_id, user_id = org_user_ids
    data = NamingProfileCreate(
        name="CRO Standard",
        description="Standard CRO naming",
        segments=[
            SegmentDefinition(position=0, field="date", format="YYYY-MM-DD", required=True),
            SegmentDefinition(position=1, field="project_code", required=True),
        ],
        project_code_mappings={"PRJX": "1"},
    )
    profile = await NamingProfileService.create_profile(session, org_id, user_id, data)
    await session.commit()
    return profile


@pytest.mark.asyncio
async def test_create_profile(client, admin_token, session, org_user_ids):
    org_id, user_id = org_user_ids
    data = NamingProfileCreate(
        name="Test Profile",
        segments=[SegmentDefinition(position=0, field="project_code", required=True)],
    )
    profile = await NamingProfileService.create_profile(session, org_id, user_id, data)
    await session.commit()
    assert profile.id is not None
    assert profile.name == "Test Profile"
    assert profile.status == "active"

    # Check audit log
    result = await session.execute(
        text("SELECT * FROM audit_log WHERE entity_type = 'naming_profile' AND action = 'create'")
    )
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_get_profile(client, admin_token, session, sample_profile):
    profile = await NamingProfileService.get_profile(session, sample_profile.id)
    assert profile is not None
    assert profile.name == "CRO Standard"


@pytest.mark.asyncio
async def test_list_profiles(client, admin_token, session, org_user_ids, sample_profile):
    org_id, _ = org_user_ids
    profiles = await NamingProfileService.list_profiles(session, org_id)
    assert len(profiles) >= 1


@pytest.mark.asyncio
async def test_list_profiles_with_status_filter(client, admin_token, session, org_user_ids, sample_profile):
    org_id, user_id = org_user_ids
    # Deactivate the profile
    await NamingProfileService.deactivate_profile(session, sample_profile.id, user_id)
    await session.commit()

    active = await NamingProfileService.list_profiles(session, org_id, status_filter="active")
    inactive = await NamingProfileService.list_profiles(session, org_id, status_filter="inactive")
    assert all(p.status == "active" for p in active)
    assert all(p.status == "inactive" for p in inactive)
    assert len(inactive) >= 1


@pytest.mark.asyncio
async def test_update_profile(client, admin_token, session, org_user_ids, sample_profile):
    _, user_id = org_user_ids
    data = NamingProfileUpdate(name="Updated Name", delimiter="-")
    updated = await NamingProfileService.update_profile(session, sample_profile.id, user_id, data)
    await session.commit()
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.delimiter == "-"


@pytest.mark.asyncio
async def test_deactivate_profile(client, admin_token, session, org_user_ids, sample_profile):
    _, user_id = org_user_ids
    deactivated = await NamingProfileService.deactivate_profile(session, sample_profile.id, user_id)
    await session.commit()
    assert deactivated is not None
    assert deactivated.status == "inactive"

    # Check audit log
    result = await session.execute(
        text("SELECT * FROM audit_log WHERE entity_type = 'naming_profile' AND action = 'deactivate'")
    )
    assert result.fetchone() is not None


@pytest.mark.asyncio
async def test_match_statistics_empty(client, admin_token, session, sample_profile):
    count = await NamingProfileService.get_match_statistics(session, sample_profile.id)
    assert count == 0


@pytest.mark.asyncio
async def test_test_profiles(client, admin_token, session, org_user_ids, sample_profile):
    org_id, _ = org_user_ids
    results = await NamingProfileService.test_profiles(session, org_id, ["2026-03-10_ProjectX.txt", "unknown_file.txt"])
    assert len(results) == 2
    # First file should match the sample_profile
    assert results[0]["match_status"] == "matched"
    assert results[0]["matched_profile_name"] == "CRO Standard"
    # Second file won't match (wrong segment count)
    assert results[1]["match_status"] == "unmatched"
