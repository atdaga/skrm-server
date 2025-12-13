"""Authentication endpoints for user login and token management."""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
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


def _is_mobile_client(request: Request) -> bool:
    """Detect if client is a mobile app based on User-Agent or X-Client-Type header.

    Args:
        request: FastAPI request object

    Returns:
        True if mobile client, False if web client
    """
    # Check for explicit client type header (preferred method)
    client_type = request.headers.get("X-Client-Type", "").lower()
    if client_type in ("mobile", "ios", "android"):
        return True

    # Fallback: Check User-Agent for mobile app patterns
    user_agent = request.headers.get("User-Agent", "").lower()
    mobile_patterns = ["okhttp", "alamofire", "cfnetwork", "mobile"]
    return any(pattern in user_agent for pattern in mobile_patterns)


def _set_refresh_token_cookie(
    response: Response, refresh_token: str, expires_in_days: int
) -> None:
    """Set refresh token as HTTP-only cookie.

    Args:
        response: FastAPI response object
        refresh_token: Refresh token value
        expires_in_days: Cookie expiration in days
    """
    max_age = expires_in_days * 24 * 60 * 60  # Convert days to seconds
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,  # False in debug mode (HTTP), True in production (HTTPS)
        samesite="strict",  # CSRF protection
        max_age=max_age,
        path="/api/auth",  # Only sent to auth endpoints
    )


def _create_token_response(
    token: Token, request: Request, response: Response, is_mobile: bool
) -> Token:
    """Create token response with appropriate refresh token handling.

    For web clients: Sets refresh token as HTTP-only cookie, excludes from body.
    For mobile clients: Returns refresh token in response body.

    Args:
        token: Token object with access and refresh tokens
        request: FastAPI request object
        response: FastAPI response object
        is_mobile: Whether client is a mobile app

    Returns:
        Token object (with refresh_token excluded for web clients)
    """
    if is_mobile:
        # Mobile: return refresh token in body
        return token
    else:
        # Web: set cookie, exclude from body
        _set_refresh_token_cookie(
            response, token.refresh_token, settings.refresh_token_expire_days
        )
        return Token(
            access_token=token.access_token,
            token_type=token.token_type,
            refresh_token="",  # Don't expose in body for web clients
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate user and return access token.

    The scope field accepts a space-separated list of scopes (e.g., "read write").

    For web clients: Refresh token is set as HTTP-only cookie.
    For mobile clients: Refresh token is returned in response body.
    Client type is detected via X-Client-Type header or User-Agent.
    """
    try:
        token = await auth_logic.perform_login(
            username=form_data.username,
            password=form_data.password,
            db=db,
            scopes=form_data.scopes,
        )
        is_mobile = _is_mobile_client(request)
        return _create_token_response(token, request, response, is_mobile)
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Body(embed=True)] = None,
) -> Token:
    """Exchange a refresh token for new access and refresh tokens.

    Supports both web (cookie-based) and mobile (body-based) clients:
    - Web clients: Refresh token sent via HTTP-only cookie
    - Mobile clients: Refresh token sent in request body as {"refresh_token": "..."}

    Args:
        request: FastAPI request object (for cookie access)
        response: FastAPI response object (for setting cookies)
        refresh_token: Optional refresh token from request body (for mobile clients)

    Returns:
        New access and refresh tokens (refresh token in cookie for web, body for mobile)

    Raises:
        HTTPException: If the refresh token is invalid or expired
    """
    is_mobile = _is_mobile_client(request)

    # Get refresh token from appropriate source
    if is_mobile:
        # Mobile: get from request body
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token required in request body for mobile clients",
            )
        token_value: str = refresh_token
    else:
        # Web: get from cookie
        cookie_token = request.cookies.get("refresh_token")
        if not cookie_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token missing from cookie",
            )
        token_value = cookie_token

    try:
        token = await auth_logic.refresh_access_token(token_value)
        return _create_token_response(token, request, response, is_mobile)
    except InvalidTokenException as e:
        # Clear invalid cookie if present
        if not is_mobile:
            response.delete_cookie(key="refresh_token", path="/api/auth")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/logout")
async def logout(
    _current_user: Annotated[UserDetail, Depends(get_current_user)],
    request: Request,
    response: Response,
) -> dict[str, str]:
    """Logout user by clearing refresh token cookie.

    For web clients: Clears HTTP-only refresh token cookie.
    For mobile clients: No-op (client should discard refresh token).

    Args:
        request: FastAPI request object (for client detection)
        response: FastAPI response object (for clearing cookies)

    Returns:
        Logout confirmation message
    """
    is_mobile = _is_mobile_client(request)

    if not is_mobile:
        # Clear refresh token cookie for web clients
        response.delete_cookie(
            key="refresh_token",
            path="/api/auth",
            samesite="strict",
        )

    return {"message": "Logged out successfully"}


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
    except (
        InvalidCredentialsException,
        InvalidTokenException,
    ) as e:  # pragma: no cover
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
    except (
        InvalidCredentialsException,
        InvalidTokenException,
    ) as e:  # pragma: no cover
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
    except (
        InvalidCredentialsException,
        InvalidTokenException,
    ) as e:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e


@router.post("/fido2/authenticate/complete", response_model=Token)
async def fido2_authenticate_complete(
    request_body: Fido2AuthenticationCompleteRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Complete FIDO2 passwordless authentication.

    Args:
        request_body: Authentication completion request with assertion and session_id
        request: FastAPI request object (for client detection)
        response: FastAPI response object (for setting cookies)
        db: Database session

    Returns:
        JWT access and refresh tokens (refresh token in cookie for web, body for mobile)

    Raises:
        HTTPException: If authentication verification fails
    """
    try:
        token = await auth_logic.perform_passwordless_login(
            request_body.session_id,
            request_body.credential,
            db,
        )
        is_mobile = _is_mobile_client(request)
        return _create_token_response(token, request, response, is_mobile)
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
    request: Request,
    response: Response,
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
        request: FastAPI request object (for client detection)
        response: FastAPI response object (for setting cookies)
        db: Database session

    Returns:
        JWT access and refresh tokens (refresh token in cookie for web, body for mobile)

    Raises:
        HTTPException: If either password or FIDO2 verification fails
    """
    try:
        token = await auth_logic.perform_2fa_login(
            username,
            password,
            session_id,
            credential,
            db,
        )
        is_mobile = _is_mobile_client(request)
        return _create_token_response(token, request, response, is_mobile)
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
    hard_delete: Annotated[
        bool, Query(description="Hard delete the credential")
    ] = False,
) -> Fido2CredentialDeleteResponse:
    """Delete a FIDO2 credential.

    Args:
        credential_id: ID of the credential to delete
        hard_delete: If True, permanently delete the credential. If False, soft delete.
        current_user: Currently authenticated user
        db: Database session

    Returns:
        Deletion confirmation message

    Raises:
        HTTPException: If credential not found or doesn't belong to user
    """
    # Check authorization for hard delete
    if hard_delete:
        from ..core.exceptions.domain_exceptions import InsufficientPrivilegesException
        from ..logic import deps as deps_logic

        try:
            deps_logic.check_hard_delete_privileges(current_user)
        except InsufficientPrivilegesException as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await auth_logic.delete_credential(
            current_user.id, credential_id, db, hard_delete=hard_delete
        )
        return Fido2CredentialDeleteResponse()
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
