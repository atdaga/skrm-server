from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import (
    oauth2_scheme,
    verify_token,
)
from ..core.db.database import get_db
from ..core.exceptions.http_exceptions import UnauthorizedException


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any] | None:
    """Get current authenticated user from token."""
    payload = await verify_token(token)
    if payload is None:
        raise UnauthorizedException("User not authenticated.")

    username_or_email = payload.get("sub")
    if not username_or_email:
        raise UnauthorizedException("User not authenticated.")

    # TODO: Implement actual user retrieval from database
    # For now, return mock data based on token
    return {
        "id": 1,
        "email": username_or_email if "@" in username_or_email else "user@example.com",
        "username": username_or_email if "@" not in username_or_email else "testuser",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> dict | None:
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


async def get_current_superuser(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Get current superuser."""
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=403,
            detail="You do not have enough privileges."
        )

    return current_user

