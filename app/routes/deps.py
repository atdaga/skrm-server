from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..schemas.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # TODO: Implement actual token validation and user retrieval
    # For now, return a mock user
    from datetime import datetime

    return User(
        id=1,
        email="user@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
