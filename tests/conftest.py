"""Pytest configuration and fixtures for tests."""

import asyncio
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.schemas.user import TokenData


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
def creator_id() -> UUID:
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
