"""Domain-specific exceptions for business logic layer.

These exceptions are raised by the logic layer and translated to HTTP exceptions
by the route handlers. This allows business logic to remain independent of HTTP concerns.
"""

from typing import Any
from uuid import UUID


class DomainException(Exception):
    """Base class for all domain exceptions."""

    def __init__(
        self, message: str, entity_type: str | None = None, entity_id: Any | None = None
    ):
        """Initialize domain exception.

        Args:
            message: Human-readable error message
            entity_type: Type of entity involved (e.g., 'team', 'user')
            entity_id: ID of the entity involved (if applicable)
        """
        super().__init__(message)
        self.message = message
        self.entity_type = entity_type
        self.entity_id = entity_id


# ============================================================================
# Team-related exceptions
# ============================================================================


class TeamNotFoundException(DomainException):
    """Raised when a team cannot be found."""

    def __init__(self, team_id: UUID, scope: str | None = None):
        message = f"Team with id '{team_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="team", entity_id=team_id)
        self.team_id = team_id
        self.scope = scope


class TeamAlreadyExistsException(DomainException):
    """Raised when attempting to create a team that already exists."""

    def __init__(self, name: str, scope: str):
        message = f"Team with name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="team", entity_id=name)
        self.name = name
        self.scope = scope


class TeamUpdateConflictException(DomainException):
    """Raised when updating a team causes a naming conflict."""

    def __init__(self, team_id: UUID, name: str, scope: str):
        message = f"Cannot update team '{team_id}': name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="team", entity_id=team_id)
        self.team_id = team_id
        self.name = name
        self.scope = scope


# ============================================================================
# Project-related exceptions
# ============================================================================


class ProjectNotFoundException(DomainException):
    """Raised when a project cannot be found."""

    def __init__(self, project_id: UUID, scope: str | None = None):
        message = f"Project with id '{project_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="project", entity_id=project_id)
        self.project_id = project_id
        self.scope = scope


class ProjectAlreadyExistsException(DomainException):
    """Raised when attempting to create a project that already exists."""

    def __init__(self, name: str, scope: str):
        message = f"Project with name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="project", entity_id=name)
        self.name = name
        self.scope = scope


class ProjectUpdateConflictException(DomainException):
    """Raised when updating a project causes a naming conflict."""

    def __init__(self, project_id: UUID, name: str, scope: str):
        message = f"Cannot update project '{project_id}': name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="project", entity_id=project_id)
        self.project_id = project_id
        self.name = name
        self.scope = scope


# ============================================================================
# Project Team-related exceptions
# ============================================================================


class ProjectTeamNotFoundException(DomainException):
    """Raised when a project team cannot be found."""

    def __init__(self, project_id: UUID, team_id: UUID, scope: str | None = None):
        message = f"Project team with project_id '{project_id}' and team_id '{team_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="project_team", entity_id=team_id)
        self.project_id = project_id
        self.team_id = team_id
        self.scope = scope


class ProjectTeamAlreadyExistsException(DomainException):
    """Raised when attempting to add a project team that already exists."""

    def __init__(self, project_id: UUID, team_id: UUID, scope: str):
        message = f"Project team with project_id '{project_id}' and team_id '{team_id}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="project_team", entity_id=team_id)
        self.project_id = project_id
        self.team_id = team_id
        self.scope = scope


# ============================================================================
# Organization-related exceptions
# ============================================================================


class OrganizationNotFoundException(DomainException):
    """Raised when an organization cannot be found."""

    def __init__(self, org_id: UUID, scope: str | None = None):
        message = f"Organization with id '{org_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="organization", entity_id=org_id)
        self.org_id = org_id
        self.scope = scope


class OrganizationAlreadyExistsException(DomainException):
    """Raised when attempting to create an organization that already exists."""

    def __init__(self, identifier: str, identifier_type: str, scope: str | None = None):
        message = f"Organization with {identifier_type} '{identifier}' already exists"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="organization", entity_id=identifier)
        self.identifier = identifier
        self.identifier_type = identifier_type
        self.scope = scope


class OrganizationUpdateConflictException(DomainException):
    """Raised when updating an organization causes a naming conflict."""

    def __init__(
        self,
        org_id: UUID,
        identifier: str,
        identifier_type: str,
        scope: str | None = None,
    ):
        message = f"Cannot update organization '{org_id}': {identifier_type} '{identifier}' already exists"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="organization", entity_id=org_id)
        self.org_id = org_id
        self.identifier = identifier
        self.identifier_type = identifier_type
        self.scope = scope


# ============================================================================
# User/Principal-related exceptions
# ============================================================================


