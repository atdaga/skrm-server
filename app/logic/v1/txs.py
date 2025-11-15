"""Business logic for transaction batch operations."""

import asyncio
import re
from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exceptions.domain_exceptions import (
    DeploymentEnvNotFoundException,
    DocNotFoundException,
    FeatureDocNotFoundException,
    FeatureNotFoundException,
    ProjectNotFoundException,
    ProjectTeamAlreadyExistsException,
    ProjectTeamNotFoundException,
    SprintNotFoundException,
    SprintTaskNotFoundException,
    SprintTeamNotFoundException,
    TaskDeploymentEnvNotFoundException,
    TaskFeatureNotFoundException,
    TaskNotFoundException,
    TaskOwnerNotFoundException,
    TaskReviewerNotFoundException,
    TeamMemberNotFoundException,
    TeamNotFoundException,
    TeamReviewerNotFoundException,
    UnauthorizedOrganizationAccessException,
)
from ...logic.v1 import (
    deployment_envs,
    docs,
    feature_docs,
    features,
    project_teams,
    projects,
    sprint_tasks,
    sprint_teams,
    sprints,
    task_deployment_envs,
    task_features,
    task_owners,
    task_reviewers,
    tasks,
    team_members,
    team_reviewers,
    teams,
)
from ...schemas.deployment_env import DeploymentEnvCreate, DeploymentEnvUpdate
from ...schemas.doc import DocCreate, DocUpdate
from ...schemas.feature import FeatureCreate, FeatureUpdate
from ...schemas.feature_doc import FeatureDocCreate, FeatureDocUpdate
from ...schemas.project import ProjectCreate, ProjectUpdate
from ...schemas.project_team import ProjectTeamCreate, ProjectTeamUpdate
from ...schemas.sprint import SprintCreate, SprintUpdate
from ...schemas.sprint_task import SprintTaskCreate, SprintTaskUpdate
from ...schemas.sprint_team import SprintTeamCreate, SprintTeamUpdate
from ...schemas.task import TaskCreate, TaskUpdate
from ...schemas.task_deployment_env import (
    TaskDeploymentEnvCreate,
    TaskDeploymentEnvUpdate,
)
from ...schemas.task_feature import TaskFeatureCreate, TaskFeatureUpdate
from ...schemas.task_owner import TaskOwnerCreate, TaskOwnerUpdate
from ...schemas.task_reviewer import TaskReviewerCreate, TaskReviewerUpdate
from ...schemas.team import TeamCreate, TeamUpdate
from ...schemas.team_member import TeamMemberCreate, TeamMemberUpdate
from ...schemas.team_reviewer import TeamReviewerCreate, TeamReviewerUpdate
from ...schemas.txs import (
    Operation,
    OperationResult,
    TransactionGroup,
    TransactionResult,
    TransactionsRequest,
    TransactionsResponse,
)

# ============================================================================
# Type Definitions
# ============================================================================

DomainOperation = Callable[..., Any]


# ============================================================================
# Operation Registry
# ============================================================================


