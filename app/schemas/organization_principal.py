from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrganizationPrincipalCreate(BaseModel):
    """Schema for adding a new organization principal."""

    principal_id: UUID
    role: str | None = None
    meta: dict = {}


class OrganizationPrincipalUpdate(BaseModel):
    """Schema for updating organization principal information."""

    role: str | None = None
    meta: dict | None = None


class OrganizationPrincipal(BaseModel):
    """Schema for organization principal response."""

    org_id: UUID
    principal_id: UUID
    role: str | None
    meta: dict

    model_config = ConfigDict(from_attributes=True)


class OrganizationPrincipalDetail(OrganizationPrincipal):
    """Schema for organization principal detailed response with audit fields."""

    deleted_at: datetime | None
    created: datetime
    created_by: UUID
    last_modified: datetime
    last_modified_by: UUID


class OrganizationPrincipalList(BaseModel):
    """Schema for organization principal list response."""

    principals: list[OrganizationPrincipalDetail]


__all__ = [
    "OrganizationPrincipalCreate",
    "OrganizationPrincipalUpdate",
    "OrganizationPrincipal",
    "OrganizationPrincipalDetail",
    "OrganizationPrincipalList",
]
