"""Tests for the ingest.pre_demux_enabled scaffolding toggle (issue #244 §3.1)."""

import pytest

pytestmark = pytest.mark.asyncio


async def test_default_is_false(session):
    from app.services.library_service import LibraryService

    assert await LibraryService.is_pre_demux_enabled(session) is False


async def test_reads_true_when_set(session):
    from app.models.component import PlatformConfig
    from app.services.library_service import (
        LibraryService,
        PRE_DEMUX_ENABLED_KEY,
    )

    session.add(PlatformConfig(key=PRE_DEMUX_ENABLED_KEY, value="true"))
    await session.flush()
    await session.commit()

    assert await LibraryService.is_pre_demux_enabled(session) is True


async def test_other_truthy_values_are_accepted(session):
    from app.models.component import PlatformConfig
    from app.services.library_service import (
        LibraryService,
        PRE_DEMUX_ENABLED_KEY,
    )

    session.add(PlatformConfig(key=PRE_DEMUX_ENABLED_KEY, value="1"))
    await session.flush()
    await session.commit()

    assert await LibraryService.is_pre_demux_enabled(session) is True


async def test_false_value_returns_false(session):
    from app.models.component import PlatformConfig
    from app.services.library_service import (
        LibraryService,
        PRE_DEMUX_ENABLED_KEY,
    )

    session.add(PlatformConfig(key=PRE_DEMUX_ENABLED_KEY, value="false"))
    await session.flush()
    await session.commit()

    assert await LibraryService.is_pre_demux_enabled(session) is False
