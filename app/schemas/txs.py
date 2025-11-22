"""Schemas for transaction batch API."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.repr_mixin import SecureReprMixin

# ============================================================================
# Request Schemas (Operation Parameters)
# ============================================================================


class CreateParams(SecureReprMixin, BaseModel):
    """Parameters for create operation."""

    data: dict[str, Any] = Field(
        ..., description="Data to create the domain object with"
    )


class GetParams(SecureReprMixin, BaseModel):
    """Parameters for get operation."""

    id: str | UUID = Field(..., description="ID of the domain object to get")
    org_id: str | UUID | None = Field(
        None, description="Organization ID (required for standard domain objects)"
    )
    team_id: str | UUID | None = Field(
        None, description="Team ID (required for team child objects)"
    )
    task_id: str | UUID | None = Field(
        None, description="Task ID (required for task child objects)"
    )
    feature_id: str | UUID | None = Field(
        None, description="Feature ID (required for feature child objects)"
    )
    project_id: str | UUID | None = Field(
        None, description="Project ID (required for project child objects)"
    )
    sprint_id: str | UUID | None = Field(
        None, description="Sprint ID (required for sprint child objects)"
    )
    fields: list[str] | None = Field(None, description="Specific fields to return")


class SortCriteria(SecureReprMixin, BaseModel):
    """Sort criteria for list operations."""

    field: str = Field(..., description="Field name to sort by")
    direction: Literal["asc", "desc"] = Field(..., description="Sort direction")


class PaginationParams(SecureReprMixin, BaseModel):
    """Pagination parameters for list operations."""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(100, ge=1, le=1000, description="Number of items per page")


class ListParams(SecureReprMixin, BaseModel):
    """Parameters for list operation."""

    filters: dict[str, Any] | None = Field(None, description="Filter criteria")
    sort: list[SortCriteria] | None = Field(None, description="Sort criteria")
    pagination: PaginationParams | None = Field(
        None, description="Pagination parameters"
    )
    fields: list[str] | None = Field(None, description="Specific fields to return")


class UpdateParams(SecureReprMixin, BaseModel):
    """Parameters for update operation."""

    id: str | UUID = Field(..., description="ID of the domain object to update")
    data: dict[str, Any] = Field(
        ..., description="Data to update the domain object with"
    )
    partial: bool = Field(
        True,
        description="Whether this is a partial update (PATCH) or full update (PUT)",
    )


class DeleteParams(SecureReprMixin, BaseModel):
    """Parameters for delete operation."""

    id: str | UUID = Field(..., description="ID of the domain object to delete")
    soft_delete: bool = Field(
        True, description="Whether to perform a soft delete or hard delete"
    )


# ============================================================================
# Operation Schema
# ============================================================================


class Operation(SecureReprMixin, BaseModel):
    """A CRUD operation on a domain object."""

    id: str | None = Field(None, description="Unique identifier for the operation")
    operation: Literal["create", "get", "list", "update", "delete"] = Field(
        ..., description="Type of CRUD operation"
    )
    domain_object: str = Field(..., description="Type of domain object")
    params: CreateParams | GetParams | ListParams | UpdateParams | DeleteParams = Field(
        ..., description="Operation-specific parameters"
    )
    depends_on: list[str] | None = Field(
        None,
        description="List of operation IDs that must complete before this operation",
    )


# ============================================================================
# Transaction Schema
# ============================================================================


class TransactionGroup(SecureReprMixin, BaseModel):
    """A transaction containing CRUD operations."""

    id: str | None = Field(None, description="Unique identifier for the transaction")
    execution_mode: Literal["serial", "parallel"] = Field(
        "serial", description="How operations execute within this transaction"
    )
    operations: list[Operation] = Field(
        ..., min_length=1, description="List of CRUD operations"
    )


# ============================================================================
# Request Schema
# ============================================================================


class TransactionsRequest(SecureReprMixin, BaseModel):
    """Top-level transaction batch request."""

    execution_mode: Literal["serial", "parallel"] = Field(
        "serial", description="How transactions execute relative to each other"
    )
    txs: list[TransactionGroup] = Field(
        ..., min_length=1, alias="txs", description="List of transactions"
    )


# ============================================================================
# Response Schemas
# ============================================================================


class OperationResult(SecureReprMixin, BaseModel):
    """Result of a single operation."""

    id: str | None = None
    operation: str
    domain_object: str
    status: Literal["success", "failure"]
    result: Any | None = None
    error: str | None = None
    error_type: str | None = None


class TransactionResult(SecureReprMixin, BaseModel):
    """Result of a single transaction."""

    id: str | None = None
    status: Literal["success", "failure", "skipped"]
    operations: list[OperationResult]
    error: str | None = None


class TransactionsResponse(SecureReprMixin, BaseModel):
    """Response for transaction batch request."""

    status: Literal["success", "failure"] = Field(..., description="Overall status")
    transactions: list[TransactionResult] = Field(
        ..., description="Results of all transactions"
    )


__all__ = [
    "CreateParams",
    "GetParams",
    "ListParams",
    "UpdateParams",
    "DeleteParams",
    "SortCriteria",
    "PaginationParams",
    "Operation",
    "TransactionGroup",
    "TransactionsRequest",
    "OperationResult",
    "TransactionResult",
    "TransactionsResponse",
]
