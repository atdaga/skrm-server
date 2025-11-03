"""Unit tests for database configuration and session management."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.db.database import (
    DatabaseConfig,
    cleanup_database,
    cleanup_database_sync,
    create_all_tables,
    get_db,
    get_db_session,
    initialize_database,
)


class TestDatabaseConfig:
    """Test suite for DatabaseConfig class."""

    def test_database_config_initialization(self):
        """Test DatabaseConfig initialization."""
        config = DatabaseConfig()

        assert config.engine is None
        assert config.session_factory is None
        assert config._initialized is False

    @patch("app.core.db.database.create_async_engine")
    @patch("app.core.db.database.async_sessionmaker")
    @patch("app.core.db.database.settings")
    def test_database_config_initialize(
        self, mock_settings, mock_sessionmaker, mock_create_engine
    ):
        """Test DatabaseConfig.initialize method."""
        mock_settings.database_url = "postgresql+asyncpg://test"
        mock_settings.debug = False
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_user = "test_user"
        mock_settings.db_password = "test_pass"
        mock_settings.db_name = "test_db"

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()
        config.initialize()

        assert config._initialized is True
        assert config.engine is not None
        assert config.session_factory is not None
        mock_create_engine.assert_called_once()
        mock_sessionmaker.assert_called_once()

    @patch("app.core.db.database.create_async_engine")
    @patch("app.core.db.database.settings")
    def test_database_config_initialize_only_once(
        self, mock_settings, mock_create_engine
    ):
        """Test that DatabaseConfig.initialize only initializes once."""
        mock_settings.database_url = "postgresql+asyncpg://test"
        mock_settings.debug = False
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_user = "test_user"
        mock_settings.db_password = "test_pass"
        mock_settings.db_name = "test_db"

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()
        config.initialize()
        config.initialize()  # Call again

        # Should only be called once
        assert mock_create_engine.call_count == 1

    @pytest.mark.asyncio
    async def test_database_config_create_tables_not_initialized(self):
        """Test create_tables raises error when not initialized."""
        config = DatabaseConfig()

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await config.create_tables()

    @pytest.mark.asyncio
    @patch("app.core.db.database.create_async_engine")
    @patch("app.core.db.database.async_sessionmaker")
    @patch("app.core.db.database.settings")
    async def test_database_config_create_tables(
        self, mock_settings, mock_sessionmaker, mock_create_engine
    ):
        """Test DatabaseConfig.create_tables method."""
        mock_settings.database_url = "postgresql+asyncpg://test"
        mock_settings.debug = False
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_user = "test_user"
        mock_settings.db_password = "test_pass"
        mock_settings.db_name = "test_db"

        # Setup mock engine with begin context manager
        mock_conn = MagicMock()
        mock_conn.run_sync = AsyncMock()

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_begin = AsyncMock()
        mock_begin.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin.return_value = mock_begin

        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()
        config.initialize()

        await config.create_tables()

        mock_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.db.database.create_async_engine")
    @patch("app.core.db.database.settings")
    async def test_database_config_close(self, mock_settings, mock_create_engine):
        """Test DatabaseConfig.close method."""
        mock_settings.database_url = "postgresql+asyncpg://test"
        mock_settings.debug = False
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_user = "test_user"
        mock_settings.db_password = "test_pass"
        mock_settings.db_name = "test_db"

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock()
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()
        config.initialize()

        await config.close()

        mock_engine.dispose.assert_called_once()
        assert config._initialized is False


class TestGetDbSession:
    """Test suite for get_db_session function."""

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_get_db_session_initializes_if_needed(self, mock_db_config):
        """Test that get_db_session initializes database if not initialized."""
        mock_db_config._initialized = False
        mock_db_config.initialize = MagicMock()

        mock_session = MagicMock(spec=AsyncSession)
        mock_session.close = AsyncMock()

        mock_factory = MagicMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        mock_db_config.session_factory = mock_factory

        async with get_db_session() as session:
            assert session == mock_session

        mock_db_config.initialize.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_get_db_session_yields_session(self, mock_db_config):
        """Test that get_db_session yields a session."""
        mock_db_config._initialized = True

        mock_session = MagicMock(spec=AsyncSession)
        mock_session.close = AsyncMock()

        mock_factory = MagicMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        mock_db_config.session_factory = mock_factory

        async with get_db_session() as session:
            assert session == mock_session

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_get_db_session_no_factory_raises_error(self, mock_db_config):
        """Test get_db_session raises error when session factory is None."""
        mock_db_config._initialized = True
        mock_db_config.session_factory = None

        with pytest.raises(RuntimeError, match="session factory not initialized"):
            async with get_db_session():
                pass

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_get_db_session_rolls_back_on_exception(self, mock_db_config):
        """Test that get_db_session rolls back on exception."""
        mock_db_config._initialized = True

        mock_session = MagicMock(spec=AsyncSession)
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        mock_factory = MagicMock()
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = mock_context

        mock_db_config.session_factory = mock_factory

        with pytest.raises(ValueError):
            async with get_db_session():
                raise ValueError("Test exception")

        mock_session.rollback.assert_called_once()


class TestGetDb:
    """Test suite for get_db dependency function."""

    @pytest.mark.asyncio
    @patch("app.core.db.database.get_db_session")
    async def test_get_db_yields_session(self, mock_get_db_session):
        """Test that get_db yields a session from get_db_session."""
        mock_session = MagicMock(spec=AsyncSession)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_db_session.return_value = mock_context

        async for session in get_db():
            assert session == mock_session

    @pytest.mark.asyncio
    @patch("app.core.db.database.get_db_session")
    async def test_get_db_calls_get_db_session(self, mock_get_db_session):
        """Test that get_db calls get_db_session."""
        mock_session = MagicMock(spec=AsyncSession)

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_db_session.return_value = mock_context

        async for _ in get_db():
            pass

        mock_get_db_session.assert_called_once()


class TestCreateAllTables:
    """Test suite for create_all_tables function."""

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_create_all_tables_initializes_if_needed(self, mock_db_config):
        """Test that create_all_tables initializes database if not initialized."""
        mock_db_config._initialized = False
        mock_db_config.initialize = MagicMock()
        mock_db_config.create_tables = AsyncMock()

        await create_all_tables()

        mock_db_config.initialize.assert_called_once()
        mock_db_config.create_tables.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_create_all_tables_calls_create_tables(self, mock_db_config):
        """Test that create_all_tables calls db_config.create_tables."""
        mock_db_config._initialized = True
        mock_db_config.create_tables = AsyncMock()

        await create_all_tables()

        mock_db_config.create_tables.assert_called_once()


class TestInitializeDatabase:
    """Test suite for initialize_database function."""

    @patch("app.core.db.database.db_config")
    def test_initialize_database_calls_initialize(self, mock_db_config):
        """Test that initialize_database calls db_config.initialize."""
        mock_db_config.initialize = MagicMock()

        initialize_database()

        mock_db_config.initialize.assert_called_once()


class TestCleanupDatabase:
    """Test suite for cleanup_database function."""

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    @patch("app.core.db.database.logger")
    async def test_cleanup_database_disposes_engine(self, mock_logger, mock_db_config):
        """Test that cleanup_database disposes the engine."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock()

        mock_db_config._initialized = True
        mock_db_config.engine = mock_engine

        await cleanup_database()

        mock_engine.dispose.assert_called_once()
        assert mock_db_config._initialized is False

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    async def test_cleanup_database_not_initialized(self, mock_db_config):
        """Test cleanup_database when database is not initialized."""
        mock_db_config._initialized = False
        mock_db_config.engine = None

        # Should not raise error
        await cleanup_database()

    @pytest.mark.asyncio
    @patch("app.core.db.database.db_config")
    @patch("app.core.db.database.logger")
    async def test_cleanup_database_handles_errors(self, mock_logger, mock_db_config):
        """Test that cleanup_database handles errors gracefully."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock(side_effect=Exception("Cleanup error"))

        mock_db_config._initialized = True
        mock_db_config.engine = mock_engine

        # Should not raise error
        await cleanup_database()


class TestCleanupDatabaseSync:
    """Test suite for cleanup_database_sync function."""

    @patch("app.core.db.database.db_config")
    @patch("app.core.db.database.logger")
    def test_cleanup_database_sync_marks_uninitialized(
        self, mock_logger, mock_db_config
    ):
        """Test that cleanup_database_sync marks database as uninitialized."""
        mock_engine = MagicMock()
        mock_engine.sync_engine = MagicMock()
        mock_engine.sync_engine.dispose = MagicMock()

        mock_db_config._initialized = True
        mock_db_config.engine = mock_engine

        cleanup_database_sync()

        assert mock_db_config._initialized is False

    @patch("app.core.db.database.db_config")
    def test_cleanup_database_sync_not_initialized(self, mock_db_config):
        """Test cleanup_database_sync when database is not initialized."""
        mock_db_config._initialized = False
        mock_db_config.engine = None

        # Should not raise error
        cleanup_database_sync()

    @patch("app.core.db.database.db_config")
    def test_cleanup_database_sync_handles_errors(self, mock_db_config):
        """Test that cleanup_database_sync handles errors silently."""
        mock_engine = MagicMock()
        mock_engine.sync_engine = MagicMock()
        mock_engine.sync_engine.dispose = MagicMock(side_effect=Exception("Error"))

        mock_db_config._initialized = True
        mock_db_config.engine = mock_engine

        # Should not raise error
        cleanup_database_sync()

    @patch("app.core.db.database.db_config")
    def test_cleanup_database_sync_no_sync_engine(self, mock_db_config):
        """Test cleanup_database_sync when engine has no sync_engine."""
        mock_engine = MagicMock(spec=AsyncEngine)
        # No sync_engine attribute

        mock_db_config._initialized = True
        mock_db_config.engine = mock_engine

        # Should not raise error and should mark as uninitialized
        cleanup_database_sync()

        assert mock_db_config._initialized is False


class TestDatabaseIntegration:
    """Integration tests for database functionality."""

    @pytest.mark.asyncio
    @patch("app.core.db.database.create_async_engine")
    @patch("app.core.db.database.async_sessionmaker")
    @patch("app.core.db.database.settings")
    async def test_full_database_lifecycle(
        self, mock_settings, mock_sessionmaker, mock_create_engine
    ):
        """Test full database initialization and cleanup lifecycle."""
        mock_settings.database_url = "postgresql+asyncpg://test"
        mock_settings.debug = False
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_user = "test_user"
        mock_settings.db_password = "test_pass"
        mock_settings.db_name = "test_db"

        mock_engine = MagicMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock()
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()

        # Initialize
        config.initialize()
        assert config._initialized is True

        # Close
        await config.close()
        assert config._initialized is False
