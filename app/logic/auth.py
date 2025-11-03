"""Business logic for authentication operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from ..core.exceptions.domain_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
)
from ..schemas.user import Token


async def perform_login(
    username: str,
    password: str,
    db: AsyncSession,
    scopes: list[str] | None = None,
) -> Token:
    """Perform user login and generate access token.

    Args:
        username: Username for authentication
        password: Password for authentication
        db: Database session
        scopes: List of requested scopes (defaults to ["global"])

    Returns:
        Token object containing the access token

    Raises:
        InvalidCredentialsException: If username or password is incorrect
    """
    user = await authenticate_user(username, password, db)
    if not user:
        raise InvalidCredentialsException(username=username)

    # Use the requested scopes from the form, or default to "global"
    scope = " ".join(scopes) if scopes else "global"

    token_data = {
        "sub": str(user.id),
        "scope": scope,
        "iss": "https://auth.baseklass.io",
    }

    access_token = await create_access_token(data=token_data)
    refresh_token = await create_refresh_token(data=token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )


async def refresh_access_token(refresh_token: str) -> Token:
    """Generate new access and refresh tokens from a valid refresh token.

    Args:
        refresh_token: The refresh token to validate

    Returns:
        Token object containing new access and refresh tokens

    Raises:
        InvalidTokenException: If the refresh token is invalid or expired
    """
    payload = await verify_token(refresh_token)
    if not payload:
        raise InvalidTokenException(reason="Invalid or expired refresh token")

    # Extract user data from the refresh token
    user_id = payload.get("sub")
    scope = payload.get("scope", "global")
    issuer = payload.get("iss", "https://auth.baseklass.io")

    if not user_id:
        raise InvalidTokenException(reason="Missing subject in refresh token payload")

    # Create new tokens
    token_data = {"sub": user_id, "scope": scope, "iss": issuer}
    new_access_token = await create_access_token(data=token_data)
    new_refresh_token = await create_refresh_token(data=token_data)

    return Token(
        access_token=new_access_token,
        token_type="bearer",
        refresh_token=new_refresh_token,
    )
