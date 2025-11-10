"""Transaction batch API endpoint for executing multiple CRUD operations."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...logic.v1 import txs as txs_logic
from ...schemas.txs import TransactionsRequest, TransactionsResponse
from ...schemas.user import TokenData
from ..deps import get_current_token

router = APIRouter(prefix="/txs", tags=["transactions"])


@router.post("", response_model=TransactionsResponse, status_code=status.HTTP_200_OK)
async def execute_transactions(
    request: TransactionsRequest,
    token_data: Annotated[TokenData, Depends(get_current_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TransactionsResponse:
    """Execute a batch of transactions containing CRUD operations.

    This endpoint allows executing multiple CRUD operations organized into transactions
    that can be executed serially or in parallel. Operations within a transaction are
    atomic - they all succeed or fail together.

    Features:
    - Batch execution of CRUD operations across multiple domain objects
    - Serial or parallel execution modes for transactions and operations
    - Reference resolution using {{tx-id.op-id.result.field}} syntax
    - Dependency management between operations
    - Atomic transactions with automatic rollback on failure

    Args:
        request: Transaction batch request containing transactions and operations
        token_data: Authenticated user token data
        db: Database session

    Returns:
        TransactionsResponse with overall status and detailed results for each transaction/operation
    """
    user_id = UUID(token_data.sub)

    response = await txs_logic.execute_transactions(
        request=request,
        user_id=user_id,
        db=db,
    )

    return response
