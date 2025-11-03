"""Unit tests for user endpoints."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.routes.deps import get_current_user
from app.routes.v1.users import router
from app.schemas.user import UserDetail


@pytest.fixture
def mock_user_detail(test_user_id: UUID, test_scope: str) -> UserDetail:
    """Create a mock UserDetail object for testing."""
    return UserDetail(
        id=test_user_id,
        scope=test_scope,
        username="testuser",
        primary_email="testuser@example.com",
        primary_email_verified=True,
        primary_phone="+1234567890",
        primary_phone_verified=True,
        enabled=True,
        time_zone="UTC",
        name_prefix=None,
        first_name="Test",
        middle_name=None,
        last_name="User",
        name_suffix=None,
        display_name="Test User",
        default_locale="en_US",
        system_role="user",
        meta={"department": "Engineering"},
        created=datetime.now(),
        created_by=test_user_id,
        last_modified=datetime.now(),
        last_modified_by=test_user_id,
    )


@pytest.fixture
def app_with_overrides(mock_user_detail: UserDetail) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing."""
    app = FastAPI()
    app.include_router(router)
    
    # Override dependencies
    async def override_get_current_user():
        return mock_user_detail
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    return app


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides),
        base_url="http://test"
    ) as ac:
        yield ac


class TestGetCurrentUserInfo:
    """Test suite for GET /users/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self,
        client: AsyncClient,
        mock_user_detail: UserDetail,
    ):
        """Test successfully getting current user information."""
        response = await client.get("/users/me")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields are present and correct
        assert data["id"] == str(mock_user_detail.id)
        assert data["scope"] == mock_user_detail.scope
        assert data["username"] == mock_user_detail.username
        assert data["primary_email"] == mock_user_detail.primary_email
        assert data["primary_email_verified"] == mock_user_detail.primary_email_verified
        assert data["primary_phone"] == mock_user_detail.primary_phone
        assert data["primary_phone_verified"] == mock_user_detail.primary_phone_verified
        assert data["enabled"] == mock_user_detail.enabled
        assert data["time_zone"] == mock_user_detail.time_zone
        assert data["name_prefix"] == mock_user_detail.name_prefix
        assert data["first_name"] == mock_user_detail.first_name
        assert data["middle_name"] == mock_user_detail.middle_name
        assert data["last_name"] == mock_user_detail.last_name
        assert data["name_suffix"] == mock_user_detail.name_suffix
        assert data["display_name"] == mock_user_detail.display_name
        assert data["default_locale"] == mock_user_detail.default_locale
        assert data["system_role"] == mock_user_detail.system_role
        assert data["meta"] == mock_user_detail.meta
        assert "created" in data
        assert "created_by" in data
        assert "last_modified" in data
        assert "last_modified_by" in data

    @pytest.mark.asyncio
    async def test_get_current_user_response_model(
        self,
        client: AsyncClient,
        test_user_id: UUID,
    ):
        """Test that response conforms to UserDetail schema."""
        response = await client.get("/users/me")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate that all required UserDetail fields are present
        required_fields = [
            "id", "scope", "username", "primary_email", "primary_email_verified",
            "primary_phone_verified", "enabled", "time_zone", "first_name",
            "last_name", "display_name", "default_locale", "system_role",
            "meta", "created", "created_by", "last_modified", "last_modified_by"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Validate UUID fields
        assert UUID(data["id"])
        assert UUID(data["created_by"])
        assert UUID(data["last_modified_by"])

    @pytest.mark.asyncio
    async def test_get_current_user_with_minimal_data(self):
        """Test getting current user with minimal data (null optional fields)."""
        # Create a minimal user detail
        minimal_user = UserDetail(
            id=uuid4(),
            scope="test-scope",
            username="minimaluser",
            primary_email="minimal@example.com",
            primary_email_verified=False,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="Minimal",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="Minimal User",
            default_locale="en_US",
            system_role="user",
            meta={},
            created=datetime.now(),
            created_by=uuid4(),
            last_modified=datetime.now(),
            last_modified_by=uuid4(),
        )
        
        # Create app with minimal user override
        app = FastAPI()
        app.include_router(router)
        
        async def override_get_current_user():
            return minimal_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/users/me")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify null fields are properly handled
            assert data["primary_phone"] is None
            assert data["name_prefix"] is None
            assert data["middle_name"] is None
            assert data["name_suffix"] is None
            assert data["meta"] == {}

    @pytest.mark.asyncio
    async def test_get_current_user_with_complex_meta(self):
        """Test getting current user with complex nested metadata."""
        complex_user = UserDetail(
            id=uuid4(),
            scope="test-scope",
            username="complexuser",
            primary_email="complex@example.com",
            primary_email_verified=True,
            primary_phone="+1234567890",
            primary_phone_verified=True,
            enabled=True,
            time_zone="America/New_York",
            name_prefix="Dr.",
            first_name="Complex",
            middle_name="Meta",
            last_name="User",
            name_suffix="Jr.",
            display_name="Dr. Complex Meta User Jr.",
            default_locale="en_US",
            system_role="admin",
            meta={
                "department": "Engineering",
                "team": "Backend",
                "preferences": {
                    "theme": "dark",
                    "notifications": {
                        "email": True,
                        "push": False,
                        "sms": True
                    }
                },
                "tags": ["senior", "fullstack", "lead"],
                "employee_id": 12345
            },
            created=datetime.now(),
            created_by=uuid4(),
            last_modified=datetime.now(),
            last_modified_by=uuid4(),
        )
        
        # Create app with complex user override
        app = FastAPI()
        app.include_router(router)
        
        async def override_get_current_user():
            return complex_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/users/me")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify complex metadata is properly returned
            assert data["meta"] == complex_user.meta
            assert data["meta"]["preferences"]["theme"] == "dark"
            assert data["meta"]["preferences"]["notifications"]["email"] is True
            assert "senior" in data["meta"]["tags"]

    @pytest.mark.asyncio
    async def test_get_current_user_different_roles(self):
        """Test getting current user with different system roles."""
        roles = ["user", "admin", "superuser", "guest"]
        
        for role in roles:
            role_user = UserDetail(
                id=uuid4(),
                scope="test-scope",
                username=f"{role}user",
                primary_email=f"{role}@example.com",
                primary_email_verified=True,
                primary_phone=None,
                primary_phone_verified=False,
                enabled=True,
                time_zone="UTC",
                name_prefix=None,
                first_name=role.capitalize(),
                middle_name=None,
                last_name="User",
                name_suffix=None,
                display_name=f"{role.capitalize()} User",
                default_locale="en_US",
                system_role=role,
                meta={"role": role},
                created=datetime.now(),
                created_by=uuid4(),
                last_modified=datetime.now(),
                last_modified_by=uuid4(),
            )
            
            # Create app with role-specific user override
            app = FastAPI()
            app.include_router(router)
            
            async def override_get_current_user():
                return role_user
            
            app.dependency_overrides[get_current_user] = override_get_current_user
            
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get("/users/me")
                
                assert response.status_code == 200
                data = response.json()
                assert data["system_role"] == role
                assert data["username"] == f"{role}user"

    @pytest.mark.asyncio
    async def test_get_current_user_disabled_user(self):
        """Test getting current user information when user is disabled."""
        # Note: In a real scenario, a disabled user shouldn't be able to authenticate,
        # but if they somehow do, the endpoint should still return their info
        disabled_user = UserDetail(
            id=uuid4(),
            scope="test-scope",
            username="disableduser",
            primary_email="disabled@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=False,  # User is disabled
            time_zone="UTC",
            name_prefix=None,
            first_name="Disabled",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="Disabled User",
            default_locale="en_US",
            system_role="user",
            meta={},
            created=datetime.now(),
            created_by=uuid4(),
            last_modified=datetime.now(),
            last_modified_by=uuid4(),
        )
        
        # Create app with disabled user override
        app = FastAPI()
        app.include_router(router)
        
        async def override_get_current_user():
            return disabled_user
        
        app.dependency_overrides[get_current_user] = override_get_current_user
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/users/me")
            
            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is False

    @pytest.mark.asyncio
    async def test_get_current_user_different_time_zones(self):
        """Test getting current user with different time zones."""
        time_zones = ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney"]
        
        for tz in time_zones:
            tz_user = UserDetail(
                id=uuid4(),
                scope="test-scope",
                username="tzuser",
                primary_email="tz@example.com",
                primary_email_verified=True,
                primary_phone=None,
                primary_phone_verified=False,
                enabled=True,
                time_zone=tz,
                name_prefix=None,
                first_name="TimeZone",
                middle_name=None,
                last_name="User",
                name_suffix=None,
                display_name="TimeZone User",
                default_locale="en_US",
                system_role="user",
                meta={},
                created=datetime.now(),
                created_by=uuid4(),
                last_modified=datetime.now(),
                last_modified_by=uuid4(),
            )
            
            # Create app with tz user override
            app = FastAPI()
            app.include_router(router)
            
            async def override_get_current_user():
                return tz_user
            
            app.dependency_overrides[get_current_user] = override_get_current_user
            
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get("/users/me")
                
                assert response.status_code == 200
                data = response.json()
                assert data["time_zone"] == tz

    @pytest.mark.asyncio
    async def test_get_current_user_endpoint_path(self, client: AsyncClient):
        """Test that the endpoint is accessible at the correct path."""
        response = await client.get("/users/me")
        assert response.status_code == 200
        
        # Verify incorrect paths return 404
        response = await client.get("/users")
        assert response.status_code == 404
        
        response = await client.get("/users/current")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_current_user_http_method(self, client: AsyncClient):
        """Test that only GET method is allowed."""
        # GET should work
        response = await client.get("/users/me")
        assert response.status_code == 200
        
        # Other methods should not be allowed
        response = await client.post("/users/me")
        assert response.status_code == 405  # Method Not Allowed
        
        response = await client.put("/users/me")
        assert response.status_code == 405
        
        response = await client.patch("/users/me")
        assert response.status_code == 405
        
        response = await client.delete("/users/me")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_get_current_user_idempotency(
        self,
        client: AsyncClient,
        mock_user_detail: UserDetail,
    ):
        """Test that multiple calls return the same user information (idempotent)."""
        # Make multiple requests
        response1 = await client.get("/users/me")
        response2 = await client.get("/users/me")
        response3 = await client.get("/users/me")
        
        # All should be successful
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        # All should return the same data
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()
        
        assert data1 == data2 == data3
        assert data1["id"] == str(mock_user_detail.id)

