from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import get_db
from ...logic.v1 import users as users_logic
from ...schemas.user import UserDetail
from ..deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserDetail)
async def get_current_user_info(
    current_user: Annotated[UserDetail, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserDetail:
    """Get current authenticated user information."""
    return await users_logic.get_current_user_info(current_user, db)
