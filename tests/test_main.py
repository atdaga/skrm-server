import pytest
from fastapi.testclient import TestClient

from ..app.main import app

client = TestClient(app)


def test_hello_world():
    """Test the hello world endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello, World!"
    assert "app_name" in data
    assert "version" in data


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_hello_world_async():
    """Test the hello world endpoint with async client."""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello, World!"
