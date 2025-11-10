"""Team member management endpoints for adding, listing, updating, and removing team members."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    InsufficientPrivilegesException,
    TeamMemberAlreadyExistsException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
)
from ...logic.v1 import team_members as team_members_logic
from ...schemas.team_member import (
    TeamMemberCreate,
    TeamMemberDetail,
    TeamMemberList,
    TeamMemberUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/teams/{team_id}/members", tags=["team-members"])


@router.post("", response_model=TeamMemberDetail, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: UUID,
    member_data: TeamMemberCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberDetail:
    """Add a new member to a team."""
    user_id = UUID(token_data.sub)

    try:
        member = await team_members_logic.add_team_member(
            team_id=team_id,
            member_data=member_data,
            user_id=user_id,
            db=db,
        )
        return TeamMemberDetail.model_validate(member)
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TeamMemberAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=TeamMemberList)
async def list_team_members(
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberList:
    """List all members of a team."""
    try:
        members = await team_members_logic.list_team_members(team_id=team_id, db=db)
        return TeamMemberList(
            members=[TeamMemberDetail.model_validate(member) for member in members]
        )
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{principal_id}", response_model=TeamMemberDetail)
async def get_team_member(
    team_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberDetail:
    """Get a single team member."""
    try:
        member = await team_members_logic.get_team_member(
            team_id=team_id,
            principal_id=principal_id,
            db=db,
        )
        return TeamMemberDetail.model_validate(member)
    except TeamMemberNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{principal_id}", response_model=TeamMemberDetail)
async def update_team_member(
    team_id: UUID,
    principal_id: UUID,
    member_data: TeamMemberUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamMemberDetail:
    """Update a team member."""
    user_id = UUID(token_data.sub)

    try:
        member = await team_members_logic.update_team_member(
            team_id=team_id,
            principal_id=principal_id,
            member_data=member_data,
            user_id=user_id,
            db=db,
        )
        return TeamMemberDetail.model_validate(member)
    except TeamMemberNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{principal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the relationship")
    ] = False,
) -> None:
    """Remove a member from a team."""
    user_id = UUID(token_data.sub)

    # Check authorization for hard delete
    if hard_delete:  # pragma: no cover
        from ...logic import deps as deps_logic  # pragma: no cover

        try:  # pragma: no cover
            deps_logic.check_hard_delete_privileges(current_user)  # pragma: no cover
        except InsufficientPrivilegesException as e:  # pragma: no cover
            raise HTTPException(  # pragma: no cover
                status_code=status.HTTP_403_FORBIDDEN,
                detail=e.message,
            ) from e

    try:
        await team_members_logic.remove_team_member(
            team_id=team_id,
            principal_id=principal_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except TeamMemberNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
