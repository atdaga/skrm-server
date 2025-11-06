"""Unit tests for domain exception classes."""

from uuid import uuid4

import pytest

from app.core.exceptions.domain_exceptions import (
    DomainException,
    InsufficientPrivilegesException,
    InvalidCredentialsException,
    InvalidTokenException,
    InvalidUserIdException,
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationUpdateConflictException,
    TeamAlreadyExistsException,
    TeamMemberAlreadyExistsException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
    TeamReviewerAlreadyExistsException,
    TeamReviewerNotFoundException,
    TeamUpdateConflictException,
    TokenNotFoundException,
    UserNotFoundException,
)


class TestDomainException:
    """Test suite for base DomainException."""

    def test_domain_exception_with_all_params(self):
        """Test DomainException with all parameters."""
        exception = DomainException(
            message="Test error", entity_type="test", entity_id="123"
        )

        assert exception.message == "Test error"
        assert exception.entity_type == "test"
        assert exception.entity_id == "123"
        assert str(exception) == "Test error"

    def test_domain_exception_minimal(self):
        """Test DomainException with only message."""
        exception = DomainException("Minimal error")

        assert exception.message == "Minimal error"
        assert exception.entity_type is None
        assert exception.entity_id is None


class TestTeamExceptions:
    """Test suite for team-related exceptions."""

    def test_team_not_found_exception(self):
        """Test TeamNotFoundException with team ID and scope."""
        team_id = uuid4()
        exception = TeamNotFoundException(team_id=team_id, scope="test-scope")

        assert exception.team_id == team_id
        assert exception.scope == "test-scope"
        assert str(team_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team"
        assert exception.entity_id == team_id

    def test_team_not_found_exception_without_scope(self):
        """Test TeamNotFoundException without scope."""
        team_id = uuid4()
        exception = TeamNotFoundException(team_id=team_id)

        assert exception.team_id == team_id
        assert exception.scope is None
        assert str(team_id) in exception.message

    def test_team_already_exists_exception(self):
        """Test TeamAlreadyExistsException."""
        exception = TeamAlreadyExistsException(name="TestTeam", scope="test-scope")

        assert exception.name == "TestTeam"
        assert exception.scope == "test-scope"
        assert "TestTeam" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team"

    def test_team_update_conflict_exception(self):
        """Test TeamUpdateConflictException."""
        team_id = uuid4()
        exception = TeamUpdateConflictException(
            team_id=team_id, name="ConflictName", scope="test-scope"
        )

        assert exception.team_id == team_id
        assert exception.name == "ConflictName"
        assert exception.scope == "test-scope"
        assert "ConflictName" in exception.message
        assert exception.entity_type == "team"


class TestUserExceptions:
    """Test suite for user-related exceptions."""

    def test_user_not_found_with_user_id(self):
        """Test UserNotFoundException with user_id parameter."""
        user_id = uuid4()
        exception = UserNotFoundException(user_id=user_id)

        assert exception.user_id == user_id
        assert exception.username is None
        assert str(user_id) in exception.message
        assert exception.entity_type == "user"
        assert exception.entity_id == user_id

    def test_user_not_found_with_username(self):
        """Test UserNotFoundException with username parameter."""
        exception = UserNotFoundException(username="testuser")

        assert exception.user_id is None
        assert exception.username == "testuser"
        assert "testuser" in exception.message
        assert exception.entity_type == "user"
        assert exception.entity_id == "testuser"

    def test_user_not_found_with_no_params(self):
        """Test UserNotFoundException with no parameters."""
        exception = UserNotFoundException()

        assert exception.user_id is None
        assert exception.username is None
        assert exception.message == "User not found"
        assert exception.entity_type == "user"
        assert exception.entity_id is None

    def test_invalid_user_id_exception(self):
        """Test InvalidUserIdException."""
        exception = InvalidUserIdException(user_id_str="not-a-uuid")

        assert exception.user_id_str == "not-a-uuid"
        assert "not-a-uuid" in exception.message
        assert exception.entity_type == "user"

    def test_invalid_credentials_exception_with_username(self):
        """Test InvalidCredentialsException with username."""
        exception = InvalidCredentialsException(username="testuser")

        assert exception.username == "testuser"
        assert "Invalid username or password" in exception.message
        assert exception.entity_type == "user"

    def test_invalid_credentials_exception_without_username(self):
        """Test InvalidCredentialsException without username."""
        exception = InvalidCredentialsException()

        assert exception.username is None
        assert "Invalid username or password" in exception.message


class TestAuthorizationExceptions:
    """Test suite for authorization-related exceptions."""

    def test_insufficient_privileges_with_all_params(self):
        """Test InsufficientPrivilegesException with all parameters."""
        user_id = uuid4()
        exception = InsufficientPrivilegesException(
            required_privilege="superuser", user_id=user_id
        )

        assert exception.required_privilege == "superuser"
        assert exception.user_id == user_id
        assert "superuser" in exception.message
        assert exception.entity_type == "authorization"

    def test_insufficient_privileges_without_params(self):
        """Test InsufficientPrivilegesException without parameters."""
        exception = InsufficientPrivilegesException()

        assert exception.required_privilege is None
        assert exception.user_id is None
        assert exception.message == "Insufficient privileges"

    def test_invalid_token_with_reason(self):
        """Test InvalidTokenException with reason."""
        exception = InvalidTokenException(reason="Token expired")

        assert exception.reason == "Token expired"
        assert "Token expired" in exception.message
        assert exception.entity_type == "authorization"

    def test_invalid_token_without_reason(self):
        """Test InvalidTokenException without reason."""
        exception = InvalidTokenException()

        assert exception.reason is None
        assert exception.message == "Invalid or expired token"

    def test_token_not_found_exception(self):
        """Test TokenNotFoundException."""
        exception = TokenNotFoundException()

        assert exception.message == "Authentication token not provided"
        assert exception.entity_type == "authorization"


class TestExceptionRaising:
    """Test that exceptions can be raised and caught correctly."""

    def test_raise_team_not_found(self):
        """Test raising TeamNotFoundException."""
        team_id = uuid4()
        with pytest.raises(TeamNotFoundException) as exc_info:
            raise TeamNotFoundException(team_id=team_id, scope="test")

        assert exc_info.value.team_id == team_id

    def test_raise_user_not_found(self):
        """Test raising UserNotFoundException."""
        with pytest.raises(UserNotFoundException) as exc_info:
            raise UserNotFoundException(username="nonexistent")

        assert exc_info.value.username == "nonexistent"

    def test_raise_invalid_credentials(self):
        """Test raising InvalidCredentialsException."""
        with pytest.raises(InvalidCredentialsException) as exc_info:
            raise InvalidCredentialsException(username="baduser")

        assert exc_info.value.username == "baduser"

    def test_raise_token_not_found(self):
        """Test raising TokenNotFoundException."""
        with pytest.raises(TokenNotFoundException):
            raise TokenNotFoundException()

    def test_catch_as_domain_exception(self):
        """Test that all domain exceptions can be caught as DomainException."""
        # Test TeamNotFoundException
        with pytest.raises(DomainException):
            raise TeamNotFoundException(team_id=uuid4())

        # Test UserNotFoundException
        with pytest.raises(DomainException):
            raise UserNotFoundException()

        # Test TokenNotFoundException
        with pytest.raises(DomainException):
            raise TokenNotFoundException()


class TestOrganizationExceptions:
    """Test suite for organization-related exceptions."""

    def test_organization_not_found_exception_with_scope(self):
        """Test OrganizationNotFoundException with scope."""
        org_id = uuid4()
        exception = OrganizationNotFoundException(org_id=org_id, scope="test-scope")

        assert exception.org_id == org_id
        assert exception.scope == "test-scope"
        assert str(org_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "organization"
        assert exception.entity_id == org_id

    def test_organization_not_found_exception_without_scope(self):
        """Test OrganizationNotFoundException without scope."""
        org_id = uuid4()
        exception = OrganizationNotFoundException(org_id=org_id)

        assert exception.org_id == org_id
        assert exception.scope is None
        assert str(org_id) in exception.message
        assert "in scope" not in exception.message

    def test_organization_already_exists_exception_with_scope(self):
        """Test OrganizationAlreadyExistsException with scope."""
        exception = OrganizationAlreadyExistsException(
            identifier="test-org", identifier_type="name", scope="test-scope"
        )

        assert exception.identifier == "test-org"
        assert exception.identifier_type == "name"
        assert exception.scope == "test-scope"
        assert "test-org" in exception.message
        assert "name" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "organization"

    def test_organization_already_exists_exception_without_scope(self):
        """Test OrganizationAlreadyExistsException without scope."""
        exception = OrganizationAlreadyExistsException(
            identifier="test-alias", identifier_type="alias"
        )

        assert exception.identifier == "test-alias"
        assert exception.identifier_type == "alias"
        assert exception.scope is None
        assert "test-alias" in exception.message
        assert "in scope" not in exception.message

    def test_organization_update_conflict_exception_with_scope(self):
        """Test OrganizationUpdateConflictException with scope."""
        org_id = uuid4()
        exception = OrganizationUpdateConflictException(
            org_id=org_id,
            identifier="conflict-name",
            identifier_type="name",
            scope="test-scope",
        )

        assert exception.org_id == org_id
        assert exception.identifier == "conflict-name"
        assert exception.identifier_type == "name"
        assert exception.scope == "test-scope"
        assert str(org_id) in exception.message
        assert "conflict-name" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "organization"

    def test_organization_update_conflict_exception_without_scope(self):
        """Test OrganizationUpdateConflictException without scope."""
        org_id = uuid4()
        exception = OrganizationUpdateConflictException(
            org_id=org_id, identifier="conflict-alias", identifier_type="alias"
        )

        assert exception.org_id == org_id
        assert exception.identifier == "conflict-alias"
        assert exception.identifier_type == "alias"
        assert exception.scope is None
        assert "in scope" not in exception.message


class TestTeamMemberExceptions:
    """Test suite for team member-related exceptions."""

    def test_team_member_not_found_exception_with_scope(self):
        """Test TeamMemberNotFoundException with scope."""
        team_id = uuid4()
        principal_id = uuid4()
        exception = TeamMemberNotFoundException(
            team_id=team_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(team_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team_member"

    def test_team_member_not_found_exception_without_scope(self):
        """Test TeamMemberNotFoundException without scope."""
        team_id = uuid4()
        principal_id = uuid4()
        exception = TeamMemberNotFoundException(
            team_id=team_id, principal_id=principal_id
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_team_member_already_exists_exception(self):
        """Test TeamMemberAlreadyExistsException."""
        team_id = uuid4()
        principal_id = uuid4()
        exception = TeamMemberAlreadyExistsException(
            team_id=team_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(team_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team_member"


class TestTeamReviewerExceptions:
    """Test suite for team reviewer-related exceptions."""

    def test_team_reviewer_not_found_exception_with_scope(self):
        """Test TeamReviewerNotFoundException with scope."""
        team_id = uuid4()
        principal_id = uuid4()
        exception = TeamReviewerNotFoundException(
            team_id=team_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(team_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team_reviewer"

    def test_team_reviewer_not_found_exception_without_scope(self):
        """Test TeamReviewerNotFoundException without scope."""
        team_id = uuid4()
        principal_id = uuid4()
        exception = TeamReviewerNotFoundException(
            team_id=team_id, principal_id=principal_id
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_team_reviewer_already_exists_exception(self):
        """Test TeamReviewerAlreadyExistsException."""
        team_id = uuid4()
        principal_id = uuid4()
        exception = TeamReviewerAlreadyExistsException(
            team_id=team_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(team_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team_reviewer"
