"""Unit tests for user management endpoints."""

from datetime import datetime
from uuid import UUID, uuid7

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KPrincipal
from app.models.k_principal import SystemRole
from app.routes.deps import get_current_user
from app.routes.v1.users import router
from app.schemas.user import UserDetail


@pytest.fixture
def mock_root_user(test_user_id: UUID) -> UserDetail:
    """Create a mock UserDetail object with systemRoot role for testing."""
    now = datetime.now()
    return UserDetail(
        id=test_user_id,
        scope="global",
        username="rootuser",
        primary_email="root@example.com",
        primary_email_verified=True,
        primary_phone=None,
        primary_phone_verified=False,
        enabled=True,
        time_zone="UTC",
        name_prefix=None,
        first_name="Root",
        middle_name=None,
        last_name="User",
        name_suffix=None,
        display_name="Root User",
        default_locale="en",
        system_role=SystemRole.SYSTEM_ROOT,
        meta={},
        deleted_at=None,
        created=now,
        created_by=test_user_id,
        last_modified=now,
        last_modified_by=test_user_id,
    )


@pytest.fixture
def mock_user_detail(test_user_id: UUID) -> UserDetail:
    """Override mock_user_detail to use SYSTEM role for user operations tests."""
    now = datetime.now()
    return UserDetail(
        id=test_user_id,
        scope="test-tenant",
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
        system_role=SystemRole.SYSTEM,
        meta={"department": "Engineering"},
        deleted_at=None,
        created=now,
        created_by=test_user_id,
        last_modified=now,
        last_modified_by=test_user_id,
    )


@pytest.fixture
def app_with_overrides(
    async_session: AsyncSession, mock_user_detail: UserDetail
) -> FastAPI:
    """Create a FastAPI app with dependency overrides for testing."""
    from app.core.db.database import get_db

    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    async def override_get_db():
        yield async_session

    async def override_get_current_user():
        return mock_user_detail

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return app


@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac


class TestCreateUser:
    """Test suite for POST /users endpoint."""

    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test successfully creating a new user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_data = {
                "username": "newuser",
                "password": "SecurePassword123!",
                "primary_email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "display_name": "New User",
            }

            response = await client.post("/users", json=user_data)

            assert response.status_code == 201
            data = response.json()
            assert data["username"] == "newuser"
            assert data["primary_email"] == "newuser@example.com"
            assert data["first_name"] == "New"
            assert data["last_name"] == "User"
            assert "id" in data
            assert UUID(data["id"])

    @pytest.mark.asyncio
    async def test_create_user_without_root_role(
        self,
        async_session: AsyncSession,
        mock_client_user: UserDetail,
    ):
        """Test that non-root users cannot create users."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_client_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_data = {
                "username": "newuser",
                "password": "SecurePassword123!",
                "primary_email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "display_name": "New User",
            }

            response = await client.post("/users", json=user_data)

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test that creating a user with duplicate username fails."""
        from app.core.db.database import get_db

        # Create existing user
        existing_user = KPrincipal(
            scope="global",
            username="existinguser",
            primary_email="existing@example.com",
            first_name="Existing",
            last_name="User",
            display_name="Existing User",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
        )
        async_session.add(existing_user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            user_data = {
                "username": "existinguser",
                "password": "SecurePassword123!",
                "primary_email": "another@example.com",
                "first_name": "Another",
                "last_name": "User",
                "display_name": "Another User",
            }

            response = await client.post("/users", json=user_data)

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]


