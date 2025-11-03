"""Business logic for authentication operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.auth import authenticate_user, create_access_token
from ..core.exceptions.domain_exceptions import InvalidCredentialsException
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

    access_token = await create_access_token(
        data={"sub": str(user.id), "scope": scope, "iss": "https://auth.baseklass.io"}
    )

    return Token(access_token=access_token, token_type="bearer")