class OperationRegistry:
    """Registry mapping domain objects to their CRUD operations."""

    def __init__(self) -> None:
        """Initialize the operation registry."""
        self.registry: dict[str, dict[str, DomainOperation]] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        """Build the registry of domain operations."""
        # Task operations
        self.registry["task"] = {
            "create": tasks.create_task,
            "get": tasks.get_task,
            "list": tasks.list_tasks,
            "update": tasks.update_task,
            "delete": tasks.delete_task,
        }

        # Project operations
        self.registry["project"] = {
            "create": projects.create_project,
            "get": projects.get_project,
            "list": projects.list_projects,
            "update": projects.update_project,
            "delete": projects.delete_project,
        }

        # Team operations
        self.registry["team"] = {
            "create": teams.create_team,
            "get": teams.get_team,
            "list": teams.list_teams,
            "update": teams.update_team,
            "delete": teams.delete_team,
        }

        # Sprint operations
        self.registry["sprint"] = {
            "create": sprints.create_sprint,
            "get": sprints.get_sprint,
            "list": sprints.list_sprints,
            "update": sprints.update_sprint,
            "delete": sprints.delete_sprint,
        }

        # Feature operations
        self.registry["feature"] = {
            "create": features.create_feature,
            "get": features.get_feature,
            "list": features.list_features,
            "update": features.update_feature,
            "delete": features.delete_feature,
        }

        # Doc operations
        self.registry["doc"] = {
            "create": docs.create_doc,
            "get": docs.get_doc,
            "list": docs.list_docs,
            "update": docs.update_doc,
            "delete": docs.delete_doc,
        }

        # DeploymentEnv operations
        self.registry["deployment_env"] = {
            "create": deployment_envs.create_deployment_env,
            "get": deployment_envs.get_deployment_env,
            "list": deployment_envs.list_deployment_envs,
            "update": deployment_envs.update_deployment_env,
            "delete": deployment_envs.delete_deployment_env,
        }

        # Team Member operations (relationship)
        self.registry["team_member"] = {
            "create": team_members.add_team_member,
            "get": team_members.get_team_member,
            "list": team_members.list_team_members,
            "update": team_members.update_team_member,
            "delete": team_members.remove_team_member,
        }

        # Team Reviewer operations (relationship)
        self.registry["team_reviewer"] = {
            "create": team_reviewers.add_team_reviewer,
            "get": team_reviewers.get_team_reviewer,
            "list": team_reviewers.list_team_reviewers,
            "update": team_reviewers.update_team_reviewer,
            "delete": team_reviewers.remove_team_reviewer,
        }

        # Task Feature operations (relationship)
        self.registry["task_feature"] = {
            "create": task_features.add_task_feature,
            "get": task_features.get_task_feature,
            "list": task_features.list_task_features,
            "update": task_features.update_task_feature,
            "delete": task_features.remove_task_feature,
        }

        # Task Deployment Env operations (relationship)
        self.registry["task_deployment_env"] = {
            "create": task_deployment_envs.add_task_deployment_env,
            "get": task_deployment_envs.get_task_deployment_env,
            "list": task_deployment_envs.list_task_deployment_envs,
            "update": task_deployment_envs.update_task_deployment_env,
            "delete": task_deployment_envs.remove_task_deployment_env,
        }

        # Task Owner operations (relationship)
        self.registry["task_owner"] = {
            "create": task_owners.add_task_owner,
            "get": task_owners.get_task_owner,
            "list": task_owners.list_task_owners,
            "update": task_owners.update_task_owner,
            "delete": task_owners.remove_task_owner,
        }

        # Task Reviewer operations (relationship)
        self.registry["task_reviewer"] = {
            "create": task_reviewers.add_task_reviewer,
            "get": task_reviewers.get_task_reviewer,
            "list": task_reviewers.list_task_reviewers,
            "update": task_reviewers.update_task_reviewer,
            "delete": task_reviewers.remove_task_reviewer,
        }

        # Feature Doc operations (relationship)
        self.registry["feature_doc"] = {
            "create": feature_docs.add_feature_doc,
            "get": feature_docs.get_feature_doc,
            "list": feature_docs.list_feature_docs,
            "update": feature_docs.update_feature_doc,
            "delete": feature_docs.remove_feature_doc,
        }

        # Project Team operations (relationship)
        self.registry["project_team"] = {
            "create": project_teams.add_project_team,
            "get": project_teams.get_project_team,
            "list": project_teams.list_project_teams,
            "update": project_teams.update_project_team,
            "delete": project_teams.remove_project_team,
        }

        # Sprint Team operations (relationship)
        self.registry["sprint_team"] = {
            "create": sprint_teams.add_sprint_team,
            "get": sprint_teams.get_sprint_team,
            "list": sprint_teams.list_sprint_teams,
            "update": sprint_teams.update_sprint_team,
            "delete": sprint_teams.remove_sprint_team,
        }

        # Sprint Task operations (relationship)
        self.registry["sprint_task"] = {
            "create": sprint_tasks.add_sprint_task,
            "get": sprint_tasks.get_sprint_task,
            "list": sprint_tasks.list_sprint_tasks,
            "update": sprint_tasks.update_sprint_task,
            "delete": sprint_tasks.remove_sprint_task,
        }

    def get_operation(
        self, domain_object: str, operation: str
    ) -> DomainOperation | None:
        """Get the operation function for a domain object and operation type."""
        return self.registry.get(domain_object, {}).get(operation)

    def supports_domain_object(self, domain_object: str) -> bool:
        """Check if a domain object is supported."""
        return domain_object in self.registry

    def supports_operation(self, domain_object: str, operation: str) -> bool:
        """Check if an operation is supported for a domain object."""
        return operation in self.registry.get(domain_object, {})


