"""Pytest configuration and fixtures for tests."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.schemas.user import TokenData


# Core async database fixtures

@pytest.fixture
async def async_engine():
    """Create an async in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
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
#     return uuid4()


# @pytest.fixture
# def sample_datetime():
#     """Generate a sample datetime for testing."""
#     return datetime.now()


@pytest.fixture
def creator_id():
    """Generate a UUID for the creator field."""
    return uuid4()


@pytest.fixture
def test_user_id() -> UUID:
    """Generate a test user ID for route testing."""
    return uuid4()


@pytest.fixture
def test_scope() -> str:
    """Generate a test scope for multi-tenancy testing."""
    return "test-tenant"


@pytest.fixture
def mock_token_data(test_user_id: UUID, test_scope: str) -> TokenData:
    """Create mock token data for authentication testing."""
    return TokenData(
        sub=str(test_user_id),
        scope=test_scope,
        iss="test-issuer"
    )
