"""Database configuration and session management for SQLModel."""

import atexit
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from ...config import settings
from ..logging import get_logger

logger = get_logger(__name__)


class DatabaseConfig:
    """Database configuration manager."""

    def __init__(self):
        self.engine = None
        self.session_factory = None
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

        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self._initialized = True

    async def create_tables(self) -> None:
        """Create all database tables."""
        if not self._initialized:
            raise RuntimeError("Database not initialized")

        # Import models to register them with SQLModel metadata

        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def close(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False


# Global database configuration instance
db_config = DatabaseConfig()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with proper cleanup."""
    if not db_config._initialized:
        db_config.initialize()

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
    if db_config._initialized and db_config.engine:
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
    """Synchronous cleanup for signal handlers and atexit."""
    if db_config._initialized and db_config.engine:
        logger.info("Closing database engine (sync backup)")
        try:
            # Use synchronous dispose for signal handlers
            db_config.engine.dispose()
            db_config._initialized = False
            logger.info("Database engine closed (sync backup)")
        except Exception:
            # Ignore cleanup errors during process exit
            pass


# Register cleanup function to run on process exit as backup
atexit.register(cleanup_database_sync)
