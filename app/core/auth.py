"""Authentication and security utilities for the application."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select

from ..config import settings
from ..models import KPrincipalIdentity, KUser
from .db.database import get_db_session

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    correct_password: bool = bcrypt.checkpw(
        plain_password.encode(), hashed_password.encode()
    )
    return correct_password


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    hashed_password: str = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashed_password


async def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def create_refresh_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(token: str) -> dict[str, Any] | None:
    """Verify a JWT token and return payload if valid.

    Parameters
    ----------
    token: str
        The JWT token to be verified.

    Returns
    -------
    dict[str, Any] | None
        Token payload if the token is valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username_or_email: str = payload.get("sub")
        if username_or_email is None:
            return None
        return payload

    except JWTError:
        return None


async def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate a user with username/email and password.

    Parameters
    ----------
    username: str
        Username (alias field in KUser model)
    password: str
        Plain text password

    Returns
    -------
    dict[str, Any] | None
        User data if authentication successful, None otherwise.
    """
    async with get_db_session() as session:
        # Query for user by alias (username)
        stmt = select(KUser).where(KUser.alias == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Query for the user's password hash
        identity_stmt = select(KPrincipalIdentity).where(KPrincipalIdentity.user_id == user.id)
        identity_result = await session.execute(identity_stmt)
        principal_identity = identity_result.scalar_one_or_none()

        if not principal_identity or not principal_identity.password:
            return None

        # Verify the password
        if await verify_password(password, principal_identity.password):
            return {
                "id": str(user.id),
                "username": user.alias,
                "meta": user.meta,
                "created": user.created,
                "last_modified": user.last_modified,
                "is_active": True,  # You can add logic here based on your requirements
            }

    return None


__all__ = [
    "oauth2_scheme",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "authenticate_user",
]
