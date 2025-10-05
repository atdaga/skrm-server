from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.schemas.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current authenticated user information."""
    return current_user
