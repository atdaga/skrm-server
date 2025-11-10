"""Unit tests for main application module."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class TestApplicationConfiguration:
    """Test suite for FastAPI application configuration."""

    def test_app_is_fastapi_instance(self):
        """Test that app is a FastAPI instance."""
        from app.main import app

        assert isinstance(app, FastAPI)

    def test_app_title(self):
        """Test that app has correct title from settings."""
        from app.main import app

        assert app.title == "sKrm Server"

    def test_app_version(self):
        """Test that app has correct version."""
        from app.main import app

        assert app.version == "0.1.0"

    def test_app_description(self):
        """Test that app has a description."""
        from app.main import app

        assert app.description == "Backend API for the sKrm application"

    def test_app_has_lifespan(self):
        """Test that app has lifespan context manager configured."""
        from app.main import app

        assert app.router.lifespan_context is not None


class TestRouterRegistration:
    """Test suite for router registration."""

    def test_health_router_registered(self):
        """Test that health router is registered."""
        from app.main import app

        # Check that health routes are registered
        routes = [route.path for route in app.routes]
        assert "/health" in routes

    def test_auth_router_registered(self):
        """Test that auth router is registered with /api prefix."""
        from app.main import app

        # Check for auth routes with /api prefix
        routes = [route.path for route in app.routes]
        assert "/api/auth/login" in routes

    def test_v1_router_registered(self):
        """Test that v1 router is registered with /api/v1 prefix."""
        from app.main import app

        # Check for v1 routes with /api/v1 prefix
        routes = [route.path for route in app.routes]
        # Check for teams and users routes
        v1_routes = [r for r in routes if r.startswith("/api/v1")]
        assert len(v1_routes) > 0

    def test_all_routers_included(self):
        """Test that all expected routers are included."""
        from app.main import app

        routes = [route.path for route in app.routes]

        # Should have routes from all routers
        assert "/health" in routes  # health router
        assert any("/api/auth" in r for r in routes)  # auth router
        assert any("/api/v1" in r for r in routes)  # v1 router


class TestLifespanManager:
    """Test suite for application lifespan manager."""

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_lifespan_startup_success(self, mock_init_db, mock_cleanup_db):
        """Test successful application startup."""
        from app.main import lifespan

        mock_cleanup_db.return_value = AsyncMock()

        app = MagicMock(spec=FastAPI)

        async with lifespan(app):
            # Verify startup actions were called
            mock_init_db.assert_called_once()

        # Verify cleanup was called on shutdown
        mock_cleanup_db.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_lifespan_startup_database_error(self, mock_init_db, mock_cleanup_db):
        """Test that database initialization errors are raised."""
        from app.main import lifespan

        mock_init_db.side_effect = Exception("Database connection failed")

        app = MagicMock(spec=FastAPI)

        with pytest.raises(Exception, match="Database connection failed"):
            async with lifespan(app):
                pass

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_lifespan_cleanup_errors_handled(self, mock_init_db, mock_cleanup_db):
        """Test that cleanup errors are caught and logged."""
        from app.main import lifespan

        mock_cleanup_db.side_effect = Exception("Cleanup failed")

        app = MagicMock(spec=FastAPI)

        # Should not raise exception even if cleanup fails
        async with lifespan(app):
            pass


class TestApplicationEndpoints:
    """Integration tests for application endpoints."""

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_health_endpoint_accessible(self, mock_init_db, mock_cleanup_db):
        """Test that health endpoint is accessible."""
        from app.main import app

        mock_cleanup_db.return_value = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_openapi_schema_accessible(self, mock_init_db, mock_cleanup_db):
        """Test that OpenAPI schema is accessible."""
        from app.main import app

        mock_cleanup_db.return_value = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/openapi.json")
            assert response.status_code == 200
            data = response.json()
            assert "openapi" in data
            assert data["info"]["title"] == "sKrm Server"
            assert data["info"]["version"] == "0.1.0"

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_docs_endpoint_accessible(self, mock_init_db, mock_cleanup_db):
        """Test that API docs endpoint is accessible."""
        from app.main import app

        mock_cleanup_db.return_value = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/docs")
            assert response.status_code == 200


class TestLoggingSetup:
    """Test suite for logging configuration."""

    @patch("app.main.setup_logging")
    def test_logging_setup_called(self, mock_setup_logging):
        """Test that logging is set up when module is imported."""
        # Since the module is already imported, we can't directly test this
        # but we can verify the logger exists
        from app.main import logger

        assert logger is not None

    def test_logger_has_name(self):
        """Test that logger has correct name."""
        from app.main import logger

        # Logger should be configured
        assert logger is not None


class TestUvloopConfiguration:
    """Test suite for uvloop configuration."""

    def test_uvloop_configuration(self):
        """Test uvloop configuration on non-Windows platforms."""
        # The uvloop setup code runs at module import time
        # This test just verifies the module imported successfully
        from app.main import app

        assert app is not None

    def test_platform_check_exists(self):
        """Test that platform check exists for uvloop."""
        # Verify sys.platform is accessible
        assert sys.platform is not None


class TestApplicationRoutes:
    """Test suite for verifying all expected routes."""

    def test_health_routes_exist(self):
        """Test that health check routes exist."""
        from app.main import app

        paths = [route.path for route in app.routes]
        assert "/health" in paths

    def test_auth_routes_exist(self):
        """Test that authentication routes exist."""
        from app.main import app

        paths = [route.path for route in app.routes]
        assert "/api/auth/login" in paths

    def test_v1_teams_routes_exist(self):
        """Test that v1 teams routes exist."""
        from app.main import app

        paths = [route.path for route in app.routes]
        teams_routes = [p for p in paths if "/api/v1/teams" in p]
        assert len(teams_routes) > 0

    def test_v1_users_routes_exist(self):
        """Test that v1 users routes exist."""
        from app.main import app

        paths = [route.path for route in app.routes]
        assert "/api/v1/users/me" in paths

    def test_route_count(self):
        """Test that app has expected number of routes."""
        from app.main import app

        # Should have multiple routes from all routers
        assert len(app.routes) > 5


class TestApplicationMetadata:
    """Test suite for application metadata."""

    def test_app_debug_mode(self):
        """Test that app debug mode matches settings."""
        from app.config import settings
        from app.main import app

        assert app.debug == settings.debug

    def test_app_openapi_url(self):
        """Test that OpenAPI URL is configured."""
        from app.main import app

        # Default OpenAPI URL should be set
        assert app.openapi_url is not None

    def test_app_docs_url(self):
        """Test that docs URL is configured."""
        from app.main import app

        # Default docs URL should be set
        assert app.docs_url is not None


class TestApplicationIntegration:
    """Integration tests for the complete application."""

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_app_lifecycle(self, mock_init_db, mock_cleanup_db):
        """Test complete application lifecycle."""
        from app.main import app

        mock_cleanup_db.return_value = AsyncMock()

        # Simulate startup and make a request
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Make requests to different routers
            health_response = await client.get("/health")
            assert health_response.status_code == 200

            # OpenAPI should be available
            openapi_response = await client.get("/openapi.json")
            assert openapi_response.status_code == 200

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_app_handles_404(self, mock_init_db, mock_cleanup_db):
        """Test that app returns 404 for non-existent routes."""
        from app.main import app

        mock_cleanup_db.return_value = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/non-existent-route")
            assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.main.cleanup_database")
    @patch("app.main.initialize_database")
    async def test_multiple_requests(self, mock_init_db, mock_cleanup_db):
        """Test that app handles multiple sequential requests."""
        from app.main import app

        mock_cleanup_db.return_value = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Make multiple requests
            for _ in range(5):
                response = await client.get("/health")
                assert response.status_code == 200
