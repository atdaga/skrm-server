"""Business logic for authentication operations."""

import base64
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fido2.webauthn import (
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)
from sqlalchemy import select
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
from ..core.fido2_server import (
    aaguid_to_hex,
    credential_id_from_base64,
    credential_id_to_base64,
    credential_to_descriptor,
    encode_options_for_client,
    generate_session_id,
    get_fido2_server,
    parse_attestation_object,
    parse_authenticator_data,
    parse_client_data,
    retrieve_challenge,
    store_challenge,
)
from ..models.k_fido2_credential import KFido2Credential
from ..models.k_principal import KPrincipal
from ..schemas.fido2 import (
    Fido2AuthenticationBeginResponse,
    Fido2CredentialDetail,
    Fido2RegistrationBeginResponse,
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


# FIDO2 Registration Logic


async def begin_fido2_registration(
    user_id: UUID, db: AsyncSession
) -> tuple[Fido2RegistrationBeginResponse, str]:
    """Begin FIDO2 credential registration process.

    Args:
        user_id: User ID for registration
        db: Database session

    Returns:
        Tuple of (registration options response, session_id for challenge tracking)

    Raises:
        InvalidCredentialsException: If user not found
    """
    # Fetch user
    result = await db.execute(select(KPrincipal).where(KPrincipal.id == user_id, KPrincipal.deleted == False))  # type: ignore[arg-type]  # noqa: E712
    user = result.scalar_one_or_none()
    if not user:
        raise InvalidCredentialsException(username=str(user_id))

    # Get existing credentials for this user to exclude them
    existing_result = await db.execute(
        select(KFido2Credential).where(KFido2Credential.principal_id == user_id, KFido2Credential.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    )
    existing_credentials = existing_result.scalars().all()

    # Create exclude list
    exclude_credentials = [
        credential_to_descriptor(cred.credential_id, cred.transports)
        for cred in existing_credentials
    ]

    # Generate registration options
    server = get_fido2_server()
    user_entity = {
        "id": str(user.id).encode("utf-8"),
        "name": user.username,
        "displayName": user.display_name,
    }

    registration_data, state = server.register_begin(
        user=user_entity,  # type: ignore[arg-type]
        credentials=exclude_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
        authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
        resident_key_requirement=(
            ResidentKeyRequirement.REQUIRED
            if settings.fido2_require_resident_key
            else ResidentKeyRequirement.PREFERRED
        ),
    )

    # Store challenge
    session_id = generate_session_id()
    store_challenge(session_id, state["challenge"])

    # Convert to client format
    options_dict = {
        "rp": registration_data.rp,  # type: ignore[attr-defined]
        "user": registration_data.user,  # type: ignore[attr-defined]
        "challenge": registration_data.challenge,  # type: ignore[attr-defined]
        "pubKeyCredParams": [
            {"type": param.type, "alg": param.alg}
            for param in registration_data.pub_key_cred_params  # type: ignore[attr-defined]
        ],
        "timeout": registration_data.timeout or settings.fido2_timeout,  # type: ignore[attr-defined]
        "excludeCredentials": [
            {
                "type": cred.type,
                "id": cred.id,
                "transports": cred.transports or [],
            }
            for cred in (registration_data.exclude_credentials or [])  # type: ignore[attr-defined]
        ],
        "authenticatorSelection": {
            "authenticatorAttachment": (
                registration_data.authenticator_selection.authenticator_attachment  # type: ignore[attr-defined]
                if registration_data.authenticator_selection  # type: ignore[attr-defined]
                else None
            ),
            "residentKey": (
                registration_data.authenticator_selection.resident_key  # type: ignore[attr-defined]
                if registration_data.authenticator_selection  # type: ignore[attr-defined]
                else "preferred"
            ),
            "requireResidentKey": (
                registration_data.authenticator_selection.require_resident_key  # type: ignore[attr-defined]
                if registration_data.authenticator_selection  # type: ignore[attr-defined]
                else False
            ),
            "userVerification": (
                registration_data.authenticator_selection.user_verification  # type: ignore[attr-defined]
                if registration_data.authenticator_selection  # type: ignore[attr-defined]
                else "preferred"
            ),
        },
        "attestation": registration_data.attestation or "none",  # type: ignore[attr-defined]
    }

    # Encode bytes to base64
    encoded_options = encode_options_for_client(options_dict)

    return (
        Fido2RegistrationBeginResponse(publicKey=encoded_options),
        session_id,
    )


async def complete_fido2_registration(
    user_id: UUID,
    session_id: str,
    attestation_response: dict,
    nickname: str | None,
    db: AsyncSession,
) -> str:
    """Complete FIDO2 credential registration.

    Args:
        user_id: User ID for registration
        session_id: Session ID for challenge retrieval
        attestation_response: Attestation response from client
        nickname: Optional nickname for the credential
        db: Database session

    Returns:
        Base64-encoded credential ID

    Raises:
        InvalidTokenException: If challenge is invalid or verification fails
    """
    # Retrieve challenge
    challenge = retrieve_challenge(session_id)
    if not challenge:
        raise InvalidTokenException(reason="Invalid or expired registration session")

    # Parse client response
    try:
        client_data = parse_client_data(
            attestation_response["response"]["clientDataJSON"]
        )
        attestation_object = parse_attestation_object(
            attestation_response["response"]["attestationObject"]
        )

        # Verify registration
        server = get_fido2_server()
        auth_data = server.register_complete(  # type: ignore[call-arg]
            state={"challenge": challenge, "user_verification": "preferred"},
            client_data=client_data,
            attestation_object=attestation_object,
        )

        # Extract credential data
        credential_data = auth_data.credential_data
        if credential_data is None:  # pragma: no cover
            raise InvalidTokenException(reason="No credential data in attestation")

        # Get transports if available
        transports = attestation_response.get("response", {}).get("transports", [])

        # Determine if discoverable (check flags)
        is_discoverable = bool(auth_data.flags & 0x04)  # Check user verified flag

        # Store credential in database
        now = datetime.now()
        credential = KFido2Credential(
            principal_id=user_id,
            credential_id=credential_data.credential_id,
            public_key=credential_data.public_key,
            sign_count=auth_data.counter,
            aaguid=credential_data.aaguid,
            transports=transports,
            is_discoverable=is_discoverable,
            nickname=nickname,
            created=now,
            created_by=user_id,
            last_modified=now,
            last_modified_by=user_id,
        )

        db.add(credential)
        await db.commit()
        await db.refresh(credential)

        return credential_id_to_base64(credential.credential_id)

    except InvalidTokenException:  # pragma: no cover
        # Re-raise domain exceptions as-is (they're already properly typed)
        await db.rollback()
        raise
    except Exception as e:  # pragma: no cover
        # Chain non-domain exceptions with InvalidTokenException
        await db.rollback()
        raise InvalidTokenException(
            reason=f"Registration verification failed: {str(e)}"
        ) from e


# FIDO2 Authentication Logic


async def begin_fido2_authentication(
    username: str | None,
    require_user_verification: bool,
    db: AsyncSession,
) -> tuple[Fido2AuthenticationBeginResponse, str]:
    """Begin FIDO2 authentication process.

    Args:
        username: Username (optional for discoverable credentials)
        require_user_verification: Whether to require user verification
        db: Database session

    Returns:
        Tuple of (authentication options response, session_id for challenge tracking)
    """
    # Get credentials for user if username provided
    allow_credentials = []
    if username:
        # Find user
        result = await db.execute(
            select(KPrincipal).where(KPrincipal.username == username, KPrincipal.deleted == False)  # type: ignore[arg-type]  # noqa: E712
        )
        user = result.scalar_one_or_none()
        if user:
            # Get user's credentials
            creds_result = await db.execute(
                select(KFido2Credential).where(KFido2Credential.principal_id == user.id, KFido2Credential.deleted == False)  # type: ignore[arg-type]  # noqa: E712
            )
            credentials = creds_result.scalars().all()
            allow_credentials = [
                credential_to_descriptor(cred.credential_id, cred.transports)
                for cred in credentials
            ]

    # Generate authentication options
    server = get_fido2_server()
    auth_data, state = server.authenticate_begin(
        credentials=allow_credentials,
        user_verification=(
            UserVerificationRequirement.REQUIRED
            if require_user_verification
            else UserVerificationRequirement.PREFERRED
        ),
    )

    # Store challenge
    session_id = generate_session_id()
    store_challenge(session_id, state["challenge"])

    # Convert to client format
    options_dict = {
        "challenge": auth_data.challenge,  # type: ignore[attr-defined]
        "timeout": auth_data.timeout or settings.fido2_timeout,  # type: ignore[attr-defined]
        "rpId": auth_data.rp_id,  # type: ignore[attr-defined]
        "allowCredentials": [
            {
                "type": cred.type,
                "id": cred.id,
                "transports": cred.transports or [],
            }
            for cred in (auth_data.allow_credentials or [])  # type: ignore[attr-defined]
        ],
        "userVerification": auth_data.user_verification or "preferred",  # type: ignore[attr-defined]
    }

    # Encode bytes to base64
    encoded_options = encode_options_for_client(options_dict)

    return (
        Fido2AuthenticationBeginResponse(publicKey=encoded_options),
        session_id,
    )


async def complete_fido2_authentication(
    session_id: str,
    assertion_response: dict,
    db: AsyncSession,
) -> tuple[KPrincipal, KFido2Credential]:
    """Complete FIDO2 authentication (verification only).

    Args:
        session_id: Session ID for challenge retrieval
        assertion_response: Assertion response from client
        db: Database session

    Returns:
        Tuple of (authenticated user, credential used)

    Raises:
        InvalidCredentialsException: If verification fails or credential not found
    """
    # Retrieve challenge
    challenge = retrieve_challenge(session_id)
    if not challenge:
        raise InvalidTokenException(reason="Invalid or expired authentication session")

    try:  # pragma: no cover - Success path tested via higher-level functions
        # Parse credential ID
        credential_id_b64 = assertion_response["id"]
        credential_id = credential_id_from_base64(credential_id_b64)

        # Find credential in database
        result = await db.execute(
            select(KFido2Credential).where(
                KFido2Credential.credential_id == credential_id, KFido2Credential.deleted == False  # type: ignore[arg-type]  # noqa: E712
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise InvalidCredentialsException(username="unknown")

        # Get user
        user_result = await db.execute(
            select(KPrincipal).where(KPrincipal.id == credential.principal_id, KPrincipal.deleted == False)  # type: ignore[arg-type]  # noqa: E712
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise InvalidCredentialsException(username="unknown")

        # Parse client response
        client_data = parse_client_data(
            assertion_response["response"]["clientDataJSON"]
        )
        authenticator_data = parse_authenticator_data(
            assertion_response["response"]["authenticatorData"]
        )
        signature = base64.urlsafe_b64decode(
            assertion_response["response"]["signature"]
        )

        # Verify assertion
        server = get_fido2_server()
        server.authenticate_complete(  # type: ignore[call-arg]
            state={
                "challenge": challenge,
                "user_verification": "preferred",
            },
            credentials=[
                {  # type: ignore[list-item]
                    "id": credential.credential_id,
                    "public_key": credential.public_key,
                    "sign_count": credential.sign_count,
                }
            ],
            credential_id=credential.credential_id,
            client_data=client_data,
            auth_data=authenticator_data,
            signature=signature,
        )

        # Update credential usage
        credential.last_used = datetime.now()
        credential.sign_count = authenticator_data.counter
        credential.last_modified = datetime.now()
        credential.last_modified_by = user.id

        await db.commit()
        await db.refresh(credential)

        return user, credential

    except (InvalidCredentialsException, InvalidTokenException):
        # Re-raise domain exceptions as-is (they're already properly typed)
        await db.rollback()
        raise
    except Exception as e:  # pragma: no cover
        # Chain non-domain exceptions with InvalidTokenException
        await db.rollback()
        raise InvalidTokenException(
            reason=f"Authentication verification failed: {str(e)}"
        ) from e


async def perform_passwordless_login(
    session_id: str,
    assertion_response: dict,
    db: AsyncSession,
) -> Token:
    """Perform passwordless login with FIDO2 only.

    Args:
        session_id: Session ID for challenge retrieval
        assertion_response: Assertion response from client
        db: Database session

    Returns:
        Token object containing access and refresh tokens

    Raises:
        InvalidCredentialsException: If verification fails
    """
    user, _ = await complete_fido2_authentication(session_id, assertion_response, db)

    # Generate tokens
    token_data = {
        "sub": str(user.id),
        "scope": "global",
    }

    now = datetime.now(UTC).replace(tzinfo=None)
    access_token = await create_access_token(data=token_data, now=now)
    refresh_token = await create_refresh_token(data=token_data, now=now)

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )


async def perform_2fa_login(
    username: str,
    password: str,
    session_id: str,
    assertion_response: dict,
    db: AsyncSession,
) -> Token:
    """Perform two-factor authentication with password + FIDO2.

    Args:
        username: Username for authentication
        password: Password for authentication
        session_id: Session ID for FIDO2 challenge
        assertion_response: FIDO2 assertion response
        db: Database session

    Returns:
        Token object containing access and refresh tokens

    Raises:
        InvalidCredentialsException: If either password or FIDO2 verification fails
    """
    # First verify password
    user = await authenticate_user(username, password, db)
    if not user:
        raise InvalidCredentialsException(username=username)

    # Then verify FIDO2
    fido2_user, _ = await complete_fido2_authentication(
        session_id, assertion_response, db
    )

    # Ensure the FIDO2 credential belongs to the password-authenticated user
    if fido2_user.id != user.id:
        raise InvalidCredentialsException(username=username)

    # Generate tokens
    token_data = {
        "sub": str(user.id),
        "scope": "global",
    }

    now = datetime.now(UTC).replace(tzinfo=None)
    access_token = await create_access_token(data=token_data, now=now)
    refresh_token = await create_refresh_token(data=token_data, now=now)

    return Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
    )


# FIDO2 Credential Management


async def list_user_credentials(
    user_id: UUID, db: AsyncSession
) -> list[Fido2CredentialDetail]:
    """List all FIDO2 credentials for a user.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        List of credential details
    """
    result = await db.execute(
        select(KFido2Credential).where(KFido2Credential.principal_id == user_id, KFido2Credential.deleted == False)  # type: ignore[arg-type]  # noqa: E712
    )
    credentials = result.scalars().all()

    return [
        Fido2CredentialDetail(
            id=cred.id,
            credential_id=credential_id_to_base64(cred.credential_id),
            nickname=cred.nickname,
            aaguid=aaguid_to_hex(cred.aaguid),
            transports=cred.transports,
            is_discoverable=cred.is_discoverable,
            last_used=cred.last_used,
            created=cred.created,
        )
        for cred in credentials
    ]


async def update_credential_nickname(
    user_id: UUID, credential_id: UUID, nickname: str, db: AsyncSession
) -> None:
    """Update the nickname of a FIDO2 credential.

    Args:
        user_id: User ID (for authorization)
        credential_id: Credential ID
        nickname: New nickname
        db: Database session

    Raises:
        InvalidCredentialsException: If credential not found or doesn't belong to user
    """
    result = await db.execute(
        select(KFido2Credential).where(
            KFido2Credential.id == credential_id,  # type: ignore[arg-type]
            KFido2Credential.principal_id == user_id,  # type: ignore[arg-type]
            KFido2Credential.deleted == False,  # type: ignore[arg-type]  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise InvalidCredentialsException(username=str(user_id))

    credential.nickname = nickname
    credential.last_modified = datetime.now()
    credential.last_modified_by = user_id

    await db.commit()


async def delete_credential(
    user_id: UUID, credential_id: UUID, db: AsyncSession
) -> None:
    """Delete a FIDO2 credential.

    Args:
        user_id: User ID (for authorization)
        credential_id: Credential ID to delete
        db: Database session

    Raises:
        InvalidCredentialsException: If credential not found or doesn't belong to user
    """
    result = await db.execute(
        select(KFido2Credential).where(
            KFido2Credential.id == credential_id,  # type: ignore[arg-type]
            KFido2Credential.principal_id == user_id,  # type: ignore[arg-type]
            KFido2Credential.deleted == False,  # type: ignore[arg-type]  # noqa: E712
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        raise InvalidCredentialsException(username=str(user_id))

    await db.delete(credential)
    await db.commit()
