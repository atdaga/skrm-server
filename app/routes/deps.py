from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import oauth2_scheme
from ..core.db.database import get_db
from ..core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    InvalidTokenException,
    InvalidUserIdException,
    UserNotFoundException,
)
from ..core.exceptions.http_exceptions import UnauthorizedException
from ..logic import deps as deps_logic
from ..schemas.user import TokenData, UserDetail


async def get_current_token(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> TokenData:
    """Get current token from Authorization header.

    Checks request.state for cached validated token to avoid duplicate validation.
    Falls back to full validation if cache miss or token mismatch.
    """
    try:
        # Check if middleware already validated this token
        cached_token = getattr(request.state, "jwt_token", None)
        cached_payload = getattr(request.state, "jwt_payload", None)

        if cached_token == token and cached_payload is not None:
            # Use cached payload to avoid duplicate validation
            # Convert Unix timestamps to datetime objects (same as get_token_data)
            from datetime import UTC, datetime

            iat = datetime.fromtimestamp(cached_payload["iat"], tz=UTC).replace(
                tzinfo=None
            )
            exp = datetime.fromtimestamp(cached_payload["exp"], tz=UTC).replace(
                tzinfo=None
            )
            ss = datetime.fromtimestamp(cached_payload["ss"], tz=UTC).replace(
                tzinfo=None
            )

            return TokenData(
                sub=cached_payload["sub"],
                scope=cached_payload["scope"],
                iss=cached_payload["iss"],
                aud=cached_payload["aud"],
                jti=cached_payload["jti"],
                iat=iat,
                exp=exp,
                ss=ss,
            )

        # Cache miss or token mismatch - perform full validation
        return await deps_logic.get_token_data(token)
    except InvalidTokenException as e:
        raise UnauthorizedException(e.message) from e


async def get_current_user(
    request: Request,
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Get current authenticated user from token.

    Checks request.state for cached validated token to avoid duplicate validation.
    Falls back to full validation if cache miss or token mismatch.
    """
    try:
        # Check if middleware already validated this token
        cached_token = getattr(request.state, "jwt_token", None)
        cached_payload = getattr(request.state, "jwt_payload", None)

        if cached_token == token and cached_payload is not None:
            # Use cached payload to extract user ID and fetch from database
            from uuid import UUID

            user_id_str = cached_payload.get("sub")
            try:
                user_id = UUID(user_id_str)
            except (ValueError, TypeError) as e:
                raise InvalidUserIdException(user_id_str=str(user_id_str)) from e

            return await deps_logic.get_user_by_id(user_id, db)

        # Cache miss or token mismatch - perform full validation
        return await deps_logic.get_user_from_token(token, db)
    except (InvalidTokenException, InvalidUserIdException, UserNotFoundException) as e:
        raise UnauthorizedException(e.message) from e


async def get_optional_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> UserDetail | None:
    """Get optional user from Authorization header.

    Checks request.state for cached validated token to avoid duplicate validation.
    """
    token = request.headers.get("Authorization")
    if not token:
        return None

    try:
        token_type, _, token_value = token.partition(" ")
        if token_type.lower() != "bearer" or not token_value:
            return None

        # Check if middleware already validated this token
        cached_token = getattr(request.state, "jwt_token", None)
        cached_payload = getattr(request.state, "jwt_payload", None)

        if cached_token == token_value and cached_payload is not None:
            # Use cached payload to extract user ID and fetch from database
            from uuid import UUID

            user_id_str = cached_payload.get("sub")
            user_id = UUID(user_id_str)
            return await deps_logic.get_user_by_id(user_id, db)

        # Cache miss or token mismatch - perform full validation
        return await deps_logic.get_user_from_token(token_value, db)

    except Exception:
        # Log unexpected errors but don't raise
        return None


async def get_current_superuser(
    current_user: Annotated[UserDetail, Depends(get_current_user)]
) -> UserDetail:
    """Get current superuser."""
    try:
        deps_logic.check_superuser_privileges(current_user)
        return current_user
    except InsufficientPrivilegesException as e:
        raise HTTPException(status_code=403, detail=e.message) from e


async def get_system_user(
    current_user: Annotated[UserDetail, Depends(get_current_user)]
) -> UserDetail:
    """Get current user with system user role or higher.

    This dependency ensures the user has one of the following roles:
    - SYSTEM
    - SYSTEM_ROOT
    - SYSTEM_ADMIN
    - SYSTEM_USER

    Returns:
        The current user if they have the required role

    Raises:
        HTTPException: 403 if user does not have system user role or higher
    """
    try:
        deps_logic.check_system_user_role(current_user)
        return current_user
    except InsufficientPrivilegesException as e:
        raise HTTPException(status_code=403, detail=e.message) from e


async def get_system_root_user(
    current_user: Annotated[UserDetail, Depends(get_current_user)]
) -> UserDetail:
    """Get current user with system root role.

    This dependency ensures the user has the systemRoot role.

    Returns:
        The current user if they have the required role

    Raises:
        HTTPException: 403 if user does not have system root role
    """
    try:
        deps_logic.check_system_root_role(current_user)
        return current_user
    except InsufficientPrivilegesException as e:
        raise HTTPException(status_code=403, detail=e.message) from e


async def check_hard_delete_authorization(
    current_user: Annotated[UserDetail, Depends(get_current_user)]
) -> UserDetail:
    """Check if current user has privileges to perform hard deletes.

    This dependency ensures the user has system or systemRoot role.

    Returns:
        The current user if they have the required role

    Raises:
        HTTPException: 403 if user does not have hard delete privileges
    """
    try:
        deps_logic.check_hard_delete_privileges(current_user)
        return current_user
    except InsufficientPrivilegesException as e:
        raise HTTPException(status_code=403, detail=e.message) from e
