"""Doc management endpoints for creating, listing, updating, and deleting docs."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...core.exceptions.domain_exceptions import (
    DocAlreadyExistsException,
    DocNotFoundException,
    DocUpdateConflictException,
    InsufficientPrivilegesException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import docs as docs_logic
from ...schemas.doc import DocCreate, DocDetail, DocList, DocUpdate
from ...schemas.user import TokenData, UserDetail
from ..deps import get_current_token, get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocDetail, status_code=status.HTTP_201_CREATED)
async def create_doc(
    doc_data: DocCreate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocDetail:
    """Create a new doc."""
    user_id = UUID(token_data.sub)

    try:
        doc = await docs_logic.create_doc(
            doc_data=doc_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return DocDetail.model_validate(doc)
    except DocAlreadyExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("", response_model=DocList)
async def list_docs(
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocList:
    """List all docs in the given organization."""
    user_id = UUID(token_data.sub)

    try:
        docs = await docs_logic.list_docs(org_id=org_id, user_id=user_id, db=db)
        return DocList(docs=[DocDetail.model_validate(doc) for doc in docs])
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.get("/{doc_id}", response_model=DocDetail)
async def get_doc(
    doc_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocDetail:
    """Get a single doc by ID."""
    user_id = UUID(token_data.sub)

    try:
        doc = await docs_logic.get_doc(
            doc_id=doc_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
        )
        return DocDetail.model_validate(doc)
    except DocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.patch("/{doc_id}", response_model=DocDetail)
async def update_doc(
    doc_id: UUID,
    doc_data: DocUpdate,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocDetail:
    """Update a doc."""
    user_id = UUID(token_data.sub)

    try:
        doc = await docs_logic.update_doc(
            doc_id=doc_id,
            doc_data=doc_data,
            user_id=user_id,
            org_id=org_id,
            db=db,
        )
        return DocDetail.model_validate(doc)
    except DocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except DocUpdateConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(
    doc_id: UUID,
    org_id: Annotated[UUID, Query(description="Organization ID")],
    token_data: Annotated[TokenData, Depends(get_current_token)],
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    hard_delete: Annotated[bool, Query(description="Hard delete the doc")] = False,
) -> None:
    """Delete a doc."""
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
        await docs_logic.delete_doc(
            doc_id=doc_id,
            org_id=org_id,
            user_id=user_id,
            db=db,
            hard_delete=hard_delete,
        )
    except DocNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except UnauthorizedOrganizationAccessException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e
