"""Team reviewer management endpoints for adding, listing, updating, and removing team reviewers."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    TeamNotFoundException,
    TeamReviewerAlreadyExistsException,
    TeamReviewerNotFoundException,
)
from ...logic.v1 import team_reviewers as team_reviewers_logic
from ...schemas.team_reviewer import (
    TeamReviewerCreate,
    TeamReviewerDetail,
    TeamReviewerList,
    TeamReviewerUpdate,
)
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/teams/{team_id}/reviewers", tags=["team-reviewers"])


@router.post("", response_model=TeamReviewerDetail, status_code=status.HTTP_201_CREATED)
async def add_team_reviewer(
    team_id: UUID,
    reviewer_data: TeamReviewerCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamReviewerDetail:
    """Add a new reviewer to a team."""
    user_id = UUID(token_data.sub)

    try:
        reviewer = await team_reviewers_logic.add_team_reviewer(
            team_id=team_id,
            reviewer_data=reviewer_data,
            user_id=user_id,
            db=db,
        )
        return TeamReviewerDetail.model_validate(reviewer)
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except TeamReviewerAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=TeamReviewerList)
async def list_team_reviewers(
    team_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamReviewerList:
    """List all reviewers of a team."""
    try:
        reviewers = await team_reviewers_logic.list_team_reviewers(
            team_id=team_id, db=db
        )
        return TeamReviewerList(
            reviewers=[
                TeamReviewerDetail.model_validate(reviewer) for reviewer in reviewers
            ]
        )
    except TeamNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{principal_id}", response_model=TeamReviewerDetail)
async def get_team_reviewer(
    team_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamReviewerDetail:
    """Get a single team reviewer."""
    try:
        reviewer = await team_reviewers_logic.get_team_reviewer(
            team_id=team_id,
            principal_id=principal_id,
            db=db,
        )
        return TeamReviewerDetail.model_validate(reviewer)
    except TeamReviewerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{principal_id}", response_model=TeamReviewerDetail)
async def update_team_reviewer(
    team_id: UUID,
    principal_id: UUID,
    reviewer_data: TeamReviewerUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TeamReviewerDetail:
    """Update a team reviewer."""
    user_id = UUID(token_data.sub)

    try:
        reviewer = await team_reviewers_logic.update_team_reviewer(
            team_id=team_id,
            principal_id=principal_id,
            reviewer_data=reviewer_data,
            user_id=user_id,
            db=db,
        )
        return TeamReviewerDetail.model_validate(reviewer)
    except TeamReviewerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{principal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_reviewer(
    team_id: UUID,
    principal_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Remove a reviewer from a team."""
    try:
        await team_reviewers_logic.remove_team_reviewer(
            team_id=team_id,
            principal_id=principal_id,
            db=db,
        )
    except TeamReviewerNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
