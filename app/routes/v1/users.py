from typing import Annotated

from fastapi import APIRouter, Depends

from ...schemas.user import UserDetail
from ..deps import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserDetail)
async def get_current_user_info(
    current_user: Annotated[UserDetail, Depends(get_current_user)]
) -> UserDetail:
    """Get current authenticated user information."""
    return current_user
