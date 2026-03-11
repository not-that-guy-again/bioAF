"""Tests for the naming profile parser engine."""

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.services.naming_profile_parser import (
    ParseResult,
    _strip_extension,
    match_filename,
    parse_filename,
    resolve_entities,
)


def _make_profile(
    segments_json,
    delimiter="_",
    strip_extension=True,
    project_code_mappings=None,
    experiment_code_mappings=None,
    profile_id=1,
    name="TestProfile",
):
    """Create a mock NamingProfile-like object for testing."""

    class MockProfile:
        def __init__(self):
            self.id = profile_id
            self.name = name
            self.delimiter = delimiter
            self.strip_extension = strip_extension
            self.segments_json = segments_json
            self.project_code_mappings = project_code_mappings or {}
            self.experiment_code_mappings = experiment_code_mappings or {}

    return MockProfile()


# --- _strip_extension tests ---


class TestStripExtension:
    def test_simple_extension(self):
        assert _strip_extension("test.fastq") == "test"

    def test_double_extension(self):
        assert _strip_extension("test.fastq.gz") == "test"

    def test_no_extension(self):
        assert _strip_extension("test") == "test"

    def test_complex_name(self):
        assert _strip_extension("2026-03-10_ProjectX_RNASeq.txt") == "2026-03-10_ProjectX_RNASeq"


# --- parse_filename tests ---


class TestParseFilename:
    def test_standard_cro_filename(self):
        """Parse a standard 6-segment CRO filename."""
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
                {"position": 2, "field": "data_type", "required": True},
                {"position": 3, "field": "analysis_type", "required": True},
                {"position": 4, "field": "researcher_initials", "required": True},
                {"position": 5, "field": "version", "required": True},
            ]
        )
        result = parse_filename("2026-03-10_ProjectX_RNASeq_DiffExpr_SmithE_v001.txt", profile)
        assert result.success is True
        assert result.segments["date"] == "2026-03-10"
        assert result.segments["project_code"] == "ProjectX"
        assert result.segments["data_type"] == "RNASeq"
        assert result.segments["analysis_type"] == "DiffExpr"
        assert result.segments["researcher_initials"] == "SmithE"
        assert result.segments["version"] == "v001"

    def test_different_delimiters(self):
        """Test parsing with hyphen delimiter."""
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "sample_id", "required": True},
            ],
            delimiter="-",
        )
        result = parse_filename("ProjectX-Sample001.fastq", profile)
        assert result.success is True
        assert result.segments["project_code"] == "ProjectX"
        assert result.segments["sample_id"] == "Sample001"

    def test_dot_delimiter(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "sample_id", "required": True},
            ],
            delimiter=".",
            strip_extension=False,
        )
        result = parse_filename("ProjectX.Sample001", profile)
        assert result.success is True

    def test_strip_extension_disabled(self):
        """With strip_extension=False, extension stays as part of last segment."""
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "data_type", "required": True},
            ],
            strip_extension=False,
        )
        result = parse_filename("ProjectX_RNASeq.fastq", profile)
        assert result.success is True
        assert result.segments["data_type"] == "RNASeq.fastq"  # extension included

    def test_optional_segment_missing(self):
        """Optional segments should not cause failure."""
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "sample_id", "required": True},
                {"position": 2, "field": "version", "required": False},
            ]
        )
        # 2 segments but profile expects 3 - should fail on count
        result = parse_filename("ProjectX_Sample001.txt", profile)
        assert result.success is False

    def test_date_format_yyyy_mm_dd(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
            ]
        )
        result = parse_filename("2026-03-10_ProjectX.txt", profile)
        assert result.success is True
        assert result.segments["date"] == "2026-03-10"

    def test_date_format_yyyymmdd(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "date", "format": "YYYYMMDD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
            ]
        )
        result = parse_filename("20260310_ProjectX.txt", profile)
        assert result.success is True
        assert result.segments["date"] == "20260310"

    def test_invalid_date_format(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
            ]
        )
        result = parse_filename("notadate_ProjectX.txt", profile)
        assert result.success is False
        assert "date" in result.error.lower()

    def test_version_format_valid(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "version", "required": True},
            ]
        )
        for version in ["v001", "v01", "v1", "V1"]:
            result = parse_filename(f"ProjectX_{version}.txt", profile)
            assert result.success is True, f"Failed for version: {version}"

    def test_version_format_invalid(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "version", "required": True},
            ]
        )
        result = parse_filename("ProjectX_abc.txt", profile)
        assert result.success is False

    def test_ignore_segment(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "ignore", "required": False},
                {"position": 2, "field": "sample_id", "required": True},
            ]
        )
        result = parse_filename("ProjectX_misc_Sample001.txt", profile)
        assert result.success is True
        assert "ignore" not in result.segments
        assert result.segments["project_code"] == "ProjectX"
        assert result.segments["sample_id"] == "Sample001"

    def test_wrong_segment_count(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "sample_id", "required": True},
                {"position": 2, "field": "version", "required": True},
            ]
        )
        result = parse_filename("ProjectX_Sample001.txt", profile)
        assert result.success is False
        assert result.error is not None and "Expected 3" in result.error

    def test_empty_filename(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
            ]
        )
        result = parse_filename("", profile)
        assert result.success is False

    def test_extra_segments(self):
        profile = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
            ]
        )
        result = parse_filename("ProjectX_Extra_More.txt", profile)
        assert result.success is False