class TestListUsers:
    """Test suite for GET /users endpoint."""

    @pytest.mark.asyncio
    async def test_list_users_empty(self, client: AsyncClient):
        """Test listing users when none exist in scope."""
        response = await client.get("/users")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)

    @pytest.mark.asyncio
    async def test_list_users_multiple(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test listing multiple users."""
        from app.core.db.database import get_db

        # Create multiple users in the same scope
        for i in range(3):
            user = KPrincipal(
                scope=mock_user_detail.scope,
                username=f"user{i}",
                primary_email=f"user{i}@example.com",
                first_name=f"User{i}",
                last_name="Test",
                display_name=f"User {i}",
                created_by=mock_user_detail.id,
                last_modified_by=mock_user_detail.id,
            )
            async_session.add(user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/users")

            assert response.status_code == 200
            data = response.json()
            assert len(data["users"]) == 3
            # Verify User schema fields are present (not UserDetail audit fields)
            for user in data["users"]:
                assert "id" in user
                assert "username" in user
                assert "primary_email" in user
                # User schema should not include audit fields
                assert "scope" not in user
                assert "created" not in user
                assert "created_by" not in user
                assert "last_modified" not in user
                assert "last_modified_by" not in user


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
        assert data["id"] == str(mock_user_detail.id)
        assert data["username"] == mock_user_detail.username


class TestGetUser:
    """Test suite for GET /users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_success(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test successfully retrieving a user by ID."""
        from app.core.db.database import get_db

        # Create a user
        user = KPrincipal(
            scope=mock_user_detail.scope,
            username="targetuser",
            primary_email="target@example.com",
            first_name="Target",
            last_name="User",
            display_name="Target User",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/users/{user.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(user.id)
            assert data["username"] == "targetuser"
            assert data["primary_email"] == "target@example.com"
            # User schema should not include audit fields
            assert "scope" not in data
            assert "created" not in data
            assert "created_by" not in data
            assert "last_modified" not in data
            assert "last_modified_by" not in data

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client: AsyncClient):
        """Test retrieving a non-existent user."""
        fake_id = uuid7()
        response = await client.get(f"/users/{fake_id}")

        assert response.status_code == 404


class TestUpdateUser:
    """Test suite for PATCH /users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_user_success(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test successfully updating own user information."""
        from app.core.db.database import get_db

        # Create the current user in DB
        user = KPrincipal(
            id=mock_user_detail.id,
            scope=mock_user_detail.scope,
            username=mock_user_detail.username,
            primary_email=mock_user_detail.primary_email,
            first_name="Old",
            last_name="Name",
            display_name="Old Name",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {
                "first_name": "New",
                "last_name": "Name",
                "display_name": "New Name",
            }

            response = await client.patch(
                f"/users/{mock_user_detail.id}", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["first_name"] == "New"
            assert data["last_name"] == "Name"

    @pytest.mark.asyncio
    async def test_update_user_unauthorized(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
        test_user_id: UUID,
    ):
        """Test that users without system or systemRoot role cannot update users."""
        from app.core.db.database import get_db

        # Create a user with insufficient privileges (SYSTEM_USER role)
        now = datetime.now()
        insufficient_user = UserDetail(
            id=test_user_id,
            scope="test-tenant",
            username="systemuser",
            primary_email="systemuser@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en_US",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create another user to try to update
        other_user = KPrincipal(
            scope=insufficient_user.scope,
            username="otheruser",
            primary_email="other@example.com",
            first_name="Other",
            last_name="User",
            display_name="Other User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_user)
        await async_session.commit()
        await async_session.refresh(other_user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return insufficient_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"first_name": "Hacked"}

            response = await client.patch(f"/users/{other_user.id}", json=update_data)

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()
            assert "system or system_root" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_user_not_found(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test updating a non-existent user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"first_name": "New"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}", json=update_data
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user_all_fields(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test updating user with all optional fields."""
        from app.core.db.database import get_db

        # Create the current user in DB
        user = KPrincipal(
            id=mock_user_detail.id,
            scope=mock_user_detail.scope,
            username=mock_user_detail.username,
            primary_email=mock_user_detail.primary_email,
            first_name="Old",
            last_name="Name",
            display_name="Old Name",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {
                "time_zone": "America/New_York",
                "name_prefix": "Dr.",
                "first_name": "New",
                "middle_name": "M",
                "last_name": "Name",
                "name_suffix": "Jr.",
                "display_name": "New Name",
                "default_locale": "en_US",
                "system_role": "systemAdmin",
                "meta": {"key": "value"},
            }

            response = await client.patch(
                f"/users/{mock_user_detail.id}", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["time_zone"] == "America/New_York"
            assert data["name_prefix"] == "Dr."
            assert data["first_name"] == "New"
            assert data["middle_name"] == "M"
            assert data["last_name"] == "Name"
            assert data["name_suffix"] == "Jr."
            assert data["display_name"] == "New Name"
            assert data["default_locale"] == "en_US"
            assert data["system_role"] == "systemAdmin"
            assert data["meta"] == {"key": "value"}


class TestUpdateUserUsername:
    """Test suite for PATCH /users/{user_id}/username endpoint."""

    @pytest.mark.asyncio
    async def test_update_username_success(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test successfully updating own username."""
        from app.core.db.database import get_db

        # Create the current user in DB
        user = KPrincipal(
            id=mock_user_detail.id,
            scope=mock_user_detail.scope,
            username="oldusername",
            primary_email=mock_user_detail.primary_email,
            first_name=mock_user_detail.first_name,
            last_name=mock_user_detail.last_name,
            display_name=mock_user_detail.display_name,
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"username": "newusername"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/username", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "newusername"

    @pytest.mark.asyncio
    async def test_update_username_conflict(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test updating username to an existing username fails."""
        from app.core.db.database import get_db

        # Create existing user with target username
        existing_user = KPrincipal(
            scope=mock_user_detail.scope,
            username="takenusername",
            primary_email="taken@example.com",
            first_name="Taken",
            last_name="User",
            display_name="Taken User",
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(existing_user)

        # Create current user
        current_user = KPrincipal(
            id=mock_user_detail.id,
            scope=mock_user_detail.scope,
            username="myusername",
            primary_email=mock_user_detail.primary_email,
            first_name=mock_user_detail.first_name,
            last_name=mock_user_detail.last_name,
            display_name=mock_user_detail.display_name,
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(current_user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"username": "takenusername"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/username", json=update_data
            )

            assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_username_unauthorized(
        self,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that users without system or systemRoot role cannot update usernames."""
        from app.core.db.database import get_db

        # Create a user with insufficient privileges (SYSTEM_USER role)
        now = datetime.now()
        insufficient_user = UserDetail(
            id=test_user_id,
            scope="test-tenant",
            username="systemuser",
            primary_email="systemuser@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en_US",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create another user to try to update
        other_user = KPrincipal(
            scope=insufficient_user.scope,
            username="otheruser",
            primary_email="other@example.com",
            first_name="Other",
            last_name="User",
            display_name="Other User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_user)
        await async_session.commit()
        await async_session.refresh(other_user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return insufficient_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"username": "hackedusername"}

            response = await client.patch(
                f"/users/{other_user.id}/username", json=update_data
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()
            assert "system or system_root" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_username_not_found(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test updating username for a non-existent user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"username": "newusername"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/username", json=update_data
            )

            assert response.status_code == 404


class TestUpdateUserEmail:
    """Test suite for PATCH /users/{user_id}/email endpoint."""

    @pytest.mark.asyncio
    async def test_update_email_success(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test successfully updating own email."""
        from app.core.db.database import get_db

        # Create the current user in DB
        user = KPrincipal(
            id=mock_user_detail.id,
            scope=mock_user_detail.scope,
            username=mock_user_detail.username,
            primary_email="old@example.com",
            primary_email_verified=True,
            first_name=mock_user_detail.first_name,
            last_name=mock_user_detail.last_name,
            display_name=mock_user_detail.display_name,
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"email": "new@example.com"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/email", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["primary_email"] == "new@example.com"
            assert data["primary_email_verified"] is False

    @pytest.mark.asyncio
    async def test_update_email_unauthorized(
        self,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that users without system or systemRoot role cannot update emails."""
        from app.core.db.database import get_db

        # Create a user with insufficient privileges (SYSTEM_USER role)
        now = datetime.now()
        insufficient_user = UserDetail(
            id=test_user_id,
            scope="test-tenant",
            username="systemuser",
            primary_email="systemuser@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en_US",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create another user to try to update
        other_user = KPrincipal(
            scope=insufficient_user.scope,
            username="otheruser",
            primary_email="other@example.com",
            first_name="Other",
            last_name="User",
            display_name="Other User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_user)
        await async_session.commit()
        await async_session.refresh(other_user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return insufficient_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"email": "hacked@example.com"}

            response = await client.patch(
                f"/users/{other_user.id}/email", json=update_data
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()
            assert "system or system_root" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_email_not_found(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test updating email for a non-existent user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"email": "newemail@example.com"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/email", json=update_data
            )

            assert response.status_code == 404


class TestUpdateUserPrimaryPhone:
    """Test suite for PATCH /users/{user_id}/primary-phone endpoint."""

    @pytest.mark.asyncio
    async def test_update_phone_success(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test successfully updating own primary phone."""
        from app.core.db.database import get_db

        # Create the current user in DB
        user = KPrincipal(
            id=mock_user_detail.id,
            scope=mock_user_detail.scope,
            username=mock_user_detail.username,
            primary_email=mock_user_detail.primary_email,
            primary_phone="+1234567890",
            primary_phone_verified=True,
            first_name=mock_user_detail.first_name,
            last_name=mock_user_detail.last_name,
            display_name=mock_user_detail.display_name,
            created_by=mock_user_detail.id,
            last_modified_by=mock_user_detail.id,
        )
        async_session.add(user)
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"primary_phone": "+9876543210"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/primary-phone", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["primary_phone"] == "+9876543210"
            assert data["primary_phone_verified"] is False

    @pytest.mark.asyncio
    async def test_update_phone_unauthorized(
        self,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that users without system or systemRoot role cannot update phones."""
        from app.core.db.database import get_db

        # Create a user with insufficient privileges (SYSTEM_USER role)
        now = datetime.now()
        insufficient_user = UserDetail(
            id=test_user_id,
            scope="test-tenant",
            username="systemuser",
            primary_email="systemuser@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en_US",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create another user to try to update
        other_user = KPrincipal(
            scope=insufficient_user.scope,
            username="otheruser",
            primary_email="other@example.com",
            first_name="Other",
            last_name="User",
            display_name="Other User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(other_user)
        await async_session.commit()
        await async_session.refresh(other_user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return insufficient_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"primary_phone": "+1111111111"}

            response = await client.patch(
                f"/users/{other_user.id}/primary-phone", json=update_data
            )

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()
            assert "system or system_root" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_phone_not_found(
        self,
        async_session: AsyncSession,
        mock_user_detail: UserDetail,
    ):
        """Test updating phone for a non-existent user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_user_detail

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            update_data = {"primary_phone": "+9876543210"}

            response = await client.patch(
                f"/users/{mock_user_detail.id}/primary-phone", json=update_data
            )

            assert response.status_code == 404


class TestDeleteUser:
    """Test suite for DELETE /users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_soft_delete_user_success(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test successfully soft deleting a user (default behavior)."""
        from sqlalchemy import select

        from app.core.db.database import get_db

        # Create a user to delete
        user = KPrincipal(
            scope=mock_root_user.scope,
            username="deleteme",
            primary_email="deleteme@example.com",
            first_name="Delete",
            last_name="Me",
            display_name="Delete Me",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        user_id = user.id

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/users/{user_id}")

            assert response.status_code == 204

            # Verify user is soft deleted (deleted_at is set)
            stmt = select(KPrincipal).where(KPrincipal.id == user_id)  # type: ignore[arg-type]
            result = await async_session.execute(stmt)
            deleted_user = result.scalar_one_or_none()

            assert deleted_user is not None
            assert deleted_user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_deleted_user_not_in_list(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test that soft-deleted users are not visible in list."""
        from datetime import datetime

        from app.core.db.database import get_db

        # Create users
        user1 = KPrincipal(
            scope=mock_root_user.scope,
            username="activeuser",
            primary_email="active@example.com",
            first_name="Active",
            last_name="User",
            display_name="Active User",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
        )
        user2 = KPrincipal(
            scope=mock_root_user.scope,
            username="deleteduser",
            primary_email="deleted@example.com",
            first_name="Deleted",
            last_name="User",
            display_name="Deleted User",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
            deleted_at=datetime.now(),  # Soft deleted
        )
        async_session.add_all([user1, user2])
        await async_session.commit()

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/users")

            assert response.status_code == 200
            data = response.json()
            usernames = [u["username"] for u in data["users"]]
            assert "activeuser" in usernames
            assert "deleteduser" not in usernames

    @pytest.mark.asyncio
    async def test_soft_deleted_user_not_retrievable(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test that soft-deleted users cannot be retrieved."""
        from datetime import datetime

        from app.core.db.database import get_db

        # Create a soft-deleted user
        user = KPrincipal(
            scope=mock_root_user.scope,
            username="deleteduser",
            primary_email="deleted@example.com",
            first_name="Deleted",
            last_name="User",
            display_name="Deleted User",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
            deleted_at=datetime.now(),  # Soft deleted
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/users/{user.id}")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_soft_deleted_user_cannot_be_deleted_again(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test that soft-deleted users cannot be deleted again."""
        from datetime import datetime

        from app.core.db.database import get_db

        # Create a soft-deleted user
        user = KPrincipal(
            scope=mock_root_user.scope,
            username="deleteduser",
            primary_email="deleted@example.com",
            first_name="Deleted",
            last_name="User",
            display_name="Deleted User",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
            deleted_at=datetime.now(),  # Soft deleted
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/users/{user.id}")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_hard_delete_user_with_system_root_role(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test hard delete with systemRoot role."""
        from sqlalchemy import select

        from app.core.db.database import get_db

        # Create a user to delete
        user = KPrincipal(
            scope=mock_root_user.scope,
            username="harddelete",
            primary_email="harddelete@example.com",
            first_name="Hard",
            last_name="Delete",
            display_name="Hard Delete",
            created_by=mock_root_user.id,
            last_modified_by=mock_root_user.id,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        user_id = user.id

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/users/{user_id}?hard_delete=true")

            assert response.status_code == 204

            # Verify user is permanently deleted from database
            stmt = select(KPrincipal).where(KPrincipal.id == user_id)  # type: ignore[arg-type]
            result = await async_session.execute(stmt)
            deleted_user = result.scalar_one_or_none()

            assert deleted_user is None

    @pytest.mark.asyncio
    async def test_hard_delete_with_system_role(
        self,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that delete endpoint allows system role."""
        from sqlalchemy import select

        from app.core.db.database import get_db

        # Create mock system user (should be allowed to delete)
        now = datetime.now()
        mock_system_user = UserDetail(
            id=test_user_id,
            scope="global",
            username="systemuser",
            primary_email="system@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en",
            system_role=SystemRole.SYSTEM,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create a user to delete
        user = KPrincipal(
            scope=mock_system_user.scope,
            username="harddelete2",
            primary_email="harddelete2@example.com",
            first_name="Hard",
            last_name="Delete",
            display_name="Hard Delete 2",
            created_by=mock_system_user.id,
            last_modified_by=mock_system_user.id,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        user_id = user.id

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_system_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/users/{user_id}?hard_delete=true")

            # Should succeed - SYSTEM role can now delete users
            assert response.status_code == 204

            # Verify user is permanently deleted from database
            stmt = select(KPrincipal).where(KPrincipal.id == user_id)  # type: ignore[arg-type]
            result = await async_session.execute(stmt)
            deleted_user = result.scalar_one_or_none()

            assert deleted_user is None

    @pytest.mark.asyncio
    async def test_hard_delete_endpoint_requires_system_root(
        self,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that delete endpoint requires systemRoot role (systemAdmin not allowed)."""
        from app.core.db.database import get_db

        # Create mock systemAdmin user (not allowed to access delete endpoint)
        now = datetime.now()
        mock_admin_user = UserDetail(
            id=test_user_id,
            scope="global",
            username="adminuser",
            primary_email="admin@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="Admin",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="Admin User",
            default_locale="en",
            system_role=SystemRole.SYSTEM_ADMIN,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create a user to delete
        user = KPrincipal(
            scope=mock_admin_user.scope,
            username="targetuser",
            primary_email="target@example.com",
            first_name="Target",
            last_name="User",
            display_name="Target User",
            created_by=mock_admin_user.id,
            last_modified_by=mock_admin_user.id,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_admin_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/users/{user.id}?hard_delete=true")

            # Should fail at dependency level - systemAdmin doesn't have systemRoot role
            assert response.status_code == 403
            assert "systemroot" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_user_without_system_or_root_role(
        self,
        async_session: AsyncSession,
        test_user_id: UUID,
    ):
        """Test that users without system or systemRoot role cannot delete users."""
        from app.core.db.database import get_db

        # Create a user with insufficient privileges (SYSTEM_USER role)
        now = datetime.now()
        insufficient_user = UserDetail(
            id=test_user_id,
            scope="test-tenant",
            username="systemuser",
            primary_email="systemuser@example.com",
            primary_email_verified=True,
            primary_phone=None,
            primary_phone_verified=False,
            enabled=True,
            time_zone="UTC",
            name_prefix=None,
            first_name="System",
            middle_name=None,
            last_name="User",
            name_suffix=None,
            display_name="System User",
            default_locale="en_US",
            system_role=SystemRole.SYSTEM_USER,
            meta={},
            deleted_at=None,
            created=now,
            created_by=test_user_id,
            last_modified=now,
            last_modified_by=test_user_id,
        )

        # Create a user to try to delete
        user = KPrincipal(
            scope=insufficient_user.scope,
            username="targetuser",
            primary_email="target@example.com",
            first_name="Target",
            last_name="User",
            display_name="Target User",
            created_by=test_user_id,
            last_modified_by=test_user_id,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return insufficient_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(f"/users/{user.id}")

            assert response.status_code == 403
            assert "insufficient privileges" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test deleting a non-existent user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            fake_id = uuid7()
            response = await client.delete(f"/users/{fake_id}")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_hard_delete_user_not_found(
        self,
        async_session: AsyncSession,
        mock_root_user: UserDetail,
    ):
        """Test hard deleting a non-existent user."""
        from app.core.db.database import get_db

        app = FastAPI()
        app.include_router(router)

        async def override_get_db():
            yield async_session

        async def override_get_current_user():
            return mock_root_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            fake_id = uuid7()
            response = await client.delete(f"/users/{fake_id}?hard_delete=true")

            assert response.status_code == 404
