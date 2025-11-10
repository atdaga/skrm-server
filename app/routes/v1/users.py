"""User management endpoints for creating, listing, updating, and deleting users."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    UnauthorizedUserUpdateException,
    UserAlreadyExistsException,
    UserNotFoundException,
    UserUpdateConflictException,
)
from ...logic.v1 import users as users_logic
from ...schemas.user import (
    User,
    UserCreate,
    UserDetail,
    UserList,
    UserUpdate,
    UserUpdateEmail,
    UserUpdatePrimaryPhone,
    UserUpdateUsername,
)
from ..deps import get_current_user, get_system_root_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserDetail, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: Annotated[UserDetail, Depends(get_system_root_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Create a new user.

    Requires systemRoot role.
    """
    try:
        user = await users_logic.create_user(
            user_data=user_data,
            created_by_user_id=current_user.id,
            scope=current_user.scope,
            db=db,
        )
        return UserDetail.model_validate(user)
    except UserAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=UserList)
async def list_users(
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserList:
    """List all users in the current user's scope."""
    users = await users_logic.list_users(scope=current_user.scope, db=db)
    return UserList(users=[User.model_validate(user) for user in users])


@router.get("/me", response_model=UserDetail)
async def get_current_user_info(
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Get current authenticated user information."""
    return await users_logic.get_current_user_info(current_user, db)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: UUID,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get a single user by ID."""
    try:
        user = await users_logic.get_user(
            user_id=user_id,
            scope=current_user.scope,
            db=db,
        )
        return User.model_validate(user)
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{user_id}", response_model=UserDetail)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Update a user.

    Only the user themselves can update their information.
    """
    try:
        user = await users_logic.update_user(
            user_id=user_id,
            user_data=user_data,
            requesting_user_id=current_user.id,
            scope=current_user.scope,
            db=db,
        )
        return UserDetail.model_validate(user)
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedUserUpdateException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{user_id}/username", response_model=UserDetail)
async def update_user_username(
    user_id: UUID,
    user_data: UserUpdateUsername,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Update a user's username.

    Only the user themselves can update their username.
    """
    try:
        user = await users_logic.update_user_username(
            user_id=user_id,
            user_data=user_data,
            requesting_user_id=current_user.id,
            scope=current_user.scope,
            db=db,
        )
        return UserDetail.model_validate(user)
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedUserUpdateException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
    except UserUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.patch("/{user_id}/email", response_model=UserDetail)
async def update_user_email(
    user_id: UUID,
    user_data: UserUpdateEmail,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Update a user's primary email.

    Only the user themselves can update their email.
    """
    try:
        user = await users_logic.update_user_email(
            user_id=user_id,
            user_data=user_data,
            requesting_user_id=current_user.id,
            scope=current_user.scope,
            db=db,
        )
        return UserDetail.model_validate(user)
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedUserUpdateException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{user_id}/primary-phone", response_model=UserDetail)
async def update_user_primary_phone(
    user_id: UUID,
    user_data: UserUpdatePrimaryPhone,
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Update a user's primary phone.

    Only the user themselves can update their phone.
    """
    try:
        user = await users_logic.update_user_primary_phone(
            user_id=user_id,
            user_data=user_data,
            requesting_user_id=current_user.id,
            scope=current_user.scope,
            db=db,
        )
        return UserDetail.model_validate(user)
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedUserUpdateException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[UserDetail, Depends(get_system_root_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[bool, Query(description="Hard delete the user")] = False,
) -> None:
    """Delete a user.

    Requires systemRoot role.
    For hard delete, requires system or systemRoot role.
    """
    # Check authorization for hard delete (systemRoot already required, but verify system/systemRoot)
    if hard_delete:
        from ...core.exceptions.domain_exceptions import InsufficientPrivilegesException
        from ...logic import deps as deps_logic

        try:  # pragma: no cover
            deps_logic.check_hard_delete_privileges(current_user)  # pragma: no cover
        except InsufficientPrivilegesException as e:  # pragma: no cover
            raise HTTPException(  # pragma: no cover
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await users_logic.delete_user(
            user_id=user_id,
            scope=current_user.scope,
            db=db,
            hard_delete=hard_delete,
        )
    except UserNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
