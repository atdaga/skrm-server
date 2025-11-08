"""V1 API-specific test configuration.

This conftest overrides fixtures from the parent routes/conftest.py
to use authenticated app configurations for v1 API testing.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Override client fixture to use app_with_overrides for v1 API tests.

    This ensures v1 tests use the authenticated app with database and
    token dependency overrides.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac
