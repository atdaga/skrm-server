"""Business logic for authentication operations."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
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
    }

    now = datetime.now(UTC).replace(tzinfo=None)
    access_token = await create_access_token(data=token_data, now=now)
    refresh_token = await create_refresh_token(data=token_data, now=now)

    print(f"Access token: {access_token}")
    print(f"Refresh token: {refresh_token}")

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
        InvalidTokenException: If the refresh token is invalid or expired, or if the absolute expiration has been exceeded
    """
    payload = await verify_token(refresh_token)
    if not payload:
        raise InvalidTokenException(reason="Invalid or expired refresh token")

    # Extract user data from the refresh token
    user_id = payload.get("sub")
    scope = payload.get("scope", "global")
    issuer = payload.get("iss", "https://auth.baseklass.io")
    session_start_timestamp = payload.get("ss")

    if not user_id:
        raise InvalidTokenException(reason="Missing subject in refresh token payload")

    if not session_start_timestamp:
        raise InvalidTokenException(
            reason="Missing session start claim in refresh token payload"
        )

    # Check absolute expiration
    now = datetime.now(UTC).replace(tzinfo=None)
    session_start = datetime.fromtimestamp(session_start_timestamp, tz=UTC).replace(
        tzinfo=None
    )

    # Calculate absolute expiration time (approximating months as 30 days)
    absolute_expiration = session_start + timedelta(
        days=settings.refresh_token_absolute_expire_months * 30
    )

    if now >= absolute_expiration:
        raise InvalidTokenException(
            reason="Session has exceeded absolute expiration time"
        )

    # Create new tokens with the original session start time
    token_data = {"sub": user_id, "scope": scope, "iss": issuer}
    new_access_token = await create_access_token(
        data=token_data, now=now, ss=session_start
    )
    new_refresh_token = await create_refresh_token(
        data=token_data, now=now, ss=session_start
    )

    return Token(
        access_token=new_access_token,
        token_type="bearer",
        refresh_token=new_refresh_token,
    )
