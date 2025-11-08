"""Authentication and security utilities for the application."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid7

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select

from app.schemas.user import UserDetail

from ..config import settings
from ..models import KPrincipal, KPrincipalIdentity

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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
    data: dict[str, Any],
    now: datetime,
    ss: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Convert datetime objects to Unix timestamps
    # Since our datetimes are naive but represent UTC, we need to add UTC timezone info
    session_start = ss if ss else now
    now_utc = now.replace(tzinfo=UTC)
    expire_utc = expire.replace(tzinfo=UTC)
    session_start_utc = session_start.replace(tzinfo=UTC)

    to_encode.update({"iss": "https://auth.baseklass.io"})
    to_encode.update({"aud": "https://dev.skrm.io"}),
    to_encode.update({"jti": str(uuid7())})
    to_encode.update({"iat": int(now_utc.timestamp())})
    to_encode.update({"exp": int(expire_utc.timestamp())})
    to_encode.update({"ss": int(session_start_utc.timestamp())})
    print(f"create_access_token to_encode: {to_encode}")
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def create_refresh_token(
    data: dict[str, Any],
    now: datetime,
    ss: datetime | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Convert datetime objects to Unix timestamps
    # Since our datetimes are naive but represent UTC, we need to add UTC timezone info
    session_start = ss if ss else now
    now_utc = now.replace(tzinfo=UTC)
    expire_utc = expire.replace(tzinfo=UTC)
    session_start_utc = session_start.replace(tzinfo=UTC)

    to_encode.update({"iss": "https://auth.baseklass.io"})
    to_encode.update({"aud": "https://dev.skrm.io"}),
    to_encode.update({"jti": str(uuid7())})
    to_encode.update({"iat": int(now_utc.timestamp())})
    to_encode.update({"exp": int(expire_utc.timestamp())})
    to_encode.update({"ss": int(session_start_utc.timestamp())})
    print(f"create_refresh_token: to_encode: {to_encode}")
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
        # Decode without audience verification since we're not validating against a specific audience
        # but keep expiration verification enabled
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False, "verify_exp": True},
        )

        # Verify all required JWT claims are present
        required_claims = ["sub", "scope", "iss", "aud", "jti", "iat", "exp", "ss"]
        for claim in required_claims:
            if claim not in payload:
                return None

        return payload

    except JWTError:
        return None


async def authenticate_user(
    username: str,
    password: str,
    db: Any,  # AsyncSession - using Any to avoid circular import
) -> UserDetail | None:
    """Authenticate a user with username and password.

    Args:
        username: Username to authenticate
        password: Plain text password to verify
        db: Database session

    Returns:
        UserDetail if authentication successful, None otherwise
    """
    stmt = select(KPrincipal).where(
        KPrincipal.scope == "global",  # type: ignore[arg-type]
        KPrincipal.human == True,  # type: ignore[arg-type]  # noqa: E712
        KPrincipal.enabled == True,  # type: ignore[arg-type]  # noqa: E712
        KPrincipal.username == username,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    principal = result.scalar_one_or_none()

    if not principal:
        return None

    # Query for the user's password hash
    identity_stmt = select(KPrincipalIdentity).where(
        KPrincipalIdentity.principal_id == principal.id,
        KPrincipalIdentity.password != None,  # type: ignore[arg-type]  # noqa: E711
    )
    identity_result = await db.execute(identity_stmt)
    principal_identity = identity_result.scalar_one_or_none()

    if not principal_identity or not principal_identity.password:
        return None

    # Verify the password
    if await verify_password(password, principal_identity.password):
        return UserDetail.model_validate(principal)

    return None


__all__ = [
    "oauth2_scheme",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "authenticate_user",
]
