"""Authentication and security utilities for the application."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from ..config import settings

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

    This is a placeholder implementation. In a real application,
    you would query the database to find the user and verify the password.

    Parameters
    ----------
    username: str
        Username or email address
    password: str
        Plain text password

    Returns
    -------
    dict[str, Any] | None
        User data if authentication successful, None otherwise.
    """
    # TODO: Replace with actual database lookup
    # For now, using a mock user for testing
    fake_user = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": get_password_hash("secret123"),
        "full_name": "Test User",
        "is_active": True,
    }

    # Check if username matches (could be username or email)
    if username in ["testuser", "test@example.com"]:
        if await verify_password(password, fake_user["hashed_password"]):
            return fake_user

    return None


__all__ = [
    "oauth2_scheme",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "authenticate_user",
]
