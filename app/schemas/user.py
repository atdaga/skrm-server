from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    username: str
    password: str
    primary_email: EmailStr
    primary_phone: str | None = None
    time_zone: str | None = None
    name_prefix: str | None = None
    first_name: str
    middle_name: str | None = None
    last_name: str
    name_suffix: str | None = None
    display_name: str
    default_locale: str | None = None
    # meta: dict


class UserUpdateUsername(BaseModel):
    """Schema for updating user username."""

    username: str


class UserUpdateEmail(BaseModel):
    """Schema for updating user email."""

    email: EmailStr


class UserUpdatePrimaryPhone(BaseModel):
    """Schema for updating user phone."""

    primary_phone: str


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    time_zone: str | None = None
    name_prefix: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    name_suffix: str | None = None
    display_name: str | None = None
    default_locale: str | None = None
    meta: dict | None = None


class User(BaseModel):
    """Schema for user response (without sensitive data)."""

    enabled: bool
    time_zone: str
    name_prefix: str | None = None
    first_name: str
    middle_name: str | None = None
    last_name: str
    name_suffix: str | None = None
    display_name: str
    default_locale: str

    model_config = ConfigDict(from_attributes=True)


class UserDetail(User):
    """Schema for user detailed response."""

    id: UUID
    scope: str
    username: str
    primary_email: EmailStr
    primary_email_verified: bool
    primary_phone: str | None = None
    primary_phone_verified: bool
    system_role: str
    meta: dict
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class Token(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    token_type: str
    refresh_token: str


class TokenData(BaseModel):
    """Schema for token payload data."""

    sub: str
    scope: str
    iss: str
