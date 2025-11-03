"""Database configuration and session management for SQLModel."""

import atexit
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

from ...config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class DatabaseConfig:
    """Database configuration manager."""

    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the database engine and session factory."""
        if self._initialized:
            return

        # Use direct connection parameters instead of URL to avoid asyncpg macOS issues
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            connect_args={
                "host": settings.db_host,
                "port": settings.db_port,
                "user": settings.db_user,
                "password": settings.db_password,
                "database": settings.db_name,
            },
        )

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self._initialized = True

    async def create_tables(self) -> None:
        """Create all database tables."""
        if not self._initialized or self.engine is None:
            raise RuntimeError("Database not initialized")

        # Import models to register them with SQLModel metadata

        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def close(self) -> None:
        """Close the database engine."""
        if self.engine is not None:
            await self.engine.dispose()
            self._initialized = False


# Global database configuration instance
db_config = DatabaseConfig()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with proper cleanup."""
    if not db_config._initialized:
        db_config.initialize()

    if db_config.session_factory is None:
        raise RuntimeError("Database session factory not initialized")

    async with db_config.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with get_db_session() as session:
        yield session


async def create_all_tables() -> None:
    """Create all database tables. Call this during application startup."""
    if not db_config._initialized:
        db_config.initialize()

    await db_config.create_tables()


def initialize_database() -> None:
    """Initialize the database configuration."""
    db_config.initialize()


async def cleanup_database() -> None:
    """Cleanup database connections."""
    if db_config._initialized and db_config.engine is not None:
        logger.info("Closing database engine (async)")
        try:
            await db_config.engine.dispose()
            db_config._initialized = False
            logger.info("Database engine closed (async)")
        except Exception as e:
            # Log cleanup errors but don't raise them
            import logging

            logging.getLogger(__name__).warning("Error during database cleanup: %s", e)


def cleanup_database_sync() -> None:
    """Synchronous cleanup for signal handlers and atexit.

    Note: This is a best-effort cleanup. For asyncpg connections,
    we cannot properly close them in a synchronous context due to
    greenlet requirements. The OS will clean up the connections
    when the process exits.
    """
    if db_config._initialized and db_config.engine is not None:
        try:
            # Only attempt cleanup if we have a sync_engine available
            # For asyncpg (async-only engines), skip the cleanup to avoid
            # "MissingGreenlet" errors during process exit
            if hasattr(db_config.engine, "sync_engine"):
                logger.info("Closing database engine (sync backup)")
                db_config.engine.sync_engine.dispose()
                logger.info("Database engine closed (sync backup)")
            # Mark as uninitialized regardless
            db_config._initialized = False
        except Exception:
            # Ignore all cleanup errors during process exit
            # This is especially important for async database drivers
            pass


# Register cleanup function to run on process exit as backup
# Note: This may not work properly with asyncpg due to greenlet requirements,
# but we register it anyway for other database drivers
atexit.register(cleanup_database_sync)