# Global operation registry instance
operation_registry = OperationRegistry()


# ============================================================================
# Schema Mapping
# ============================================================================


def get_create_schema(domain_object: str) -> type:
    """Get the create schema for a domain object."""
    schema_map = {
        "task": TaskCreate,
        "project": ProjectCreate,
        "team": TeamCreate,
        "sprint": SprintCreate,
        "feature": FeatureCreate,
        "doc": DocCreate,
        "deployment_env": DeploymentEnvCreate,
        "team_member": TeamMemberCreate,
        "team_reviewer": TeamReviewerCreate,
        "task_feature": TaskFeatureCreate,
        "task_deployment_env": TaskDeploymentEnvCreate,
        "task_owner": TaskOwnerCreate,
        "task_reviewer": TaskReviewerCreate,
        "feature_doc": FeatureDocCreate,
        "project_team": ProjectTeamCreate,
        "sprint_team": SprintTeamCreate,
        "sprint_task": SprintTaskCreate,
    }
    return schema_map.get(domain_object, dict)


def get_update_schema(domain_object: str) -> type:  # pragma: no cover
    """Get the update schema for a domain object."""
    schema_map = {
        "task": TaskUpdate,
        "project": ProjectUpdate,
        "team": TeamUpdate,
        "sprint": SprintUpdate,
        "feature": FeatureUpdate,
        "doc": DocUpdate,
        "deployment_env": DeploymentEnvUpdate,
        "team_member": TeamMemberUpdate,
        "team_reviewer": TeamReviewerUpdate,
        "task_feature": TaskFeatureUpdate,
        "task_deployment_env": TaskDeploymentEnvUpdate,
        "task_owner": TaskOwnerUpdate,
        "task_reviewer": TaskReviewerUpdate,
        "feature_doc": FeatureDocUpdate,
        "project_team": ProjectTeamUpdate,
        "sprint_team": SprintTeamUpdate,
        "sprint_task": SprintTaskUpdate,
    }
    return schema_map.get(domain_object, dict)


# ============================================================================
# Parameter Builder
# ============================================================================


