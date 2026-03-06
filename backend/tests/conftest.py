import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.services.auth_service import AuthService

TEST_DATABASE_URL = os.environ.get(
    "BIOAF_TEST_DATABASE_URL",
    "postgresql+asyncpg://bioaf_app:devpassword@localhost:5432/bioaf_test",
)

# These are lazily initialized — only when fixtures needing DB are requested
_engine = None
_test_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine
        _engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    return _engine


def _get_session_factory():
    global _test_session_factory
    if _test_session_factory is None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        _test_session_factory = async_sessionmaker(_get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _test_session_factory


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def setup_database():
    from app.database import Base
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session(setup_database):
    from sqlalchemy.ext.asyncio import AsyncSession
    async with _get_session_factory()() as session:
        yield session


@pytest_asyncio.fixture
async def client(session):
    from app.database import get_session
    from app.main import app

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(session):
    from app.models.organization import Organization
    from app.models.user import User

    org = Organization(name="Test Org", setup_complete=True)
    session.add(org)
    await session.flush()

    password_hash = AuthService.hash_password("testpassword123")
    user = User(
        email="admin@test.com",
        password_hash=password_hash,
        role="admin",
        organization_id=org.id,
        status="active",
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return user


@pytest_asyncio.fixture
async def admin_token(admin_user) -> str:
    return AuthService.create_token(
        admin_user.id, admin_user.email, admin_user.role, admin_user.organization_id
    )


@pytest_asyncio.fixture
async def viewer_user(session, admin_user):
    from app.models.user import User

    password_hash = AuthService.hash_password("viewerpass123")
    user = User(
        email="viewer@test.com",
        password_hash=password_hash,
        role="viewer",
        organization_id=admin_user.organization_id,
        status="active",
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return user


@pytest_asyncio.fixture
async def viewer_token(viewer_user) -> str:
    return AuthService.create_token(
        viewer_user.id, viewer_user.email, viewer_user.role, viewer_user.organization_id
    )