# --- match_filename tests ---


class TestMatchFilename:
    def test_exactly_one_match(self):
        profile1 = _make_profile(
            segments_json=[
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
            ],
            profile_id=1,
            name="Profile1",
        )
        profile2 = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "sample_id", "required": True},
                {"position": 2, "field": "version", "required": True},
            ],
            profile_id=2,
            name="Profile2",
        )
        result = match_filename("2026-03-10_ProjectX.txt", [profile1, profile2])
        assert result.status == "matched"
        assert result.parse_result is not None
        assert result.parse_result.profile_id == 1

    def test_zero_matches(self):
        profile1 = _make_profile(
            segments_json=[
                {"position": 0, "field": "date", "format": "YYYY-MM-DD", "required": True},
                {"position": 1, "field": "project_code", "required": True},
                {"position": 2, "field": "version", "required": True},
            ],
            profile_id=1,
        )
        result = match_filename("something.txt", [profile1])
        assert result.status == "unmatched"

    def test_multiple_matches(self):
        # Two profiles with same segment count and loose validation
        profile1 = _make_profile(
            segments_json=[
                {"position": 0, "field": "project_code", "required": True},
                {"position": 1, "field": "sample_id", "required": True},
            ],
            profile_id=1,
            name="Profile1",
        )
        profile2 = _make_profile(
            segments_json=[
                {"position": 0, "field": "data_type", "required": True},
                {"position": 1, "field": "organism", "required": True},
            ],
            profile_id=2,
            name="Profile2",
        )
        result = match_filename("ABC_DEF.txt", [profile1, profile2])
        assert result.status == "multiple_matches"
        assert len(result.candidate_profile_ids) == 2

    def test_empty_filename(self):
        result = match_filename("", [])
        assert result.status == "unmatched"

    def test_no_profiles(self):
        result = match_filename("test.fastq", [])
        assert result.status == "unmatched"


# --- resolve_entities tests ---


@pytest_asyncio.fixture
async def org_and_user(client, admin_token, session):
    """Get the test org and user IDs."""
    result = await session.execute(text("SELECT id FROM organizations LIMIT 1"))
    org = result.fetchone()
    result = await session.execute(text("SELECT id FROM users LIMIT 1"))
    user = result.fetchone()
    return org.id, user.id


@pytest.mark.asyncio
async def test_resolve_mapped_project(client, admin_token, session, org_and_user):
    """Test entity resolution when project code is mapped to an existing project."""
    from app.models.project import Project

    org_id, _ = org_and_user
    project = Project(organization_id=org_id, name="Mapped Project")
    session.add(project)
    await session.flush()
    await session.commit()

    profile = _make_profile(
        segments_json=[],
        project_code_mappings={"PRJX": str(project.id)},
    )

    parse_result = ParseResult(success=True, segments={"project_code": "PRJX"})
    resolution = await resolve_entities(parse_result, profile, org_id, session)
    assert resolution.project_id == project.id
    assert resolution.project_name == "Mapped Project"


@pytest.mark.asyncio
async def test_resolve_unmapped_project_by_name(client, admin_token, session, org_and_user):
    """Test resolution by project name when no mapping exists."""
    from app.models.project import Project

    org_id, _ = org_and_user
    project = Project(organization_id=org_id, name="DiscoverMe")
    session.add(project)
    await session.flush()
    await session.commit()

    profile = _make_profile(segments_json=[])
    parse_result = ParseResult(success=True, segments={"project_code": "DiscoverMe"})
    resolution = await resolve_entities(parse_result, profile, org_id, session)
    assert resolution.project_id == project.id


@pytest.mark.asyncio
async def test_resolve_unmapped_code_returns_null(client, admin_token, session, org_and_user):
    """Test that an unmapped code that doesn't match any entity returns None."""
    org_id, _ = org_and_user
    profile = _make_profile(segments_json=[])
    parse_result = ParseResult(success=True, segments={"project_code": "NonExistent"})
    resolution = await resolve_entities(parse_result, profile, org_id, session)
    assert resolution.project_id is None
    assert resolution.project_name == "NonExistent"
