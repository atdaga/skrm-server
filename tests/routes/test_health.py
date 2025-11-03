"""Unit tests for health check endpoint."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.routes.health import router


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with health router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestHealthCheck:
    """Test suite for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: AsyncClient):
        """Test that health check returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_returns_json(self, client: AsyncClient):
        """Test that health check returns JSON response."""
        response = await client.get("/health")

        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_check_no_authentication_required(self, client: AsyncClient):
        """Test that health check endpoint doesn't require authentication."""
        # Should succeed without any authorization header
        response = await client.get("/health")

        assert response.status_code == 200
