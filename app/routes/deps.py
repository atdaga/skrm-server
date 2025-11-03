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
    token: Annotated[str, Depends(oauth2_scheme)],
) -> TokenData:
    """Get current token from Authorization header."""
    try:
        return await deps_logic.get_token_data(token)
    except InvalidTokenException as e:
        raise UnauthorizedException(e.message) from e


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Get current authenticated user from token."""
    try:
        return await deps_logic.get_user_from_token(token, db)
    except (InvalidTokenException, InvalidUserIdException, UserNotFoundException) as e:
        raise UnauthorizedException(e.message) from e


async def get_optional_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> UserDetail | None:
    """Get optional user from Authorization header."""
    token = request.headers.get("Authorization")
    if not token:
        return None

    try:
        token_type, _, token_value = token.partition(" ")
        if token_type.lower() != "bearer" or not token_value:
            return None

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
