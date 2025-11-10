"""Feature doc relationship management endpoints for adding, listing, updating, and removing feature docs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    DocNotFoundException,
    FeatureDocAlreadyExistsException,
    FeatureDocNotFoundException,
    FeatureNotFoundException,
    InsufficientPrivilegesException,
)
from ...logic.v1 import feature_docs as feature_docs_logic
from ...schemas.feature_doc import (
    FeatureDocCreate,
    FeatureDocDetail,
    FeatureDocList,
    FeatureDocUpdate,
)
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/features/{feature_id}/docs", tags=["feature-docs"])


@router.post("", response_model=FeatureDocDetail, status_code=status.HTTP_201_CREATED)
async def add_feature_doc(
    feature_id: UUID,
    doc_data: FeatureDocCreate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDocDetail:
    """Add a new doc to a feature."""
    user_id = UUID(token_data.sub)

    try:
        feature_doc = await feature_docs_logic.add_feature_doc(
            feature_id=feature_id,
            doc_data=doc_data,
            user_id=user_id,
            db=db,
        )
        return FeatureDocDetail.model_validate(feature_doc)
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except DocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except FeatureDocAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e


@router.get("", response_model=FeatureDocList)
async def list_feature_docs(
    feature_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDocList:
    """List all docs for a feature."""
    try:
        docs = await feature_docs_logic.list_feature_docs(feature_id=feature_id, db=db)
        return FeatureDocList(
            docs=[FeatureDocDetail.model_validate(doc) for doc in docs]
        )
    except FeatureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.get("/{doc_id}", response_model=FeatureDocDetail)
async def get_feature_doc(
    feature_id: UUID,
    doc_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDocDetail:
    """Get a single feature doc relationship."""
    try:
        feature_doc = await feature_docs_logic.get_feature_doc(
            feature_id=feature_id,
            doc_id=doc_id,
            db=db,
        )
        return FeatureDocDetail.model_validate(feature_doc)
    except FeatureDocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.patch("/{doc_id}", response_model=FeatureDocDetail)
async def update_feature_doc(
    feature_id: UUID,
    doc_id: UUID,
    doc_data: FeatureDocUpdate,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FeatureDocDetail:
    """Update a feature doc relationship."""
    user_id = UUID(token_data.sub)

    try:
        feature_doc = await feature_docs_logic.update_feature_doc(
            feature_id=feature_id,
            doc_id=doc_id,
            doc_data=doc_data,
            user_id=user_id,
            db=db,
        )
        return FeatureDocDetail.model_validate(feature_doc)
    except FeatureDocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_feature_doc(
    feature_id: UUID,
    doc_id: UUID,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[
        bool, Query(description="Hard delete the relationship")
    ] = False,
) -> None:
    """Remove a doc from a feature."""
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
        await feature_docs_logic.remove_feature_doc(
            feature_id=feature_id,
            doc_id=doc_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except FeatureDocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