class UserNotFoundException(DomainException):
    """Raised when a user cannot be found."""

    def __init__(self, user_id: UUID | None = None, username: str | None = None):
        entity_id: UUID | str | None
        if user_id:
            message = f"User with id '{user_id}' not found"
            entity_id = user_id
        elif username:
            message = f"User with username '{username}' not found"
            entity_id = username
        else:
            message = "User not found"
            entity_id = None
        super().__init__(message, entity_type="user", entity_id=entity_id)
        self.user_id = user_id
        self.username = username


class InvalidUserIdException(DomainException):
    """Raised when a user ID is invalid or malformed."""

    def __init__(self, user_id_str: str):
        message = f"Invalid user ID format: '{user_id_str}'"
        super().__init__(message, entity_type="user", entity_id=user_id_str)
        self.user_id_str = user_id_str


class InvalidCredentialsException(DomainException):
    """Raised when authentication credentials are invalid."""

    def __init__(self, username: str | None = None):
        message = "Invalid username or password"
        super().__init__(message, entity_type="user", entity_id=username)
        self.username = username


# ============================================================================
# Authorization-related exceptions
# ============================================================================


class InsufficientPrivilegesException(DomainException):
    """Raised when a user lacks required privileges for an operation."""

    def __init__(
        self, required_privilege: str | None = None, user_id: UUID | None = None
    ):
        message = "Insufficient privileges"
        if required_privilege:
            message += f": requires '{required_privilege}'"
        super().__init__(message, entity_type="authorization", entity_id=user_id)
        self.required_privilege = required_privilege
        self.user_id = user_id


class InvalidTokenException(DomainException):
    """Raised when a token is invalid or cannot be verified."""

    def __init__(self, reason: str | None = None):
        message = "Invalid or expired token"
        if reason:
            message += f": {reason}"
        super().__init__(message, entity_type="authorization")
        self.reason = reason


class TokenNotFoundException(DomainException):
    """Raised when no token is provided."""

    def __init__(self) -> None:
        super().__init__(
            "Authentication token not provided", entity_type="authorization"
        )


# ============================================================================
# Team Member-related exceptions
# ============================================================================


class TeamMemberNotFoundException(DomainException):
    """Raised when a team member cannot be found."""

    def __init__(self, team_id: UUID, principal_id: UUID, scope: str | None = None):
        message = f"Team member with team_id '{team_id}' and principal_id '{principal_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="team_member", entity_id=principal_id)
        self.team_id = team_id
        self.principal_id = principal_id
        self.scope = scope


class TeamMemberAlreadyExistsException(DomainException):
    """Raised when attempting to add a team member that already exists."""

    def __init__(self, team_id: UUID, principal_id: UUID, scope: str):
        message = f"Team member with team_id '{team_id}' and principal_id '{principal_id}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="team_member", entity_id=principal_id)
        self.team_id = team_id
        self.principal_id = principal_id
        self.scope = scope


# ============================================================================
# Team Reviewer-related exceptions
# ============================================================================


class TeamReviewerNotFoundException(DomainException):
    """Raised when a team reviewer cannot be found."""

    def __init__(self, team_id: UUID, principal_id: UUID, scope: str | None = None):
        message = f"Team reviewer with team_id '{team_id}' and principal_id '{principal_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="team_reviewer", entity_id=principal_id)
        self.team_id = team_id
        self.principal_id = principal_id
        self.scope = scope


class TeamReviewerAlreadyExistsException(DomainException):
    """Raised when attempting to add a team reviewer that already exists."""

    def __init__(self, team_id: UUID, principal_id: UUID, scope: str):
        message = f"Team reviewer with team_id '{team_id}' and principal_id '{principal_id}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="team_reviewer", entity_id=principal_id)
        self.team_id = team_id
        self.principal_id = principal_id
        self.scope = scope


# ============================================================================
# Organization Principal-related exceptions
# ============================================================================


class OrganizationPrincipalNotFoundException(DomainException):
    """Raised when an organization principal cannot be found."""

    def __init__(self, org_id: UUID, principal_id: UUID, scope: str | None = None):
        message = f"Organization principal with org_id '{org_id}' and principal_id '{principal_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(
            message, entity_type="organization_principal", entity_id=principal_id
        )
        self.org_id = org_id
        self.principal_id = principal_id
        self.scope = scope


class OrganizationPrincipalAlreadyExistsException(DomainException):
    """Raised when attempting to add an organization principal that already exists."""

    def __init__(self, org_id: UUID, principal_id: UUID, scope: str):
        message = f"Organization principal with org_id '{org_id}' and principal_id '{principal_id}' already exists in scope '{scope}'"
        super().__init__(
            message, entity_type="organization_principal", entity_id=principal_id
        )
        self.org_id = org_id
        self.principal_id = principal_id
        self.scope = scope


