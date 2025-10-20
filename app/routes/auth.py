"""Authentication endpoints for user login and token management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.auth import authenticate_user, create_access_token
from ..schemas.user import Token

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    """Authenticate user and return access token.

    The scope field accepts a space-separated list of scopes (e.g., "read write").
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Use the requested scopes from the form, or default to "global"
    scope = " ".join(form_data.scopes) if form_data.scopes else "global"
    access_token = await create_access_token(
        data={"sub": str(user.id), "scope": scope, "iss": "https://auth.baseklass.io"}
    )
    return Token(access_token=access_token, token_type="bearer")
