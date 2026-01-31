"""Feature management endpoints for creating, listing, updating, and deleting features."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db, logger
from ...core.exceptions.domain_exceptions import (
    FeatureAlreadyExistsException,
    FeatureNotFoundException,
    FeatureUpdateConflictException,
    InsufficientPrivilegesException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import features as features_logic
from ...schemas.feature import FeatureCreate, FeatureDetail, FeatureList, FeatureUpdate
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/features", tags=["features"])


@router.post("", response_model=FeatureDetail, status_code=status.HTTP_201_CREATED)
async def create_feature(
    feature_data: FeatureCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDetail:
    """Create a new feature."""
    user_id = UUID(token_data.sub)

    try:
        feature = await features_logic.create_feature(
            feature_data=feature_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return FeatureDetail.model_validate(feature)
    except FeatureAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=FeatureList)
async def list_features(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureList:
    """List all features in the given organization."""
    logger.info(f"Listing features for organization {org_id}")
    user_id = UUID(token_data.sub)
    logger.info(f"User ID: {user_id}")

    try:
        features = await features_logic.list_features(
            org_id=org_id, user_id=user_id, db=db
        )
        logger.info(f"Features: {features}")
        return FeatureList(
            features=[FeatureDetail.model_validate(feature) for feature in features]
        )
    except UnauthorizedOrganizationAccessException as e:
        logger.error(f"Unauthorized organization access: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{feature_id}", response_model=FeatureDetail)
async def get_feature(
    feature_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDetail:
    """Get a single feature by ID."""
    user_id = UUID(token_data.sub)

    try:
        feature = await features_logic.get_feature(
            feature_id=feature_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return FeatureDetail.model_validate(feature)
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{feature_id}", response_model=FeatureDetail)
async def update_feature(
    feature_id: UUID,
    feature_data: FeatureUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDetail:
    """Update a feature."""
    user_id = UUID(token_data.sub)

    try:
        feature = await features_logic.update_feature(
            feature_id=feature_id,
            feature_data=feature_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return FeatureDetail.model_validate(feature)
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except FeatureUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature(
    feature_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[bool, Query(description="Hard delete the feature")] = False,
) -> None:
    """Delete a feature."""
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
        await features_logic.delete_feature(
            feature_id=feature_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
