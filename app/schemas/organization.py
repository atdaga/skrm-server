from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.repr_mixin import SecureReprMixin


class OrganizationCreate(SecureReprMixin, BaseModel):
    """Schema for creating a new organization."""

    name: str
    alias: str
    meta: dict = {}

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, v: str) -> str:
        """Validate alias format: lowercase alphanumeric starting with letter."""
        if not v:
            raise ValueError("Alias cannot be empty")
        if not v[0].isalpha() or not v[0].islower():
            raise ValueError("Alias must start with a lowercase letter")
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                "Alias can only contain lowercase letters, digits, and underscores"
            )
        if not v.islower():
            raise ValueError("Alias must be lowercase")
        return v


class OrganizationUpdate(SecureReprMixin, BaseModel):
    """Schema for updating organization information."""

    name: str | None = None
    alias: str | None = None
    meta: dict | None = None

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, v: str | None) -> str | None:
        """Validate alias format: lowercase alphanumeric starting with letter."""
        if v is None:
            return v
        if not v:
            raise ValueError("Alias cannot be empty")
        if not v[0].isalpha() or not v[0].islower():
            raise ValueError("Alias must start with a lowercase letter")
        if not all(c.isalnum() or c == "_" for c in v):
            raise ValueError(
                "Alias can only contain lowercase letters, digits, and underscores"
            )
        if not v.islower():
            raise ValueError("Alias must be lowercase")
        return v


class Organization(SecureReprMixin, BaseModel):
    """Schema for organization response."""

    id: UUID
    name: str
    alias: str
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class OrganizationDetail(Organization):
    """Schema for organization detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class OrganizationList(SecureReprMixin, BaseModel):
    """Schema for organization list response."""

    organizations: list[OrganizationDetail]


__all__ = [
    "OrganizationCreate",
    "OrganizationUpdate",
    "Organization",
    "OrganizationDetail",
    "OrganizationList",
]
