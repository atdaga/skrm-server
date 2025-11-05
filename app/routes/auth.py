"""Authentication endpoints for user login and token management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db.database import get_db
from ..core.exceptions.domain_exceptions import (
    InvalidCredentialsException,
    InvalidTokenException,
)
from ..logic import auth as auth_logic
from ..schemas.fido2 import (
    Fido2AuthenticationBeginRequest,
    Fido2AuthenticationBeginResponse,
    Fido2AuthenticationCompleteRequest,
    Fido2CredentialDeleteResponse,
    Fido2CredentialDetail,
    Fido2CredentialList,
    Fido2CredentialUpdateRequest,
    Fido2RegistrationBeginResponse,
    Fido2RegistrationCompleteRequest,
    Fido2RegistrationCompleteResponse,
)
from ..schemas.user import Token, UserDetail
from .deps import get_current_user

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


# FIDO2 Registration Endpoints


@router.post("/fido2/register/begin", response_model=Fido2RegistrationBeginResponse)
async def fido2_register_begin(
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Fido2RegistrationBeginResponse:
    """Begin FIDO2 credential registration for authenticated user.

    Returns:
        PublicKeyCredentialCreationOptions for the browser/client

    Raises:
        HTTPException: If registration cannot be started
    """
    try:
        response, session_id = await auth_logic.begin_fido2_registration(
            current_user.id, db
        )
        # Store session_id in response for client to send back
        # In production, consider using signed cookies or session storage
        response.publicKey["sessionId"] = session_id
        return response
    except (InvalidCredentialsException, InvalidTokenException) as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e


@router.post(
    "/fido2/register/complete", response_model=Fido2RegistrationCompleteResponse
)
async def fido2_register_complete(
    request: Fido2RegistrationCompleteRequest,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Fido2RegistrationCompleteResponse:
    """Complete FIDO2 credential registration.

    Args:
        request: Registration completion request with attestation and session_id
        current_user: Currently authenticated user
        db: Database session

    Returns:
        Registration completion response with credential ID

    Raises:
        HTTPException: If registration verification fails
    """
    try:
        credential_id = await auth_logic.complete_fido2_registration(
            current_user.id,
            request.session_id,
            request.credential,
            request.nickname,
            db,
        )
        return Fido2RegistrationCompleteResponse(credential_id=credential_id)
    except (InvalidCredentialsException, InvalidTokenException) as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e


# FIDO2 Authentication Endpoints


@router.post(
    "/fido2/authenticate/begin", response_model=Fido2AuthenticationBeginResponse
)
async def fido2_authenticate_begin(
    request: Fido2AuthenticationBeginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Fido2AuthenticationBeginResponse:
    """Begin FIDO2 authentication.

    Args:
        request: Authentication begin request (username optional for passwordless)
        db: Database session

    Returns:
        PublicKeyCredentialRequestOptions for the browser/client
    """
    try:
        response, session_id = await auth_logic.begin_fido2_authentication(
            request.username,
            request.require_user_verification,
            db,
        )
        # Store session_id in response for client to send back
        response.publicKey["sessionId"] = session_id
        return response
    except (InvalidCredentialsException, InvalidTokenException) as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e


@router.post("/fido2/authenticate/complete", response_model=Token)
async def fido2_authenticate_complete(
    request: Fido2AuthenticationCompleteRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Complete FIDO2 passwordless authentication.

    Args:
        request: Authentication completion request with assertion and session_id
        db: Database session

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If authentication verification fails
    """
    try:
        return await auth_logic.perform_passwordless_login(
            request.session_id,
            request.credential,
            db,
        )
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/login/2fa", response_model=Token)
async def login_2fa(
    username: Annotated[str, Body()],
    password: Annotated[str, Body()],
    session_id: Annotated[str, Body()],
    credential: Annotated[dict, Body()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Perform two-factor authentication with password + FIDO2.

    This endpoint combines password and FIDO2 authentication in a single request.
    The client must first obtain a FIDO2 challenge via /fido2/authenticate/begin,
    then provide both password and FIDO2 assertion here.

    Args:
        username: Username
        password: Password
        session_id: FIDO2 session ID from authenticate/begin
        credential: FIDO2 assertion from authenticator
        db: Database session

    Returns:
        JWT access and refresh tokens

    Raises:
        HTTPException: If either password or FIDO2 verification fails
    """
    try:
        return await auth_logic.perform_2fa_login(
            username,
            password,
            session_id,
            credential,
            db,
        )
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# FIDO2 Credential Management Endpoints


@router.get("/fido2/credentials", response_model=Fido2CredentialList)
async def list_credentials(
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Fido2CredentialList:
    """List all FIDO2 credentials for the authenticated user.

    Returns:
        List of user's FIDO2 credentials
    """
    try:
        credentials = await auth_logic.list_user_credentials(current_user.id, db)
        return Fido2CredentialList(credentials=credentials, total=len(credentials))
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list credentials: {str(e)}",
        ) from e


@router.patch(
    "/fido2/credentials/{credential_id}", response_model=Fido2CredentialDetail
)
async def update_credential(
    credential_id: UUID,
    request: Fido2CredentialUpdateRequest,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Fido2CredentialDetail:
    """Update a FIDO2 credential's nickname.

    Args:
        credential_id: ID of the credential to update
        request: Update request with new nickname
        current_user: Currently authenticated user
        db: Database session

    Returns:
        Updated credential details

    Raises:
        HTTPException: If credential not found or doesn't belong to user
    """
    try:
        await auth_logic.update_credential_nickname(
            current_user.id,
            credential_id,
            request.nickname,
            db,
        )
        # Fetch updated credential
        credentials = await auth_logic.list_user_credentials(current_user.id, db)
        updated = next((c for c in credentials if c.id == credential_id), None)
        if not updated:  # pragma: no cover
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found after update",
            )
        return updated
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete(
    "/fido2/credentials/{credential_id}",
    response_model=Fido2CredentialDeleteResponse,
)
async def delete_credential(
    credential_id: UUID,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Fido2CredentialDeleteResponse:
    """Delete a FIDO2 credential.

    Args:
        credential_id: ID of the credential to delete
        current_user: Currently authenticated user
        db: Database session

    Returns:
        Deletion confirmation message

    Raises:
        HTTPException: If credential not found or doesn't belong to user
    """
    try:
        await auth_logic.delete_credential(current_user.id, credential_id, db)
        return Fido2CredentialDeleteResponse()
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
