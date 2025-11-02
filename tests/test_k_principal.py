"""Unit tests for KPrincipal model."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from app.models.k_principal import KPrincipal


class TestKPrincipalModel:
    """Test suite for KPrincipal model."""

    def test_create_principal_with_required_fields(self, session: Session, creator_id: UUID):
        """Test creating a principal with only required fields."""
        principal = KPrincipal(
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.id is not None
        assert isinstance(principal.id, UUID)
        assert principal.username == "testuser"
        assert principal.primary_email == "test@example.com"
        assert principal.first_name == "Test"
        assert principal.last_name == "User"
        assert principal.display_name == "Test User"

    def test_principal_default_values(self, session: Session, creator_id: UUID):
        """Test that default values are set correctly."""
        principal = KPrincipal(
            username="testuser",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.scope == "global"
        assert principal.primary_email_verified is False
        assert principal.primary_phone is None
        assert principal.primary_phone_verified is False
        assert principal.human is True
        assert principal.enabled is True
        assert principal.time_zone == "UTC"
        assert principal.name_prefix is None
        assert principal.middle_name is None
        assert principal.name_suffix is None
        assert principal.default_locale == "en"
        assert principal.system_role == "system_user"
        assert principal.meta == {}
        assert isinstance(principal.created, datetime)
        assert isinstance(principal.last_modified, datetime)

    def test_principal_with_all_fields(self, session: Session, creator_id: UUID):
        """Test creating a principal with all fields populated."""
        principal = KPrincipal(
            scope="tenant1",
            username="jdoe",
            primary_email="john.doe@example.com",
            primary_email_verified=True,
            primary_phone="+1234567890",
            primary_phone_verified=True,
            human=True,
            enabled=True,
            time_zone="America/New_York",
            name_prefix="Dr.",
            first_name="John",
            middle_name="Michael",
            last_name="Doe",
            name_suffix="Jr.",
            display_name="Dr. John Doe Jr.",
            default_locale="en-US",
            system_role="admin",
            meta={"department": "Engineering", "employee_id": "12345"},
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.scope == "tenant1"
        assert principal.username == "jdoe"
        assert principal.primary_email == "john.doe@example.com"
        assert principal.primary_email_verified is True
        assert principal.primary_phone == "+1234567890"
        assert principal.primary_phone_verified is True
        assert principal.time_zone == "America/New_York"
        assert principal.name_prefix == "Dr."
        assert principal.first_name == "John"
        assert principal.middle_name == "Michael"
        assert principal.last_name == "Doe"
        assert principal.name_suffix == "Jr."
        assert principal.display_name == "Dr. John Doe Jr."
        assert principal.default_locale == "en-US"
        assert principal.system_role == "admin"
        assert principal.meta == {"department": "Engineering", "employee_id": "12345"}

    def test_principal_unique_constraint(self, session: Session, creator_id: UUID):
        """Test that scope+username combination must be unique."""
        principal1 = KPrincipal(
            scope="global",
            username="testuser",
            primary_email="test1@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User 1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal1)
        session.commit()

        # Try to create another principal with same scope+username
        principal2 = KPrincipal(
            scope="global",
            username="testuser",
            primary_email="test2@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User 2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal2)
        with pytest.raises(Exception):  # Should raise IntegrityError
            session.commit()

    def test_principal_same_username_different_scope(self, session: Session, creator_id: UUID):
        """Test that same username can exist in different scopes."""
        principal1 = KPrincipal(
            scope="tenant1",
            username="testuser",
            primary_email="test1@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User 1",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        principal2 = KPrincipal(
            scope="tenant2",
            username="testuser",
            primary_email="test2@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User 2",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal1)
        session.add(principal2)
        session.commit()

        # Both should exist
        principals = session.exec(select(KPrincipal)).all()
        assert len(principals) == 2

    def test_principal_query(self, session: Session, creator_id: UUID):
        """Test querying principals from database."""
        principal = KPrincipal(
            username="querytest",
            primary_email="query@example.com",
            first_name="Query",
            last_name="Test",
            display_name="Query Test",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()

        # Query by username
        result = session.exec(
            select(KPrincipal).where(KPrincipal.username == "querytest")
        ).first()

        assert result is not None
        assert result.username == "querytest"
        assert result.primary_email == "query@example.com"

    def test_principal_update(self, session: Session, creator_id: UUID):
        """Test updating principal fields."""
        principal = KPrincipal(
            username="updatetest",
            primary_email="update@example.com",
            first_name="Update",
            last_name="Test",
            display_name="Update Test",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        # Update fields
        principal.primary_email_verified = True
        principal.primary_phone = "+9876543210"
        principal.time_zone = "Europe/London"
        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.primary_email_verified is True
        assert principal.primary_phone == "+9876543210"
        assert principal.time_zone == "Europe/London"

    def test_principal_delete(self, session: Session, creator_id: UUID):
        """Test deleting a principal."""
        principal = KPrincipal(
            username="deletetest",
            primary_email="delete@example.com",
            first_name="Delete",
            last_name="Test",
            display_name="Delete Test",
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        principal_id = principal.id

        # Delete the principal
        session.delete(principal)
        session.commit()

        # Verify it's deleted
        result = session.get(KPrincipal, principal_id)
        assert result is None

    def test_principal_meta_json_field(self, session: Session, creator_id: UUID):
        """Test that meta field correctly stores and retrieves JSON data."""
        meta_data = {
            "custom_field": "value",
            "nested": {"key": "value"},
            "array": [1, 2, 3],
        }

        principal = KPrincipal(
            username="metatest",
            primary_email="meta@example.com",
            first_name="Meta",
            last_name="Test",
            display_name="Meta Test",
            meta=meta_data,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.meta == meta_data
        assert principal.meta["custom_field"] == "value"
        assert principal.meta["nested"]["key"] == "value"
        assert principal.meta["array"] == [1, 2, 3]

    def test_principal_disabled_flag(self, session: Session, creator_id: UUID):
        """Test that principals can be disabled."""
        principal = KPrincipal(
            username="disabletest",
            primary_email="disable@example.com",
            first_name="Disable",
            last_name="Test",
            display_name="Disable Test",
            enabled=False,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.enabled is False

    def test_principal_non_human_flag(self, session: Session, creator_id: UUID):
        """Test creating a non-human principal (service account)."""
        principal = KPrincipal(
            username="service.bot",
            primary_email="bot@example.com",
            first_name="Service",
            last_name="Bot",
            display_name="Service Bot",
            human=False,
            created_by=creator_id,
            last_modified_by=creator_id,
        )

        session.add(principal)
        session.commit()
        session.refresh(principal)

        assert principal.human is False
