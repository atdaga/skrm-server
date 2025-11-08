"""Unit tests for request context middleware."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.auth import create_access_token
from app.core.context import (
    get_principal_id,
    get_request_context,
    get_request_id,
    get_request_time,
)
from app.core.middleware import RequestContextMiddleware


@pytest.fixture
def test_app():
    """Create a test FastAPI app with the request context middleware."""
    app = FastAPI()

    # Add middleware
    app.add_middleware(RequestContextMiddleware)

    # Test route that returns context values
    @app.get("/test-context")
    async def test_context():  # noqa: F841 (used as route handler)
        return {
            "request_id": str(get_request_id()) if get_request_id() else None,
            "principal_id": get_principal_id(),
            "request_time": (
                get_request_time().isoformat() if get_request_time() else None
            ),
        }

    return app


class TestRequestContextMiddleware:
    """Test suite for RequestContextMiddleware."""

    @pytest.mark.asyncio
    async def test_middleware_generates_request_id(self, test_app):
        """Test that middleware generates a valid UUID7 request ID."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test-context")

        assert response.status_code == 200
        data = response.json()

        # Should have a request_id
        assert data["request_id"] is not None
        # Should be a valid UUID
        request_id = UUID(data["request_id"])
        # Should be UUID version 7
        assert request_id.version == 7

    @pytest.mark.asyncio
    async def test_middleware_generates_request_time(self, test_app):
        """Test that middleware generates a UTC timestamp."""
        before_request = datetime.now(UTC).replace(tzinfo=None)

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test-context")

        after_request = datetime.now(UTC).replace(tzinfo=None)

        assert response.status_code == 200
        data = response.json()

        # Should have a request_time
        assert data["request_time"] is not None

        # Parse the timestamp
        request_time = datetime.fromisoformat(data["request_time"])

        # Should be between before and after
        assert before_request <= request_time <= after_request

    @pytest.mark.asyncio
    async def test_middleware_no_token_sets_principal_id_none(self, test_app):
        """Test that middleware sets principal_id to None when no token provided."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test-context")

        assert response.status_code == 200
        data = response.json()

        # No token means principal_id should be None
        assert data["principal_id"] is None

    @pytest.mark.asyncio
    async def test_middleware_invalid_token_sets_principal_id_none(self, test_app):
        """Test that middleware sets principal_id to None for invalid token."""
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/test-context", headers={"Authorization": "Bearer invalid.token.here"}
            )

        assert response.status_code == 200
        data = response.json()

        # Invalid token means principal_id should be None
        assert data["principal_id"] is None

    @pytest.mark.asyncio
    async def test_middleware_valid_token_extracts_principal_id(self, test_app):
        """Test that middleware extracts principal_id from valid JWT token."""
        # Create a valid token
        user_id = str(uuid7())
        token_data = {"sub": user_id, "scope": "global"}
        now = datetime.now(UTC).replace(tzinfo=None)
        token = await create_access_token(token_data, now)

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/test-context", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()

        # Should extract the principal_id from token
        assert data["principal_id"] == user_id

    @pytest.mark.asyncio
    async def test_middleware_malformed_auth_header_sets_principal_id_none(
        self, test_app
    ):
        """Test that malformed Authorization header results in None principal_id."""
        malformed_headers = [
            {"Authorization": "InvalidFormat token"},
            {"Authorization": "Bearer"},
            {"Authorization": "token_without_bearer"},
            {"Authorization": ""},
        ]

        for headers in malformed_headers:
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get("/test-context", headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert data["principal_id"] is None

    @pytest.mark.asyncio
    async def test_middleware_expired_token_sets_principal_id_none(self, test_app):
        """Test that expired token results in None principal_id."""
        from datetime import timedelta

        # Create token that's already expired
        user_id = str(uuid7())
        token_data = {"sub": user_id, "scope": "global"}
        now = datetime.now(UTC).replace(tzinfo=None)
        token = await create_access_token(
            token_data, now, expires_delta=timedelta(seconds=-10)
        )

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/test-context", headers={"Authorization": f"Bearer {token}"}
            )

        assert response.status_code == 200
        data = response.json()

        # Expired token should result in None principal_id
        assert data["principal_id"] is None

    @pytest.mark.asyncio
    async def test_middleware_unique_request_ids(self, test_app):
        """Test that each request gets a unique request ID."""
        request_ids = []

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            for _ in range(5):
                response = await client.get("/test-context")
                data = response.json()
                request_ids.append(data["request_id"])

        # All request IDs should be unique
        assert len(request_ids) == len(set(request_ids))

    @pytest.mark.asyncio
    async def test_middleware_context_isolation(self, test_app):
        """Test that context variables are isolated between requests."""
        # Create two different tokens
        user_id_1 = str(uuid7())
        user_id_2 = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)

        token_1 = await create_access_token({"sub": user_id_1, "scope": "global"}, now)
        token_2 = await create_access_token({"sub": user_id_2, "scope": "global"}, now)

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # First request with token 1
            response1 = await client.get(
                "/test-context", headers={"Authorization": f"Bearer {token_1}"}
            )

            # Second request with token 2
            response2 = await client.get(
                "/test-context", headers={"Authorization": f"Bearer {token_2}"}
            )

            # Third request with no token
            response3 = await client.get("/test-context")

        # Each should have their own context
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1["principal_id"] == user_id_1
        assert data2["principal_id"] == user_id_2
        assert data3["principal_id"] is None

        # Request IDs should all be different
        assert data1["request_id"] != data2["request_id"]
        assert data2["request_id"] != data3["request_id"]
        assert data1["request_id"] != data3["request_id"]

    @pytest.mark.asyncio
    async def test_middleware_concurrent_requests(self, test_app):
        """Test that context is properly isolated in concurrent requests."""
        # Create multiple tokens for different users
        tokens = []
        user_ids = []

        for _ in range(10):
            user_id = str(uuid7())
            user_ids.append(user_id)
            now = datetime.now(UTC).replace(tzinfo=None)
            token = await create_access_token({"sub": user_id, "scope": "global"}, now)
            tokens.append(token)

        # Make concurrent requests
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            tasks = [
                client.get(
                    "/test-context", headers={"Authorization": f"Bearer {token}"}
                )
                for token in tokens
            ]
            responses = await asyncio.gather(*tasks)

        # Each response should have the correct principal_id
        for i, response in enumerate(responses):
            data = response.json()
            assert data["principal_id"] == user_ids[i]

    @pytest.mark.asyncio
    async def test_get_request_context_returns_all_values(self, test_app):
        """Test that get_request_context returns all context values."""
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        token = await create_access_token({"sub": user_id, "scope": "global"}, now)

        # Route that uses get_request_context
        @test_app.get("/test-full-context")
        async def test_full_context():  # noqa: F841 (used as route handler)
            context = get_request_context()
            return {
                "request_id": str(context.request_id) if context.request_id else None,
                "principal_id": context.principal_id,
                "request_time": (
                    context.request_time.isoformat() if context.request_time else None
                ),
            }

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/test-full-context", headers={"Authorization": f"Bearer {token}"}
            )

        data = response.json()

        # All values should be present
        assert data["request_id"] is not None
        assert data["principal_id"] == user_id
        assert data["request_time"] is not None

    @pytest.mark.asyncio
    async def test_middleware_context_cleared_after_request(self, test_app):
        """Test that context is cleared after request completes."""
        # This test verifies that context doesn't leak between requests

        # Make a request with a token
        user_id = str(uuid7())
        now = datetime.now(UTC).replace(tzinfo=None)
        token = await create_access_token({"sub": user_id, "scope": "global"}, now)

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response1 = await client.get(
                "/test-context", headers={"Authorization": f"Bearer {token}"}
            )

            # Make another request without a token
            response2 = await client.get("/test-context")

        data1 = response1.json()
        data2 = response2.json()

        # First request should have principal_id
        assert data1["principal_id"] == user_id

        # Second request should NOT have the same principal_id
        assert data2["principal_id"] is None

    @pytest.mark.asyncio
    async def test_middleware_token_without_sub_claim(self, test_app):
        """Test that token without 'sub' claim results in None principal_id."""
        from datetime import timedelta

        from jose import jwt

        from app.core.auth import ALGORITHM, SECRET_KEY

        # Create a token without 'sub' claim
        now = datetime.now(UTC).replace(tzinfo=None)
        now_utc = now.replace(tzinfo=UTC)

        data = {
            "scope": "test",
            "iss": "https://auth.baseklass.io",
            "aud": "https://dev.skrm.io",
            "jti": str(uuid7()),
            "iat": int(now_utc.timestamp()),
            "exp": int((now_utc + timedelta(minutes=15)).timestamp()),
            "ss": int(now_utc.timestamp()),
        }
        # Missing 'sub' claim
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/test-context", headers={"Authorization": f"Bearer {token}"}
            )

        data = response.json()

        # Token without sub should result in None (verify_token will reject it)
        assert data["principal_id"] is None


class TestRequestContextGetters:
    """Test suite for context getter functions."""

    def test_get_request_id_returns_none_outside_context(self):
        """Test that get_request_id returns None outside request context."""
        # Outside of a request context
        assert get_request_id() is None

    def test_get_principal_id_returns_none_outside_context(self):
        """Test that get_principal_id returns None outside request context."""
        assert get_principal_id() is None

    def test_get_request_time_returns_none_outside_context(self):
        """Test that get_request_time returns None outside request context."""
        assert get_request_time() is None

    def test_get_request_context_returns_all_none_outside_context(self):
        """Test that get_request_context returns all None outside request context."""
        context = get_request_context()

        assert context.request_id is None
        assert context.principal_id is None
        assert context.request_time is None
