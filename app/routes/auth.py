"""Authentication endpoints for user login and token management."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db.database import get_db
from ..core.exceptions.domain_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
)
from ..logic import auth as auth_logic
from ..schemas.user import Token

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate user and return access token.

    The scope field accepts a space-separated list of scopes (e.g., "read write").
    """
    try:
        return await auth_logic.perform_login(
            username=form_data.username,
            password=form_data.password,
            db=db,
            scopes=form_data.scopes,
        )
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: Annotated[str, Body(embed=True)],
) -> Token:
    """Exchange a refresh token for new access and refresh tokens.

    Args:
        refresh_token: The refresh token to exchange

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If the refresh token is invalid or expired
    """
    try:
        return await auth_logic.refresh_access_token(refresh_token)
    except InvalidTokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