class UnauthorizedOrganizationAccessException(DomainException):
    """Raised when a user attempts to access an organization they don't belong to."""

    def __init__(self, org_id: UUID, user_id: UUID):
        message = (
            f"User '{user_id}' is not authorized to access organization '{org_id}'"
        )
        super().__init__(message, entity_type="organization", entity_id=org_id)
        self.org_id = org_id
        self.user_id = user_id


# ============================================================================
# Doc-related exceptions
# ============================================================================


class DocNotFoundException(DomainException):
    """Raised when a doc cannot be found."""

    def __init__(self, doc_id: UUID, scope: str | None = None):
        message = f"Doc with id '{doc_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="doc", entity_id=doc_id)
        self.doc_id = doc_id
        self.scope = scope


class DocAlreadyExistsException(DomainException):
    """Raised when attempting to create a doc that already exists."""

    def __init__(self, name: str, scope: str):
        message = f"Doc with name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="doc", entity_id=name)
        self.name = name
        self.scope = scope


class DocUpdateConflictException(DomainException):
    """Raised when updating a doc causes a naming conflict."""

    def __init__(self, doc_id: UUID, name: str, scope: str):
        message = f"Cannot update doc '{doc_id}': name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="doc", entity_id=doc_id)
        self.doc_id = doc_id
        self.name = name
        self.scope = scope


# ============================================================================
# Deployment Environment-related exceptions
# ============================================================================


class DeploymentEnvNotFoundException(DomainException):
    """Raised when a deployment environment cannot be found."""

    def __init__(self, deployment_env_id: UUID, scope: str | None = None):
        message = f"Deployment environment with id '{deployment_env_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(
            message, entity_type="deployment_env", entity_id=deployment_env_id
        )
        self.deployment_env_id = deployment_env_id
        self.scope = scope


class DeploymentEnvAlreadyExistsException(DomainException):
    """Raised when attempting to create a deployment environment that already exists."""

    def __init__(self, name: str, scope: str):
        message = f"Deployment environment with name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="deployment_env", entity_id=name)
        self.name = name
        self.scope = scope


class DeploymentEnvUpdateConflictException(DomainException):
    """Raised when updating a deployment environment causes a naming conflict."""

    def __init__(self, deployment_env_id: UUID, name: str, scope: str):
        message = f"Cannot update deployment environment '{deployment_env_id}': name '{name}' already exists in scope '{scope}'"
        super().__init__(
            message, entity_type="deployment_env", entity_id=deployment_env_id
        )
        self.deployment_env_id = deployment_env_id
        self.name = name
        self.scope = scope


# ============================================================================
# Feature-related exceptions
# ============================================================================


class FeatureNotFoundException(DomainException):
    """Raised when a feature cannot be found."""

    def __init__(self, feature_id: UUID, scope: str | None = None):
        message = f"Feature with id '{feature_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="feature", entity_id=feature_id)
        self.feature_id = feature_id
        self.scope = scope


class FeatureAlreadyExistsException(DomainException):
    """Raised when attempting to create a feature that already exists."""

    def __init__(self, name: str, scope: str):
        message = f"Feature with name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="feature", entity_id=name)
        self.name = name
        self.scope = scope


class FeatureUpdateConflictException(DomainException):
    """Raised when updating a feature causes a naming conflict."""

    def __init__(self, feature_id: UUID, name: str, scope: str):
        message = f"Cannot update feature '{feature_id}': name '{name}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="feature", entity_id=feature_id)
        self.feature_id = feature_id
        self.name = name
        self.scope = scope


# ============================================================================
# Feature Doc-related exceptions
# ============================================================================


class FeatureDocNotFoundException(DomainException):
    """Raised when a feature doc relationship cannot be found."""

    def __init__(self, feature_id: UUID, doc_id: UUID, scope: str | None = None):
        message = f"Feature doc with feature_id '{feature_id}' and doc_id '{doc_id}' not found"
        if scope:
            message += f" in scope '{scope}'"
        super().__init__(message, entity_type="feature_doc", entity_id=doc_id)
        self.feature_id = feature_id
        self.doc_id = doc_id
        self.scope = scope


class FeatureDocAlreadyExistsException(DomainException):
    """Raised when attempting to add a feature doc relationship that already exists."""

    def __init__(self, feature_id: UUID, doc_id: UUID, scope: str):
        message = f"Feature doc with feature_id '{feature_id}' and doc_id '{doc_id}' already exists in scope '{scope}'"
        super().__init__(message, entity_type="feature_doc", entity_id=doc_id)
        self.feature_id = feature_id
        self.doc_id = doc_id
        self.scope = scope
