from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str
    full_name: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


class UserInDB(UserBase):
    """Schema for user as stored in database."""

    hashed_password: str


class User(UserBase):
    """Schema for user response (without sensitive data)."""

    id: str
    username: str
    meta: dict
    last_modified: datetime
    last_modified_by: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token payload data."""

    username: str | None = None
