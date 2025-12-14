from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.repr_mixin import SecureReprMixin
from app.models.k_principal import SystemRole


class UserCreate(SecureReprMixin, BaseModel):
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
    system_role: SystemRole | None = None
    # meta: dict


class UserUpdateUsername(SecureReprMixin, BaseModel):
    """Schema for updating user username."""

    username: str


class UserUpdateEmail(SecureReprMixin, BaseModel):
    """Schema for updating user email."""

    email: EmailStr


class UserUpdatePrimaryPhone(SecureReprMixin, BaseModel):
    """Schema for updating user phone."""

    primary_phone: str


class UserUpdate(SecureReprMixin, BaseModel):
    """Schema for updating user information."""

    time_zone: str | None = None
    name_prefix: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None = None
    name_suffix: str | None = None
    display_name: str | None = None
    default_locale: str | None = None
    system_role: SystemRole | None = None
    meta: dict | None = None


class User(SecureReprMixin, BaseModel):
    """Schema for user response (without audit fields)."""

    id: UUID
    username: str
    primary_email: EmailStr
    primary_email_verified: bool
    primary_phone: str | None = None
    primary_phone_verified: bool
    enabled: bool
    time_zone: str
    name_prefix: str | None = None
    first_name: str
    middle_name: str | None = None
    last_name: str
    name_suffix: str | None = None
    display_name: str
    default_locale: str
    system_role: SystemRole
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class UserDetail(User):
    """Schema for user detailed response (includes audit fields)."""

    scope: str
    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class UserList(SecureReprMixin, BaseModel):
    """Schema for user list response."""

    users: list[User]


class Token(SecureReprMixin, BaseModel):
    """Schema for authentication token response."""

    access_token: str
    token_type: str
    refresh_token: str | None = (
        None  # None for web clients (token in cookie), str for mobile clients
    )


class TokenData(SecureReprMixin, BaseModel):
    """Schema for token payload data."""

    sub: str
    scope: str
    iss: str
    aud: str
    jti: str
    iat: datetime
    exp: datetime
    ss: datetime  # Session start time
