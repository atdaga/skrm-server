"""Business logic for dependency operations (user lookup, token verification, etc.)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import verify_token
from ..core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    InvalidTokenException,
    InvalidUserIdException,
    UnauthorizedOrganizationAccessException,
    UserNotFoundException,
)
from ..models import KOrganizationPrincipal, KPrincipal
from ..models.k_principal import SystemRole
from ..schemas.user import TokenData, UserDetail


async def get_token_data(token: str) -> TokenData:
    """Extract and validate token data.

    Args:
        token: JWT token string

    Returns:
        Token data with all JWT claims

    Raises:
        InvalidTokenException: If token is invalid or expired
    """
    payload = await verify_token(token)
    if payload is None:
        raise InvalidTokenException(reason="Token verification failed")

    # TODO: Check blacklist of tokens or principal IDs.

    # Convert Unix timestamps back to datetime objects
    iat = datetime.fromtimestamp(payload["iat"], tz=UTC).replace(tzinfo=None)
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC).replace(tzinfo=None)
    ss = datetime.fromtimestamp(payload["ss"], tz=UTC).replace(tzinfo=None)

    return TokenData(
        sub=payload["sub"],
        scope=payload["scope"],
        iss=payload["iss"],
        aud=payload["aud"],
        jti=payload["jti"],
        iat=iat,
        exp=exp,
        ss=ss,
    )


async def get_user_by_id(user_id: UUID, db: AsyncSession) -> UserDetail:
    """Get a user by their ID.

    Args:
        user_id: UUID of the user
        db: Database session

    Returns:
        User detail model

    Raises:
        UserNotFoundException: If user is not found in database
    """
    stmt = select(KPrincipal).where(KPrincipal.id == user_id, KPrincipal.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    return UserDetail.model_validate(user)


async def get_user_from_token(token: str, db: AsyncSession) -> UserDetail:
    """Get user from a JWT token.

    Args:
        token: JWT token string
        db: Database session

    Returns:
        User detail model

    Raises:
        InvalidTokenException: If token is invalid
        InvalidUserIdException: If user ID in token is malformed
        UserNotFoundException: If user is not found
    """
    payload = await verify_token(token)
    if payload is None:
        raise InvalidTokenException(reason="Token verification failed")

    user_id_str = payload.get("sub")
    try:
        user_id = UUID(user_id_str)
    except (ValueError, TypeError) as e:
        raise InvalidUserIdException(user_id_str=str(user_id_str)) from e

    return await get_user_by_id(user_id, db)


def check_superuser_privileges(user: UserDetail) -> None:
    """Check if user has superuser privileges.

    Args:
        user: User to check privileges for

    Raises:
        InsufficientPrivilegesException: If user is not a superuser
    """
    is_superuser = user.meta.get("is_superuser", False) if user.meta else False
    if not is_superuser:
        raise InsufficientPrivilegesException(
            required_privilege="superuser",
            user_id=user.id,
        )


def check_system_user_role(user: UserDetail) -> None:
    """Check if user has system user role or higher.

    Allows users with the following roles:
    - SYSTEM
    - SYSTEM_ROOT
    - SYSTEM_ADMIN
    - SYSTEM_USER

    Does not allow:
    - SYSTEM_CLIENT

    Args:
        user: User to check role for

    Raises:
        InsufficientPrivilegesException: If user does not have system user role or higher
    """
    allowed_roles = {
        SystemRole.SYSTEM,
        SystemRole.SYSTEM_ROOT,
        SystemRole.SYSTEM_ADMIN,
        SystemRole.SYSTEM_USER,
    }
    if user.system_role not in allowed_roles:
        raise InsufficientPrivilegesException(
            required_privilege="system user or higher",
            user_id=user.id,
        )


async def verify_organization_membership(
    org_id: UUID, user_id: UUID, db: AsyncSession
) -> None:
    """Verify that a user is a member of an organization.

    Args:
        org_id: Organization ID to check membership for
        user_id: User ID to verify
        db: Database session

    Raises:
        UnauthorizedOrganizationAccessException: If user is not a member of the organization
    """
    stmt = select(KOrganizationPrincipal).where(
        KOrganizationPrincipal.org_id == org_id,  # type: ignore[arg-type]
        KOrganizationPrincipal.principal_id == user_id,  # type: ignore[arg-type]
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise UnauthorizedOrganizationAccessException(org_id=org_id, user_id=user_id)
