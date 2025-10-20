from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import oauth2_scheme, verify_token
from ..core.db.database import get_db
from ..core.exceptions.http_exceptions import UnauthorizedException
from ..models import KPrincipal
from ..schemas.user import TokenData, UserDetail


async def get_current_token(
    token: Annotated[str, Depends(oauth2_scheme)],
    # db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenData:
    """Get current token from Authorization header."""
    payload = await verify_token(token)
    if payload is None:
        raise UnauthorizedException("User not authenticated.")

    # TODO: Check blacklist of tokens or principal IDs.

    return TokenData(sub=payload["sub"], scope=payload["scope"], iss=payload["iss"])


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Get current authenticated user from token."""
    payload = await verify_token(token)
    if payload is None:
        raise UnauthorizedException("User not authenticated.")

    id = payload.get("sub")
    try:
        uuid = UUID(id)
    except ValueError as e:
        raise UnauthorizedException("Invalid user ID.") from e

    if not id:
        raise UnauthorizedException("User not authenticated.")

    # Query the database for the user by username
    stmt = select(KPrincipal).where(KPrincipal.id == uuid)  # type: ignore
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found.")

    return UserDetail.model_validate(user)


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

        payload = await verify_token(token_value)
        if payload is None:
            return None

        return await get_current_user(token_value, db=db)

    except HTTPException as http_exc:
        if http_exc.status_code != 401:
            # Log unexpected errors but don't raise
            pass
        return None

    except Exception:
        # Log unexpected errors but don't raise
        return None


async def get_current_superuser(
    current_user: Annotated[UserDetail, Depends(get_current_user)]
) -> UserDetail:
    """Get current superuser."""
    # Check if user has superuser privileges in meta
    is_superuser = current_user.meta.get("is_superuser", False)
    if not is_superuser:
        raise HTTPException(
            status_code=403, detail="You do not have enough privileges."
        )

    return current_user