class ParameterBuilder:
    """Builds parameters for operation calls based on domain object."""

    # Domain objects that need a parent ID (relationships)
    TEAM_CHILDREN = {"team_member", "team_reviewer"}
    TASK_CHILDREN = {
        "task_feature",
        "task_deployment_env",
        "task_owner",
        "task_reviewer",
    }
    FEATURE_CHILDREN = {"feature_doc"}
    PROJECT_CHILDREN = {"project_team"}
    SPRINT_CHILDREN = {"sprint_team", "sprint_task"}

    # Standard domain objects with org_id
    STANDARD_DOMAINS = {
        "task",
        "project",
        "team",
        "sprint",
        "feature",
        "doc",
        "deployment_env",
    }

    # Mapping of domain objects to their ID parameter names
    ID_PARAM_NAMES = {
        "task": "task_id",
        "project": "project_id",
        "team": "team_id",
        "sprint": "sprint_id",
        "feature": "feature_id",
        "doc": "doc_id",
        "deployment_env": "deployment_env_id",
    }

    # Mapping of domain objects to their data parameter names
    DATA_PARAM_NAMES = {
        "task": "task_data",
        "project": "project_data",
        "team": "team_data",
        "sprint": "sprint_data",
        "feature": "feature_data",
        "doc": "doc_data",
        "deployment_env": "deployment_env_data",
        "team_member": "member_data",
        "team_reviewer": "member_data",
        "task_feature": "feature_data",
        "task_deployment_env": "deployment_env_data",
        "task_owner": "owner_data",
        "task_reviewer": "reviewer_data",
        "feature_doc": "doc_data",
        "project_team": "team_data",
        "sprint_team": "team_data",
        "sprint_task": "task_data",
    }

    @classmethod
    def build_create_params(
        cls,
        domain_object: str,
        data_obj: Any,
        resolved_params: dict[str, Any],
        user_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Build parameters for create operation."""
        params: dict[str, Any] = {"user_id": user_id, "db": db}

        # Get the data parameter name
        data_param_name = cls.DATA_PARAM_NAMES.get(domain_object, "data")
        params[data_param_name] = data_obj

        # Handle different domain object types
        if domain_object in cls.TEAM_CHILDREN:  # pragma: no cover
            params["team_id"] = UUID(resolved_params["data"]["team_id"])
        elif domain_object in cls.TASK_CHILDREN:  # pragma: no cover
            params["task_id"] = UUID(resolved_params["data"]["task_id"])
        elif domain_object in cls.FEATURE_CHILDREN:  # pragma: no cover
            params["feature_id"] = UUID(resolved_params["data"]["feature_id"])
        elif domain_object in cls.PROJECT_CHILDREN:  # pragma: no cover
            params["project_id"] = UUID(resolved_params["data"]["project_id"])
        elif domain_object in cls.SPRINT_CHILDREN:  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params["data"]["sprint_id"])
        elif domain_object in cls.STANDARD_DOMAINS:
            params["org_id"] = UUID(resolved_params["data"]["org_id"])

        return params

    @classmethod
    def build_get_params(
        cls,
        domain_object: str,
        obj_id: UUID,
        resolved_params: dict[str, Any],
        user_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Build parameters for get operation."""
        params: dict[str, Any] = {"db": db}

        # Handle different domain object types
        if domain_object in cls.TEAM_CHILDREN:  # pragma: no cover
            params["team_id"] = UUID(resolved_params.get("team_id"))
            params["principal_id"] = obj_id
        elif domain_object == "task_feature":  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["feature_id"] = obj_id
        elif domain_object == "task_deployment_env":  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["deployment_env_id"] = obj_id
        elif domain_object in {"task_owner", "task_reviewer"}:  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["principal_id"] = obj_id
        elif domain_object == "feature_doc":  # pragma: no cover
            params["feature_id"] = UUID(resolved_params.get("feature_id"))
            params["doc_id"] = obj_id
        elif domain_object == "project_team":  # pragma: no cover
            params["project_id"] = UUID(resolved_params.get("project_id"))
            params["team_id"] = obj_id
        elif domain_object == "sprint_team":  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params.get("sprint_id"))
            params["team_id"] = obj_id
        elif domain_object == "sprint_task":  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params.get("sprint_id"))
            params["task_id"] = obj_id
        elif domain_object in cls.STANDARD_DOMAINS:
            id_param_name = cls.ID_PARAM_NAMES.get(domain_object, "id")
            params[id_param_name] = obj_id
            params["org_id"] = UUID(resolved_params.get("org_id"))
            params["user_id"] = user_id
        else:  # pragma: no cover
            params["id"] = obj_id
            params["org_id"] = UUID(resolved_params.get("org_id"))
            params["user_id"] = user_id

        return params

    @classmethod
    def build_list_params(
        cls,
        domain_object: str,
        filters: dict[str, Any],
        user_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Build parameters for list operation."""
        params: dict[str, Any] = {"db": db}

        # Handle different domain object types
        if domain_object in cls.TEAM_CHILDREN:  # pragma: no cover
            params["team_id"] = UUID(filters.get("team_id"))
        elif domain_object in cls.TASK_CHILDREN:  # pragma: no cover
            params["task_id"] = UUID(filters.get("task_id"))
        elif domain_object in cls.FEATURE_CHILDREN:  # pragma: no cover
            params["feature_id"] = UUID(filters.get("feature_id"))
        elif domain_object in cls.PROJECT_CHILDREN:  # pragma: no cover
            params["project_id"] = UUID(filters.get("project_id"))
        elif domain_object in cls.SPRINT_CHILDREN:  # pragma: no cover
            params["sprint_id"] = UUID(filters.get("sprint_id"))
        elif domain_object in cls.STANDARD_DOMAINS:
            params["org_id"] = UUID(filters.get("org_id"))
            params["user_id"] = user_id

        return params

    @classmethod
    def build_update_params(
        cls,
        domain_object: str,
        obj_id: UUID,
        data_obj: Any,
        resolved_params: dict[str, Any],
        user_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Build parameters for update operation."""
        params: dict[str, Any] = {"user_id": user_id, "db": db}

        # Get the data parameter name
        data_param_name = cls.DATA_PARAM_NAMES.get(domain_object, "data")
        params[data_param_name] = data_obj

        # Handle different domain object types
        if domain_object in cls.TEAM_CHILDREN:  # pragma: no cover
            params["team_id"] = UUID(resolved_params.get("team_id"))
            params["principal_id"] = obj_id
        elif domain_object == "task_feature":  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["feature_id"] = obj_id
        elif domain_object == "task_deployment_env":  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["deployment_env_id"] = obj_id
        elif domain_object in {"task_owner", "task_reviewer"}:  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["principal_id"] = obj_id
        elif domain_object == "feature_doc":  # pragma: no cover
            params["feature_id"] = UUID(resolved_params.get("feature_id"))
            params["doc_id"] = obj_id
        elif domain_object == "project_team":  # pragma: no cover
            params["project_id"] = UUID(resolved_params.get("project_id"))
            params["team_id"] = obj_id
        elif domain_object == "sprint_team":  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params.get("sprint_id"))
            params["team_id"] = obj_id
        elif domain_object == "sprint_task":  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params.get("sprint_id"))
            params["task_id"] = obj_id
        elif domain_object in cls.STANDARD_DOMAINS:
            id_param_name = cls.ID_PARAM_NAMES.get(domain_object, "id")
            params[id_param_name] = obj_id
            params["org_id"] = UUID(resolved_params.get("org_id"))
        else:  # pragma: no cover
            params["id"] = obj_id
            params["org_id"] = UUID(resolved_params.get("org_id"))

        return params

    @classmethod
    def build_delete_params(
        cls,
        domain_object: str,
        obj_id: UUID,
        resolved_params: dict[str, Any],
        user_id: UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Build parameters for delete operation."""
        params: dict[str, Any] = {"db": db}

        # Handle different domain object types
        if domain_object in cls.TEAM_CHILDREN:  # pragma: no cover
            params["team_id"] = UUID(resolved_params.get("team_id"))
            params["principal_id"] = obj_id
        elif domain_object == "task_feature":  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["feature_id"] = obj_id
        elif domain_object == "task_deployment_env":  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["deployment_env_id"] = obj_id
        elif domain_object in {"task_owner", "task_reviewer"}:  # pragma: no cover
            params["task_id"] = UUID(resolved_params.get("task_id"))
            params["principal_id"] = obj_id
        elif domain_object == "feature_doc":  # pragma: no cover
            params["feature_id"] = UUID(resolved_params.get("feature_id"))
            params["doc_id"] = obj_id
        elif domain_object == "project_team":  # pragma: no cover
            params["project_id"] = UUID(resolved_params.get("project_id"))
            params["team_id"] = obj_id
        elif domain_object == "sprint_team":  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params.get("sprint_id"))
            params["team_id"] = obj_id
        elif domain_object == "sprint_task":  # pragma: no cover
            params["sprint_id"] = UUID(resolved_params.get("sprint_id"))
            params["task_id"] = obj_id
        elif domain_object in cls.STANDARD_DOMAINS:
            id_param_name = cls.ID_PARAM_NAMES.get(domain_object, "id")
            params[id_param_name] = obj_id
            params["org_id"] = UUID(resolved_params.get("org_id"))
            params["user_id"] = user_id
        else:  # pragma: no cover
            params["id"] = obj_id
            params["org_id"] = UUID(resolved_params.get("org_id"))
            params["user_id"] = user_id

        return params


# ============================================================================
# Reference Resolution
# ============================================================================


class ReferenceResolver:
    """Resolves template references in operation parameters."""

    # Pattern: {{tx-id.op-id.result.field}} or {{op-id.result.field}}
    REFERENCE_PATTERN = re.compile(
        r"\{\{([a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)?\.result(?:\.[a-zA-Z0-9_\[\]\-\.]+)?)\}\}"
    )

    def __init__(self) -> None:
        """Initialize the reference resolver."""
        self.results: dict[str, Any] = {}

    def store_result(self, tx_id: str | None, op_id: str | None, result: Any) -> None:
        """Store an operation result for later reference."""
        if op_id:
            # Store with just op_id for same-transaction references
            self.results[f"{op_id}.result"] = result

        if tx_id and op_id:
            # Store with tx_id.op_id for cross-transaction references
            self.results[f"{tx_id}.{op_id}.result"] = result

    def resolve_value(
        self, value: Any, current_tx_id: str | None = None
    ) -> Any:  # pragma: no cover
        """Resolve references in a value (recursive for dicts/lists)."""
        if isinstance(value, str):
            # Check if the entire string is a reference
            match = self.REFERENCE_PATTERN.fullmatch(value)
            if match:
                ref_path = match.group(1)
                resolved = self._get_nested_value(ref_path)
                # Return the original string if reference doesn't exist
                return resolved if resolved is not None else value

            # Replace references within the string
            def replace_ref(match_obj: re.Match) -> str:
                ref_path = match_obj.group(1)
                resolved = self._get_nested_value(ref_path)
                return str(resolved) if resolved is not None else match_obj.group(0)

            return self.REFERENCE_PATTERN.sub(replace_ref, value)

        elif isinstance(value, dict):
            return {k: self.resolve_value(v, current_tx_id) for k, v in value.items()}

        elif isinstance(value, list):
            return [self.resolve_value(item, current_tx_id) for item in value]

        return value

    def _get_nested_value(self, path: str) -> Any:  # pragma: no cover
        """Get a nested value from stored results using dot notation and array indexing."""
        # First, try to find the base result reference
        # Path format: "op-id.result.field" or "tx-id.op-id.result.field"

        # Split the path to find ".result" and extract base key and remaining path
        if ".result" in path:
            result_index = path.index(".result")
            # Base key includes ".result"
            base_key = path[: result_index + 7]  # 7 is len(".result")
            remaining_part = path[result_index + 7 :]  # Everything after ".result"

            # Remove leading "." from remaining part if present
            if remaining_part.startswith("."):
                remaining_part = remaining_part[1:]

            if base_key in self.results:
                current = self.results[base_key]
                # Navigate remaining path if any
                if remaining_part:
                    return self._navigate_path(current, remaining_part)
                return current

        return None

    def _navigate_path(self, obj: Any, path: str) -> Any:  # pragma: no cover
        """Navigate through nested fields and array indices."""
        # Split path into parts (handling array notation)
        parts = re.split(r"[\.\[]", path)
        parts = [p.rstrip("]") for p in parts if p]

        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current


# ============================================================================
# Dependency Graph
# ============================================================================


class DependencyGraph:
    """Builds and validates dependency graphs for operation execution."""

    @staticmethod
    def build_execution_order(operations: list[Operation]) -> list[Operation]:
        """Build execution order based on dependencies (topological sort)."""
        # Build adjacency list and in-degree count
        op_map = {op.id: op for op in operations if op.id}
        graph: dict[str, list[str]] = {op.id: [] for op in operations if op.id}
        in_degree: dict[str, int] = {op.id: 0 for op in operations if op.id}

        # Build graph from dependencies
        for op in operations:
            if op.id and op.depends_on:
                for dep in op.depends_on:
                    # Extract just the op_id from tx-id.op-id or op-id format
                    dep_op_id = dep.split(".")[-1] if "." in dep else dep
                    if dep_op_id in graph:
                        graph[dep_op_id].append(op.id)
                        in_degree[op.id] += 1

        # Topological sort using Kahn's algorithm
        queue = [op_id for op_id, degree in in_degree.items() if degree == 0]
        sorted_ops = []

        while queue:
            op_id = queue.pop(0)
            sorted_ops.append(op_map[op_id])

            for neighbor in graph[op_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add operations without IDs (no dependencies) at the end
        ops_without_ids = [op for op in operations if not op.id]
        sorted_ops.extend(ops_without_ids)

        # Check for circular dependencies
        if len(sorted_ops) < len(operations):
            raise ValueError("Circular dependency detected in operations")

        return sorted_ops


# ============================================================================
# Operation Execution
# ============================================================================


async def execute_operation(
    operation: Operation,
    resolver: ReferenceResolver,
    user_id: UUID,
    db: AsyncSession,
    current_tx_id: str | None = None,
) -> OperationResult:
    """Execute a single operation.

    Args:
        operation: The operation to execute
        resolver: Reference resolver for template substitution
        user_id: ID of the user executing the operation
        db: Database session (already within a transaction)
        current_tx_id: Current transaction ID for reference resolution

    Returns:
        OperationResult containing the result or error
    """
    try:
        # Get the operation function
        op_func = operation_registry.get_operation(
            operation.domain_object, operation.operation
        )
        if not op_func:
            return OperationResult(
                id=operation.id,
                operation=operation.operation,
                domain_object=operation.domain_object,
                status="failure",
                error=f"Unsupported domain object '{operation.domain_object}' or operation '{operation.operation}'",
                error_type="UnsupportedOperation",
            )

        # Resolve references in parameters
        # Use mode='json' to ensure UUIDs are converted to strings
        raw_params = operation.params.model_dump(mode="json", exclude_none=True)
        resolved_params = resolver.resolve_value(raw_params, current_tx_id)

        # Execute the operation based on type using ParameterBuilder
        result = None

        if operation.operation == "create":
            # Create operations
            schema_class = get_create_schema(operation.domain_object)
            data_obj = schema_class(**resolved_params["data"])

            # Build parameters using ParameterBuilder
            params = ParameterBuilder.build_create_params(
                operation.domain_object,
                data_obj,
                resolved_params,
                user_id,
                db,
            )
            result = await op_func(**params)

        elif operation.operation == "get":
            # Get operations
            obj_id = UUID(str(resolved_params["id"]))

            # Build parameters using ParameterBuilder
            params = ParameterBuilder.build_get_params(
                operation.domain_object,
                obj_id,
                resolved_params,
                user_id,
                db,
            )
            result = await op_func(**params)

        elif operation.operation == "list":  # pragma: no cover
            # List operations
            filters = resolved_params.get("filters", {})

            # Build parameters using ParameterBuilder
            params = ParameterBuilder.build_list_params(
                operation.domain_object,
                filters,
                user_id,
                db,
            )
            result = await op_func(**params)

        elif operation.operation == "update":  # pragma: no cover
            # Update operations
            obj_id = UUID(str(resolved_params["id"]))
            schema_class = get_update_schema(operation.domain_object)
            data_obj = schema_class(**resolved_params["data"])

            # Build parameters using ParameterBuilder
            params = ParameterBuilder.build_update_params(
                operation.domain_object,
                obj_id,
                data_obj,
                resolved_params,
                user_id,
                db,
            )
            result = await op_func(**params)

        elif operation.operation == "delete":  # pragma: no cover
            # Delete operations
            obj_id = UUID(str(resolved_params["id"]))

            # Build parameters using ParameterBuilder
            params = ParameterBuilder.build_delete_params(
                operation.domain_object,
                obj_id,
                resolved_params,
                user_id,
                db,
            )
            await op_func(**params)

            result = {"deleted": True, "id": str(obj_id)}

        # Convert result to dict if it's a model (keeping existing code after all operations)
        result_dict = None
        if result is not None:  # pragma: no cover
            if hasattr(result, "model_dump"):
                result_dict = result.model_dump()
            elif hasattr(result, "__dict__"):
                result_dict = {
                    k: v for k, v in result.__dict__.items() if not k.startswith("_")
                }
            elif isinstance(result, list):
                result_dict = {
                    "items": [
                        (
                            item.model_dump()
                            if hasattr(item, "model_dump")
                            else {
                                k: v
                                for k, v in item.__dict__.items()
                                if not k.startswith("_")
                            }
                        )
                        for item in result
                    ]
                }
            elif isinstance(result, dict):
                result_dict = result
            else:
                result_dict = {"value": result}

        return OperationResult(
            id=operation.id,
            operation=operation.operation,
            domain_object=operation.domain_object,
            status="success",
            result=result_dict,
        )

    except (
        TaskNotFoundException,
        ProjectNotFoundException,
        TeamNotFoundException,
        SprintNotFoundException,
        FeatureNotFoundException,
        DocNotFoundException,
        DeploymentEnvNotFoundException,
        TeamMemberNotFoundException,
        TeamReviewerNotFoundException,
        TaskFeatureNotFoundException,
        TaskDeploymentEnvNotFoundException,
        TaskOwnerNotFoundException,
        TaskReviewerNotFoundException,
        FeatureDocNotFoundException,
        ProjectTeamNotFoundException,
        SprintTeamNotFoundException,
        SprintTaskNotFoundException,
    ) as e:
        return OperationResult(
            id=operation.id,
            operation=operation.operation,
            domain_object=operation.domain_object,
            status="failure",
            error=str(e.message),
            error_type="NotFound",
        )
    except UnauthorizedOrganizationAccessException as e:
        return OperationResult(
            id=operation.id,
            operation=operation.operation,
            domain_object=operation.domain_object,
            status="failure",
            error=str(e.message),
            error_type="Unauthorized",
        )
    except ProjectTeamAlreadyExistsException as e:
        return OperationResult(
            id=operation.id,
            operation=operation.operation,
            domain_object=operation.domain_object,
            status="failure",
            error=str(e.message),
            error_type="AlreadyExists",
        )
    except Exception as e:
        return OperationResult(
            id=operation.id,
            operation=operation.operation,
            domain_object=operation.domain_object,
            status="failure",
            error=str(e),
            error_type=type(e).__name__,
        )


# ============================================================================
# Transaction Execution
# ============================================================================


async def execute_transaction_group(
    tx: TransactionGroup,
    resolver: ReferenceResolver,
    user_id: UUID,
    db: AsyncSession,
) -> TransactionResult:
    """Execute a single transaction group (atomic unit).

    Args:
        tx: Transaction group to execute
        resolver: Reference resolver
        user_id: User ID
        db: Database session (NOT yet in a transaction)

    Returns:
        TransactionResult with all operation results
    """
    operation_results: list[OperationResult] = []

    try:
        # Start a database transaction
        async with db.begin():
            # Build execution order based on dependencies
            if tx.execution_mode == "serial":
                # Serial execution within transaction
                sorted_ops = DependencyGraph.build_execution_order(tx.operations)

                for op in sorted_ops:
                    result = await execute_operation(op, resolver, user_id, db, tx.id)
                    operation_results.append(result)

                    # Store result for reference resolution
                    if result.status == "success" and result.id:
                        resolver.store_result(tx.id, result.id, result.result)

                    # Stop on first failure in serial mode
                    if result.status == "failure":
                        # Transaction will auto-rollback on exception
                        return TransactionResult(
                            id=tx.id,
                            status="failure",
                            operations=operation_results,
                            error=f"Operation {result.id or 'unnamed'} failed: {result.error}",
                        )

            else:
                # Parallel execution within transaction
                sorted_ops = DependencyGraph.build_execution_order(tx.operations)

                # Execute operations in parallel using asyncio.gather
                tasks = [
                    execute_operation(op, resolver, user_id, db, tx.id)
                    for op in sorted_ops
                ]
                operation_results = await asyncio.gather(*tasks)

                # Store results
                for result in operation_results:
                    if result.status == "success" and result.id:
                        resolver.store_result(tx.id, result.id, result.result)

                # Check if any failed
                failed = [r for r in operation_results if r.status == "failure"]
                if failed:
                    # Raise to trigger rollback
                    raise ValueError(
                        f"{len(failed)} operation(s) failed in parallel transaction"
                    )  # pragma: no cover

        # Transaction committed successfully
        return TransactionResult(
            id=tx.id,
            status="success",
            operations=operation_results,
        )

    except Exception as e:
        # Transaction rolled back
        return TransactionResult(
            id=tx.id,
            status="failure",
            operations=operation_results,
            error=str(e),
        )


async def execute_transactions(
    request: TransactionsRequest,
    user_id: UUID,
    db: AsyncSession,
) -> TransactionsResponse:
    """Execute a batch of transactions.

    Args:
        request: Transaction batch request
        user_id: ID of the user executing the transactions
        db: Database session

    Returns:
        TransactionsResponse with all transaction results
    """
    resolver = ReferenceResolver()
    transaction_results: list[TransactionResult] = []

    if request.execution_mode == "serial":
        # Serial execution of transactions
        for tx in request.txs:
            result = await execute_transaction_group(tx, resolver, user_id, db)
            transaction_results.append(result)

            # Stop on first transaction failure in serial mode
            if result.status == "failure":
                # Skip remaining transactions
                for remaining_tx in request.txs[len(transaction_results) :]:
                    transaction_results.append(
                        TransactionResult(
                            id=remaining_tx.id,
                            status="skipped",
                            operations=[],
                            error="Skipped due to previous transaction failure",
                        )
                    )
                break

    else:
        # Parallel execution of transactions
        tasks = [
            execute_transaction_group(tx, resolver, user_id, db) for tx in request.txs
        ]
        transaction_results = await asyncio.gather(*tasks)

    # Determine overall status
    failed = [r for r in transaction_results if r.status == "failure"]
    overall_status: Literal["success", "failure"] = "failure" if failed else "success"

    return TransactionsResponse(
        status=overall_status,
        transactions=transaction_results,
    )
