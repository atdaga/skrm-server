"""Pytest configuration and fixtures for tests."""

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid7

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.schemas.user import TokenData

if TYPE_CHECKING:
    from app.schemas.user import UserDetail

# Pytest hooks for cleanup


def pytest_sessionfinish(session, exitstatus):
    """Clean up database connections before pytest exits."""
    # Import here to avoid circular imports
    from app.core.db.database import db_config

    if db_config._initialized and db_config.engine is not None:
        # Get or create event loop for cleanup
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the cleanup in the event loop
        try:
            loop.run_until_complete(db_config.engine.dispose())
            db_config._initialized = False
        except Exception:
            # Ignore cleanup errors
            pass
        finally:
            # Don't close the loop if it was already running
            if not loop.is_running():
                try:
                    loop.close()
                except Exception:
                    pass


# Core async database fixtures


@pytest.fixture
async def async_engine():
    """Create an async in-memory SQLite engine for testing."""
    import sqlite3

    from sqlalchemy import event

    # Register datetime adapters for Python 3.12+ compatibility
    # These prevent deprecation warnings about default datetime adapters
    def adapt_datetime_iso(val):
        """Adapt datetime.datetime to ISO 8601 string."""
        return val.isoformat()

    def convert_datetime(val):
        """Convert ISO 8601 string to datetime.datetime."""
        return datetime.fromisoformat(val.decode())

    sqlite3.register_adapter(datetime, adapt_datetime_iso)
    sqlite3.register_converter("datetime", convert_datetime)

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support in SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create an async database session for testing."""
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session


# Alias for backward compatibility and cleaner test code
@pytest.fixture
async def session(async_session):
    """Alias for async_session to simplify test code."""
    return async_session


# Helper fixtures

# @pytest.fixture
# def sample_uuid():
#     """Generate a sample UUID for testing."""
#     return uuid7()


# @pytest.fixture
# def sample_datetime():
#     """Generate a sample datetime for testing."""
#     return datetime.now()


@pytest.fixture
def creator_id() -> UUID:
    """Generate a UUID for the creator field."""
    return uuid7()


@pytest.fixture
def test_user_id() -> UUID:
    """Generate a test user ID for route testing."""
    return uuid7()


@pytest.fixture
def test_scope() -> str:
    """Generate a test scope for multi-tenancy testing."""
    return "test-tenant"


@pytest.fixture
async def test_org_id(async_session: AsyncSession, test_user_id: UUID) -> UUID:
    """Create a test organization and return its ID."""
    from app.models import KOrganization

    org = KOrganization(
        name="Test Organization",
        alias="test_org",
        meta={},
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)
    return org.id


@pytest.fixture
def mock_token_data(test_user_id: UUID, test_scope: str) -> TokenData:
    """Create mock token data for authentication testing."""
    now = datetime.now(UTC).replace(tzinfo=None)
    return TokenData(
        sub=str(test_user_id),
        scope=test_scope,
        iss="test-issuer",
        aud="test-audience",
        jti=str(uuid7()),
        iat=now,
        exp=now,
        ss=now,
    )


# Helper function to add organization membership
async def add_user_to_organization(
    session: AsyncSession, org_id: UUID, user_id: UUID
) -> None:
    """Helper function to add a user as a principal of an organization.

    Args:
        session: Database session
        org_id: Organization ID
        user_id: User/Principal ID to add to organization
    """
    from app.models import KOrganizationPrincipal

    org_principal = KOrganizationPrincipal(
        org_id=org_id,
        principal_id=user_id,
        created_by=user_id,
        last_modified_by=user_id,
    )
    session.add(org_principal)
    await session.commit()


# Common test data fixtures


@pytest.fixture
async def test_organization(async_session: AsyncSession, test_user_id: UUID):
    """Create a test organization with the test user as a member.

    This is the standard organization fixture where the test user IS a member.
    Use this for testing normal authorized operations.
    """
    from app.models import KOrganization, KPrincipal

    # Create a principal for the test user
    principal = KPrincipal(
        id=test_user_id,
        username="testuser",
        primary_email="test@example.com",
        first_name="Test",
        last_name="User",
        display_name="Test User",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()

    org = KOrganization(
        name="Test Organization",
        alias="test_org",
        meta={"test": "data"},
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)

    # Add test user as organization member
    await add_user_to_organization(async_session, org.id, test_user_id)

    return org


@pytest.fixture
async def test_organization_without_membership(
    async_session: AsyncSession, test_user_id: UUID
):
    """Create a test organization WITHOUT adding the test user as a member.

    Use this for testing unauthorized access scenarios where the user
    is NOT a member of the organization.
    """
    # Create a principal for the test user if it doesn't exist
    from sqlmodel import select

    from app.models import KOrganization, KPrincipal

    result = await async_session.execute(
        select(KPrincipal).where(
            KPrincipal.id == test_user_id,
            KPrincipal.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
        )
    )
    existing_principal = result.scalar_one_or_none()

    if not existing_principal:
        principal = KPrincipal(
            id=test_user_id,
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(principal)
        await async_session.commit()

    org = KOrganization(
        name="Unauthorized Organization",
        alias="unauth_org",
        meta={},
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)

    return org


@pytest.fixture
async def test_principal(async_session: AsyncSession, test_user_id: UUID):
    """Create a test principal (user) for testing.

    This creates a separate principal (not the test_user_id) that can be
    added to organizations, teams, etc.
    """
    from sqlmodel import select

    from app.models import KPrincipal

    # Create or get the test_user principal first (for created_by/last_modified_by)
    result = await async_session.execute(
        select(KPrincipal).where(
            KPrincipal.id == test_user_id,
            KPrincipal.deleted == False,  # type: ignore[comparison-overlap]  # noqa: E712
        )
    )
    test_user_principal = result.scalar_one_or_none()

    if not test_user_principal:
        test_user_principal = KPrincipal(
            id=test_user_id,
            username="testuser",
            primary_email="testuser@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(test_user_principal)
        await async_session.commit()

    principal = KPrincipal(
        username="testprincipal",
        primary_email="principal@example.com",
        first_name="Test",
        last_name="Principal",
        display_name="Test Principal",
        created_by=test_user_id,
        last_modified_by=test_user_id,
    )
    async_session.add(principal)
    await async_session.commit()
    await async_session.refresh(principal)

    return principal


# FastAPI test client fixtures


@pytest.fixture
def app_with_overrides(async_session: AsyncSession, mock_token_data: TokenData):
    """Create a FastAPI app with dependency overrides for testing.

    This fixture is meant to be used with parametrization or by including
    the router in the test file. By default, it creates an app with no routes.
    """
    from fastapi import FastAPI

    from app.core.db.database import get_db
    from app.routes.deps import get_current_token

    app = FastAPI()

    # Override dependencies
    async def override_get_db():
        yield async_session

    async def override_get_current_token():
        return mock_token_data

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_token] = override_get_current_token

    return app


@pytest.fixture
async def client(app_with_overrides):
    """Create an async HTTP client for testing.

    This fixture depends on app_with_overrides, which should have routes
    included before creating the client.
    """
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac


# Mock user fixtures for authentication testing


@pytest.fixture
def mock_user(test_user_id: UUID) -> "UserDetail":
    """Create a mock UserDetail object for testing.

    This is useful for testing endpoints that require authentication
    without going through the full authentication flow.
    """
    from datetime import datetime

    from app.models.k_principal import SystemRole
    from app.schemas.user import UserDetail

    now = datetime.now()
    return UserDetail(
        id=test_user_id,
        scope="global",
        username="testuser",
        primary_email="test@example.com",
        primary_email_verified=True,
        primary_phone=None,
        primary_phone_verified=False,
        enabled=True,
        time_zone="UTC",
        name_prefix=None,
        first_name="Test",
        middle_name=None,
        last_name="User",
        name_suffix=None,
        display_name="Test User",
        default_locale="en",
        system_role=SystemRole.SYSTEM_USER,
        meta={},
        created=now,
        created_by=test_user_id,
        last_modified=now,
        last_modified_by=test_user_id,
    )


@pytest.fixture
def mock_user_detail(test_user_id: UUID, test_scope: str) -> "UserDetail":
    """Create a mock UserDetail object with custom scope for testing.

    Similar to mock_user but allows custom scope configuration.
    """
    from datetime import datetime

    from app.models.k_principal import SystemRole
    from app.schemas.user import UserDetail

    return UserDetail(
        id=test_user_id,
        scope=test_scope,
        username="testuser",
        primary_email="testuser@example.com",
        primary_email_verified=True,
        primary_phone="+1234567890",
        primary_phone_verified=True,
        enabled=True,
        time_zone="UTC",
        name_prefix=None,
        first_name="Test",
        middle_name=None,
        last_name="User",
        name_suffix=None,
        display_name="Test User",
        default_locale="en_US",
        system_role=SystemRole.SYSTEM_USER,
        meta={"department": "Engineering"},
        created=datetime.now(),
        created_by=test_user_id,
        last_modified=datetime.now(),
        last_modified_by=test_user_id,
    )
