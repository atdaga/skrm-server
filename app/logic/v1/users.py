"""Business logic for user management operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth import get_password_hash
from ...core.exceptions.domain_exceptions import (
    UnauthorizedUserUpdateException,
    UserAlreadyExistsException,
    UserNotFoundException,
    UserUpdateConflictException,
)
from ...models import KPrincipal, KPrincipalIdentity
from ...models.k_principal import SystemRole
from ...schemas.user import (
    UserCreate,
    UserDetail,
    UserUpdate,
    UserUpdateEmail,
    UserUpdatePrimaryPhone,
    UserUpdateUsername,
)


async def get_current_user_info(user: UserDetail, db: AsyncSession) -> UserDetail:
    """Get current user information.

    Args:
        user: The authenticated user from the token
        db: Database session (for future use)

    Returns:
        User detail model
    """
    return user


async def create_user(
    user_data: UserCreate,
    created_by_user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KPrincipal:
    """Create a new user.

    Args:
        user_data: User creation data
        created_by_user_id: ID of the user creating the user (must be systemRoot)
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        The created user model

    Raises:
        UserAlreadyExistsException: If a user with the same username already exists in the scope
    """
    # Create new user principal with audit fields
    new_user = KPrincipal(
        scope=scope,
        username=user_data.username,
        primary_email=user_data.primary_email,
        primary_phone=user_data.primary_phone,
        time_zone=user_data.time_zone or "UTC",
        name_prefix=user_data.name_prefix,
        first_name=user_data.first_name,
        middle_name=user_data.middle_name,
        last_name=user_data.last_name,
        name_suffix=user_data.name_suffix,
        display_name=user_data.display_name,
        default_locale=user_data.default_locale or "en",
        system_role=user_data.system_role
        if user_data.system_role is not None
        else SystemRole.SYSTEM_USER,
        created_by=created_by_user_id,
        last_modified_by=created_by_user_id,
    )

    db.add(new_user)

    try:
        await db.flush()  # Flush to get the user ID without committing

        # Create password identity
        password_hash = get_password_hash(user_data.password)
        identity = KPrincipalIdentity(
            principal_id=new_user.id,
            password=password_hash,
            created_by=created_by_user_id,
            last_modified_by=created_by_user_id,
        )
        db.add(identity)

        await db.commit()
        await db.refresh(new_user)
    except IntegrityError as e:
        await db.rollback()
        # Username constraint failed
        raise UserAlreadyExistsException(
            username=user_data.username, scope=scope
        ) from e

    return new_user


async def list_users(scope: str, db: AsyncSession) -> list[KPrincipal]:
    """List all users in a scope.

    Args:
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        List of user models
    """
    stmt = select(KPrincipal).where(
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return list(users)


async def get_user(user_id: UUID, scope: str, db: AsyncSession) -> KPrincipal:
    """Get a single user by ID.

    Args:
        user_id: ID of the user to retrieve
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        The user model

    Raises:
        UserNotFoundException: If the user is not found
    """
    stmt = select(KPrincipal).where(
        KPrincipal.id == user_id,  # type: ignore[arg-type]
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    return user


async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    requesting_user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KPrincipal:
    """Update a user.

    Args:
        user_id: ID of the user to update
        user_data: User update data
        requesting_user_id: ID of the user performing the update (must be the user themselves)
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        The updated user model

    Raises:
        UserNotFoundException: If the user is not found
        UnauthorizedUserUpdateException: If requesting user is not the user being updated
    """
    # Check authorization: only the user themselves can update
    if user_id != requesting_user_id:
        raise UnauthorizedUserUpdateException(
            user_id=user_id, requesting_user_id=requesting_user_id
        )

    stmt = select(KPrincipal).where(
        KPrincipal.id == user_id,  # type: ignore[arg-type]
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    # Update only provided fields
    if user_data.time_zone is not None:
        user.time_zone = user_data.time_zone
    if user_data.name_prefix is not None:
        user.name_prefix = user_data.name_prefix
    if user_data.first_name is not None:
        user.first_name = user_data.first_name
    if user_data.middle_name is not None:
        user.middle_name = user_data.middle_name
    if user_data.last_name is not None:
        user.last_name = user_data.last_name
    if user_data.name_suffix is not None:
        user.name_suffix = user_data.name_suffix
    if user_data.display_name is not None:
        user.display_name = user_data.display_name
    if user_data.default_locale is not None:
        user.default_locale = user_data.default_locale
    if user_data.system_role is not None:
        user.system_role = user_data.system_role
    if user_data.meta is not None:
        user.meta = user_data.meta

    # Update audit fields
    user.last_modified = datetime.now()
    user.last_modified_by = requesting_user_id

    await db.commit()
    await db.refresh(user)

    return user


async def update_user_username(
    user_id: UUID,
    user_data: UserUpdateUsername,
    requesting_user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KPrincipal:
    """Update a user's username.

    Args:
        user_id: ID of the user to update
        user_data: Username update data
        requesting_user_id: ID of the user performing the update (must be the user themselves)
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        The updated user model

    Raises:
        UserNotFoundException: If the user is not found
        UnauthorizedUserUpdateException: If requesting user is not the user being updated
        UserUpdateConflictException: If the new username already exists
    """
    # Check authorization: only the user themselves can update
    if user_id != requesting_user_id:
        raise UnauthorizedUserUpdateException(
            user_id=user_id, requesting_user_id=requesting_user_id
        )

    stmt = select(KPrincipal).where(
        KPrincipal.id == user_id,  # type: ignore[arg-type]
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    # Update username
    user.username = user_data.username

    # Update audit fields
    user.last_modified = datetime.now()
    user.last_modified_by = requesting_user_id

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as e:
        await db.rollback()
        raise UserUpdateConflictException(
            user_id=user_id, username=user_data.username, scope=scope
        ) from e

    return user


async def update_user_email(
    user_id: UUID,
    user_data: UserUpdateEmail,
    requesting_user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KPrincipal:
    """Update a user's primary email.

    Args:
        user_id: ID of the user to update
        user_data: Email update data
        requesting_user_id: ID of the user performing the update (must be the user themselves)
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        The updated user model

    Raises:
        UserNotFoundException: If the user is not found
        UnauthorizedUserUpdateException: If requesting user is not the user being updated
    """
    # Check authorization: only the user themselves can update
    if user_id != requesting_user_id:
        raise UnauthorizedUserUpdateException(
            user_id=user_id, requesting_user_id=requesting_user_id
        )

    stmt = select(KPrincipal).where(
        KPrincipal.id == user_id,  # type: ignore[arg-type]
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    # Update email and mark as unverified
    user.primary_email = user_data.email
    user.primary_email_verified = False

    # Update audit fields
    user.last_modified = datetime.now()
    user.last_modified_by = requesting_user_id

    await db.commit()
    await db.refresh(user)

    return user


async def update_user_primary_phone(
    user_id: UUID,
    user_data: UserUpdatePrimaryPhone,
    requesting_user_id: UUID,
    scope: str,
    db: AsyncSession,
) -> KPrincipal:
    """Update a user's primary phone.

    Args:
        user_id: ID of the user to update
        user_data: Phone update data
        requesting_user_id: ID of the user performing the update (must be the user themselves)
        scope: Scope for multi-tenancy
        db: Database session

    Returns:
        The updated user model

    Raises:
        UserNotFoundException: If the user is not found
        UnauthorizedUserUpdateException: If requesting user is not the user being updated
    """
    # Check authorization: only the user themselves can update
    if user_id != requesting_user_id:
        raise UnauthorizedUserUpdateException(
            user_id=user_id, requesting_user_id=requesting_user_id
        )

    stmt = select(KPrincipal).where(
        KPrincipal.id == user_id,  # type: ignore[arg-type]
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    # Update phone and mark as unverified
    user.primary_phone = user_data.primary_phone
    user.primary_phone_verified = False

    # Update audit fields
    user.last_modified = datetime.now()
    user.last_modified_by = requesting_user_id

    await db.commit()
    await db.refresh(user)

    return user


async def delete_user(user_id: UUID, scope: str, db: AsyncSession) -> None:
    """Delete a user.

    Args:
        user_id: ID of the user to delete
        scope: Scope for multi-tenancy
        db: Database session

    Raises:
        UserNotFoundException: If the user is not found
    """
    stmt = select(KPrincipal).where(
        KPrincipal.id == user_id,  # type: ignore[arg-type]
        KPrincipal.scope == scope,  # type: ignore[arg-type]
        KPrincipal.deleted == False,  # type: ignore[arg-type]  # noqa: E712
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise UserNotFoundException(user_id=user_id)

    # Soft delete by setting deleted flag
    user.deleted = True
    await db.commit()
