"""Unit tests for domain exception classes."""

from uuid import uuid7

import pytest

from app.core.exceptions.domain_exceptions import (
    DeploymentEnvAlreadyExistsException,
    DeploymentEnvNotFoundException,
    DeploymentEnvUpdateConflictException,
    DocAlreadyExistsException,
    DocNotFoundException,
    DocUpdateConflictException,
    DomainException,
    FeatureAlreadyExistsException,
    FeatureDocAlreadyExistsException,
    FeatureDocNotFoundException,
    FeatureNotFoundException,
    FeatureUpdateConflictException,
    InsufficientPrivilegesException,
    InvalidCredentialsException,
    InvalidTokenException,
    InvalidUserIdException,
    OrganizationAlreadyExistsException,
    OrganizationNotFoundException,
    OrganizationPrincipalAlreadyExistsException,
    OrganizationPrincipalNotFoundException,
    OrganizationUpdateConflictException,
    PrincipalNotFoundException,
    ProjectAlreadyExistsException,
    ProjectNotFoundException,
    ProjectTeamAlreadyExistsException,
    ProjectTeamNotFoundException,
    ProjectUpdateConflictException,
    TaskDeploymentEnvAlreadyExistsException,
    TaskDeploymentEnvNotFoundException,
    TaskFeatureAlreadyExistsException,
    TaskFeatureNotFoundException,
    TaskOwnerAlreadyExistsException,
    TaskOwnerNotFoundException,
    TaskReviewerAlreadyExistsException,
    TaskReviewerNotFoundException,
    TeamAlreadyExistsException,
    TeamMemberAlreadyExistsException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
    TeamReviewerAlreadyExistsException,
    TeamReviewerNotFoundException,
    TeamUpdateConflictException,
    TokenNotFoundException,
    UnauthorizedOrganizationAccessException,
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
        team_id = uuid7()
        exception = TeamNotFoundException(team_id=team_id, scope="test-scope")

        assert exception.team_id == team_id
        assert exception.scope == "test-scope"
        assert str(team_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "team"
        assert exception.entity_id == team_id

    def test_team_not_found_exception_without_scope(self):
        """Test TeamNotFoundException without scope."""
        team_id = uuid7()
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
        team_id = uuid7()
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
        user_id = uuid7()
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
        user_id = uuid7()
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
        team_id = uuid7()
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

    def test_raise_project_not_found(self):
        """Test raising ProjectNotFoundException."""
        project_id = uuid7()
        with pytest.raises(ProjectNotFoundException) as exc_info:
            raise ProjectNotFoundException(project_id=project_id, scope="test")

        assert exc_info.value.project_id == project_id

    def test_raise_project_team_not_found(self):
        """Test raising ProjectTeamNotFoundException."""
        project_id = uuid7()
        team_id = uuid7()
        with pytest.raises(ProjectTeamNotFoundException) as exc_info:
            raise ProjectTeamNotFoundException(
                project_id=project_id, team_id=team_id, scope="test"
            )

        assert exc_info.value.project_id == project_id
        assert exc_info.value.team_id == team_id

    def test_catch_as_domain_exception(self):
        """Test that all domain exceptions can be caught as DomainException."""
        # Test TeamNotFoundException
        with pytest.raises(DomainException):
            raise TeamNotFoundException(team_id=uuid7())

        # Test UserNotFoundException
        with pytest.raises(DomainException):
            raise UserNotFoundException()

        # Test TokenNotFoundException
        with pytest.raises(DomainException):
            raise TokenNotFoundException()

        # Test ProjectNotFoundException
        with pytest.raises(DomainException):
            raise ProjectNotFoundException(project_id=uuid7())

        # Test ProjectTeamNotFoundException
        with pytest.raises(DomainException):
            raise ProjectTeamNotFoundException(project_id=uuid7(), team_id=uuid7())


class TestOrganizationExceptions:
    """Test suite for organization-related exceptions."""

    def test_organization_not_found_exception_with_scope(self):
        """Test OrganizationNotFoundException with scope."""
        org_id = uuid7()
        exception = OrganizationNotFoundException(org_id=org_id, scope="test-scope")

        assert exception.org_id == org_id
        assert exception.scope == "test-scope"
        assert str(org_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "organization"
        assert exception.entity_id == org_id

    def test_organization_not_found_exception_without_scope(self):
        """Test OrganizationNotFoundException without scope."""
        org_id = uuid7()
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
        org_id = uuid7()
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
        org_id = uuid7()
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
        team_id = uuid7()
        principal_id = uuid7()
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
        team_id = uuid7()
        principal_id = uuid7()
        exception = TeamMemberNotFoundException(
            team_id=team_id, principal_id=principal_id
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_team_member_already_exists_exception(self):
        """Test TeamMemberAlreadyExistsException."""
        team_id = uuid7()
        principal_id = uuid7()
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
        team_id = uuid7()
        principal_id = uuid7()
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
        team_id = uuid7()
        principal_id = uuid7()
        exception = TeamReviewerNotFoundException(
            team_id=team_id, principal_id=principal_id
        )

        assert exception.team_id == team_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_team_reviewer_already_exists_exception(self):
        """Test TeamReviewerAlreadyExistsException."""
        team_id = uuid7()
        principal_id = uuid7()
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


class TestOrganizationPrincipalExceptions:
    """Test suite for organization principal-related exceptions."""

    def test_organization_principal_not_found_exception_with_scope(self):
        """Test OrganizationPrincipalNotFoundException with scope."""
        org_id = uuid7()
        principal_id = uuid7()
        exception = OrganizationPrincipalNotFoundException(
            org_id=org_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.org_id == org_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(org_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "organization_principal"

    def test_organization_principal_not_found_exception_without_scope(self):
        """Test OrganizationPrincipalNotFoundException without scope."""
        org_id = uuid7()
        principal_id = uuid7()
        exception = OrganizationPrincipalNotFoundException(
            org_id=org_id, principal_id=principal_id
        )

        assert exception.org_id == org_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_organization_principal_already_exists_exception(self):
        """Test OrganizationPrincipalAlreadyExistsException."""
        org_id = uuid7()
        principal_id = uuid7()
        exception = OrganizationPrincipalAlreadyExistsException(
            org_id=org_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.org_id == org_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(org_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "organization_principal"

    def test_unauthorized_organization_access_exception(self):
        """Test UnauthorizedOrganizationAccessException."""
        org_id = uuid7()
        user_id = uuid7()
        exception = UnauthorizedOrganizationAccessException(
            org_id=org_id, user_id=user_id
        )

        assert exception.org_id == org_id
        assert exception.user_id == user_id
        assert str(org_id) in exception.message
        assert str(user_id) in exception.message
        assert "not authorized" in exception.message.lower()
        assert exception.entity_type == "organization"


class TestProjectExceptions:
    """Test suite for project-related exceptions."""

    def test_project_not_found_exception_with_scope(self):
        """Test ProjectNotFoundException with scope."""
        project_id = uuid7()
        exception = ProjectNotFoundException(project_id=project_id, scope="test-scope")

        assert exception.project_id == project_id
        assert exception.scope == "test-scope"
        assert str(project_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "project"
        assert exception.entity_id == project_id

    def test_project_not_found_exception_without_scope(self):
        """Test ProjectNotFoundException without scope."""
        project_id = uuid7()
        exception = ProjectNotFoundException(project_id=project_id)

        assert exception.project_id == project_id
        assert exception.scope is None
        assert str(project_id) in exception.message
        assert "in scope" not in exception.message

    def test_project_already_exists_exception(self):
        """Test ProjectAlreadyExistsException."""
        exception = ProjectAlreadyExistsException(
            name="TestProject", scope="test-scope"
        )

        assert exception.name == "TestProject"
        assert exception.scope == "test-scope"
        assert "TestProject" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "project"

    def test_project_update_conflict_exception(self):
        """Test ProjectUpdateConflictException."""
        project_id = uuid7()
        exception = ProjectUpdateConflictException(
            project_id=project_id, name="ConflictName", scope="test-scope"
        )

        assert exception.project_id == project_id
        assert exception.name == "ConflictName"
        assert exception.scope == "test-scope"
        assert str(project_id) in exception.message
        assert "ConflictName" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "project"


class TestProjectTeamExceptions:
    """Test suite for project team-related exceptions."""

    def test_project_team_not_found_exception_with_scope(self):
        """Test ProjectTeamNotFoundException with scope."""
        project_id = uuid7()
        team_id = uuid7()
        exception = ProjectTeamNotFoundException(
            project_id=project_id, team_id=team_id, scope="test-scope"
        )

        assert exception.project_id == project_id
        assert exception.team_id == team_id
        assert exception.scope == "test-scope"
        assert str(project_id) in exception.message
        assert str(team_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "project_team"

    def test_project_team_not_found_exception_without_scope(self):
        """Test ProjectTeamNotFoundException without scope."""
        project_id = uuid7()
        team_id = uuid7()
        exception = ProjectTeamNotFoundException(project_id=project_id, team_id=team_id)

        assert exception.project_id == project_id
        assert exception.team_id == team_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_project_team_already_exists_exception(self):
        """Test ProjectTeamAlreadyExistsException."""
        project_id = uuid7()
        team_id = uuid7()
        exception = ProjectTeamAlreadyExistsException(
            project_id=project_id, team_id=team_id, scope="test-scope"
        )

        assert exception.project_id == project_id
        assert exception.team_id == team_id
        assert exception.scope == "test-scope"
        assert str(project_id) in exception.message
        assert str(team_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "project_team"


class TestDocExceptions:
    """Test suite for doc-related exceptions."""

    def test_doc_not_found_exception_with_scope(self):
        """Test DocNotFoundException with scope."""
        doc_id = uuid7()
        exception = DocNotFoundException(doc_id=doc_id, scope="test-scope")

        assert exception.doc_id == doc_id
        assert exception.scope == "test-scope"
        assert str(doc_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "doc"
        assert exception.entity_id == doc_id

    def test_doc_not_found_exception_without_scope(self):
        """Test DocNotFoundException without scope."""
        doc_id = uuid7()
        exception = DocNotFoundException(doc_id=doc_id)

        assert exception.doc_id == doc_id
        assert exception.scope is None
        assert str(doc_id) in exception.message
        assert "in scope" not in exception.message

    def test_doc_already_exists_exception(self):
        """Test DocAlreadyExistsException."""
        exception = DocAlreadyExistsException(name="TestDoc", scope="test-scope")

        assert exception.name == "TestDoc"
        assert exception.scope == "test-scope"
        assert "TestDoc" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "doc"

    def test_doc_update_conflict_exception(self):
        """Test DocUpdateConflictException."""
        doc_id = uuid7()
        exception = DocUpdateConflictException(
            doc_id=doc_id, name="ConflictName", scope="test-scope"
        )

        assert exception.doc_id == doc_id
        assert exception.name == "ConflictName"
        assert exception.scope == "test-scope"
        assert str(doc_id) in exception.message
        assert "ConflictName" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "doc"


class TestDeploymentEnvExceptions:
    """Test suite for deployment environment-related exceptions."""

    def test_deployment_env_not_found_exception_with_scope(self):
        """Test DeploymentEnvNotFoundException with scope."""
        deployment_env_id = uuid7()
        exception = DeploymentEnvNotFoundException(
            deployment_env_id=deployment_env_id, scope="test-scope"
        )

        assert exception.deployment_env_id == deployment_env_id
        assert exception.scope == "test-scope"
        assert str(deployment_env_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "deployment_env"
        assert exception.entity_id == deployment_env_id

    def test_deployment_env_not_found_exception_without_scope(self):
        """Test DeploymentEnvNotFoundException without scope."""
        deployment_env_id = uuid7()
        exception = DeploymentEnvNotFoundException(deployment_env_id=deployment_env_id)

        assert exception.deployment_env_id == deployment_env_id
        assert exception.scope is None
        assert str(deployment_env_id) in exception.message
        assert "in scope" not in exception.message

    def test_deployment_env_already_exists_exception(self):
        """Test DeploymentEnvAlreadyExistsException."""
        exception = DeploymentEnvAlreadyExistsException(
            name="production", scope="test-scope"
        )

        assert exception.name == "production"
        assert exception.scope == "test-scope"
        assert "production" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "deployment_env"

    def test_deployment_env_update_conflict_exception(self):
        """Test DeploymentEnvUpdateConflictException."""
        deployment_env_id = uuid7()
        exception = DeploymentEnvUpdateConflictException(
            deployment_env_id=deployment_env_id, name="staging", scope="test-scope"
        )

        assert exception.deployment_env_id == deployment_env_id
        assert exception.name == "staging"
        assert exception.scope == "test-scope"
        assert str(deployment_env_id) in exception.message
        assert "staging" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "deployment_env"


class TestFeatureExceptions:
    """Test suite for feature-related exceptions."""

    def test_feature_not_found_exception_with_scope(self):
        """Test FeatureNotFoundException with scope."""
        feature_id = uuid7()
        exception = FeatureNotFoundException(feature_id=feature_id, scope="test-scope")

        assert exception.feature_id == feature_id
        assert exception.scope == "test-scope"
        assert str(feature_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "feature"
        assert exception.entity_id == feature_id

    def test_feature_not_found_exception_without_scope(self):
        """Test FeatureNotFoundException without scope."""
        feature_id = uuid7()
        exception = FeatureNotFoundException(feature_id=feature_id)

        assert exception.feature_id == feature_id
        assert exception.scope is None
        assert str(feature_id) in exception.message
        assert "in scope" not in exception.message

    def test_feature_already_exists_exception(self):
        """Test FeatureAlreadyExistsException."""
        exception = FeatureAlreadyExistsException(
            name="TestFeature", scope="test-scope"
        )

        assert exception.name == "TestFeature"
        assert exception.scope == "test-scope"
        assert "TestFeature" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "feature"

    def test_feature_update_conflict_exception(self):
        """Test FeatureUpdateConflictException."""
        feature_id = uuid7()
        exception = FeatureUpdateConflictException(
            feature_id=feature_id, name="ConflictName", scope="test-scope"
        )

        assert exception.feature_id == feature_id
        assert exception.name == "ConflictName"
        assert exception.scope == "test-scope"
        assert str(feature_id) in exception.message
        assert "ConflictName" in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "feature"


class TestFeatureDocExceptions:
    """Test suite for feature doc-related exceptions."""

    def test_feature_doc_not_found_exception_with_scope(self):
        """Test FeatureDocNotFoundException with scope."""
        feature_id = uuid7()
        doc_id = uuid7()
        exception = FeatureDocNotFoundException(
            feature_id=feature_id, doc_id=doc_id, scope="test-scope"
        )

        assert exception.feature_id == feature_id
        assert exception.doc_id == doc_id
        assert exception.scope == "test-scope"
        assert str(feature_id) in exception.message
        assert str(doc_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "feature_doc"

    def test_feature_doc_not_found_exception_without_scope(self):
        """Test FeatureDocNotFoundException without scope."""
        feature_id = uuid7()
        doc_id = uuid7()
        exception = FeatureDocNotFoundException(feature_id=feature_id, doc_id=doc_id)

        assert exception.feature_id == feature_id
        assert exception.doc_id == doc_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_feature_doc_already_exists_exception(self):
        """Test FeatureDocAlreadyExistsException."""
        feature_id = uuid7()
        doc_id = uuid7()
        exception = FeatureDocAlreadyExistsException(
            feature_id=feature_id, doc_id=doc_id, scope="test-scope"
        )

        assert exception.feature_id == feature_id
        assert exception.doc_id == doc_id
        assert exception.scope == "test-scope"
        assert str(feature_id) in exception.message
        assert str(doc_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "feature_doc"


class TestTaskDeploymentEnvExceptions:
    """Test suite for task deployment environment-related exceptions."""

    def test_task_deployment_env_not_found_exception_with_scope(self):
        """Test TaskDeploymentEnvNotFoundException with scope."""
        task_id = uuid7()
        deployment_env_id = uuid7()
        exception = TaskDeploymentEnvNotFoundException(
            task_id=task_id, deployment_env_id=deployment_env_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.deployment_env_id == deployment_env_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(deployment_env_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_deployment_env"

    def test_task_deployment_env_not_found_exception_without_scope(self):
        """Test TaskDeploymentEnvNotFoundException without scope."""
        task_id = uuid7()
        deployment_env_id = uuid7()
        exception = TaskDeploymentEnvNotFoundException(
            task_id=task_id, deployment_env_id=deployment_env_id
        )

        assert exception.task_id == task_id
        assert exception.deployment_env_id == deployment_env_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_task_deployment_env_already_exists_exception(self):
        """Test TaskDeploymentEnvAlreadyExistsException."""
        task_id = uuid7()
        deployment_env_id = uuid7()
        exception = TaskDeploymentEnvAlreadyExistsException(
            task_id=task_id, deployment_env_id=deployment_env_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.deployment_env_id == deployment_env_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(deployment_env_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_deployment_env"


class TestTaskFeatureExceptions:
    """Test suite for task feature-related exceptions."""

    def test_task_feature_not_found_exception_with_scope(self):
        """Test TaskFeatureNotFoundException with scope."""
        task_id = uuid7()
        feature_id = uuid7()
        exception = TaskFeatureNotFoundException(
            task_id=task_id, feature_id=feature_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.feature_id == feature_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(feature_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_feature"

    def test_task_feature_not_found_exception_without_scope(self):
        """Test TaskFeatureNotFoundException without scope."""
        task_id = uuid7()
        feature_id = uuid7()
        exception = TaskFeatureNotFoundException(task_id=task_id, feature_id=feature_id)

        assert exception.task_id == task_id
        assert exception.feature_id == feature_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_task_feature_already_exists_exception(self):
        """Test TaskFeatureAlreadyExistsException."""
        task_id = uuid7()
        feature_id = uuid7()
        exception = TaskFeatureAlreadyExistsException(
            task_id=task_id, feature_id=feature_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.feature_id == feature_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(feature_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_feature"


class TestPrincipalExceptions:
    """Test suite for principal-related exceptions."""

    def test_principal_not_found_exception_with_scope(self):
        """Test PrincipalNotFoundException with scope."""
        principal_id = uuid7()
        exception = PrincipalNotFoundException(
            principal_id=principal_id, scope="test-scope"
        )

        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "principal"

    def test_principal_not_found_exception_without_scope(self):
        """Test PrincipalNotFoundException without scope."""
        principal_id = uuid7()
        exception = PrincipalNotFoundException(principal_id=principal_id)

        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message


class TestTaskOwnerExceptions:
    """Test suite for task owner-related exceptions."""

    def test_task_owner_not_found_exception_with_scope(self):
        """Test TaskOwnerNotFoundException with scope."""
        task_id = uuid7()
        principal_id = uuid7()
        exception = TaskOwnerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_owner"

    def test_task_owner_not_found_exception_without_scope(self):
        """Test TaskOwnerNotFoundException without scope."""
        task_id = uuid7()
        principal_id = uuid7()
        exception = TaskOwnerNotFoundException(
            task_id=task_id, principal_id=principal_id
        )

        assert exception.task_id == task_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_task_owner_already_exists_exception(self):
        """Test TaskOwnerAlreadyExistsException."""
        task_id = uuid7()
        principal_id = uuid7()
        exception = TaskOwnerAlreadyExistsException(
            task_id=task_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_owner"


class TestTaskReviewerExceptions:
    """Test suite for task reviewer-related exceptions."""

    def test_task_reviewer_not_found_exception_with_scope(self):
        """Test TaskReviewerNotFoundException with scope."""
        task_id = uuid7()
        principal_id = uuid7()
        exception = TaskReviewerNotFoundException(
            task_id=task_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_reviewer"

    def test_task_reviewer_not_found_exception_without_scope(self):
        """Test TaskReviewerNotFoundException without scope."""
        task_id = uuid7()
        principal_id = uuid7()
        exception = TaskReviewerNotFoundException(
            task_id=task_id, principal_id=principal_id
        )

        assert exception.task_id == task_id
        assert exception.principal_id == principal_id
        assert exception.scope is None
        assert "in scope" not in exception.message

    def test_task_reviewer_already_exists_exception(self):
        """Test TaskReviewerAlreadyExistsException."""
        task_id = uuid7()
        principal_id = uuid7()
        exception = TaskReviewerAlreadyExistsException(
            task_id=task_id, principal_id=principal_id, scope="test-scope"
        )

        assert exception.task_id == task_id
        assert exception.principal_id == principal_id
        assert exception.scope == "test-scope"
        assert str(task_id) in exception.message
        assert str(principal_id) in exception.message
        assert "test-scope" in exception.message
        assert exception.entity_type == "task_reviewer"
