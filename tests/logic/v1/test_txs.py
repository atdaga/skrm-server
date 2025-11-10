"""Unit tests for transaction batch API logic."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid7

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.logic.v1.txs import (
    DependencyGraph,
    OperationRegistry,
    ParameterBuilder,
    ReferenceResolver,
    execute_operation,
    execute_transaction_group,
    execute_transactions,
    operation_registry,
)
from app.schemas.txs import (
    CreateParams,
    GetParams,
    ListParams,
    Operation,
    OperationResult,
    TransactionGroup,
    TransactionResult,
    TransactionsRequest,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_user_id() -> UUID:
    """Generate a sample user ID for testing."""
    return uuid7()


@pytest.fixture
def sample_org_id() -> UUID:
    """Generate a sample org ID for testing."""
    return uuid7()


@pytest.fixture
def sample_task_id() -> UUID:
    """Generate a sample task ID for testing."""
    return uuid7()


@pytest.fixture
def sample_team_id() -> UUID:
    """Generate a sample team ID for testing."""
    return uuid7()


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def reference_resolver():
    """Create a fresh ReferenceResolver instance."""
    return ReferenceResolver()


# ============================================================================
# ParameterBuilder Tests
# ============================================================================


class TestParameterBuilder:
    """Test suite for ParameterBuilder class."""

    def test_build_create_params_standard_domain(
        self, sample_user_id, sample_org_id, mock_db
    ):
        """Test building create parameters for standard domain objects."""
        data_obj = MagicMock()
        resolved_params = {"data": {"org_id": str(sample_org_id), "name": "Test Task"}}

        params = ParameterBuilder.build_create_params(
            domain_object="task",
            data_obj=data_obj,
            resolved_params=resolved_params,
            user_id=sample_user_id,
            db=mock_db,
        )

        assert params["task_data"] == data_obj
        assert params["user_id"] == sample_user_id
        assert params["org_id"] == sample_org_id
        assert params["db"] == mock_db

    def test_build_create_params_team_child(
        self, sample_user_id, sample_team_id, mock_db
    ):
        """Test building create parameters for team child objects."""
        data_obj = MagicMock()
        resolved_params = {
            "data": {"team_id": str(sample_team_id), "principal_id": str(uuid7())}
        }

        params = ParameterBuilder.build_create_params(
            domain_object="team_member",
            data_obj=data_obj,
            resolved_params=resolved_params,
            user_id=sample_user_id,
            db=mock_db,
        )

        assert params["member_data"] == data_obj
        assert params["team_id"] == sample_team_id
        assert params["user_id"] == sample_user_id
        assert params["db"] == mock_db

    def test_build_get_params_standard_domain(
        self, sample_user_id, sample_org_id, sample_task_id, mock_db
    ):
        """Test building get parameters for standard domain objects."""
        resolved_params = {"id": str(sample_task_id), "org_id": str(sample_org_id)}

        params = ParameterBuilder.build_get_params(
            domain_object="task",
            obj_id=sample_task_id,
            resolved_params=resolved_params,
            user_id=sample_user_id,
            db=mock_db,
        )

        assert params["task_id"] == sample_task_id
        assert params["org_id"] == sample_org_id
        assert params["user_id"] == sample_user_id
        assert params["db"] == mock_db

    def test_build_list_params_standard_domain(
        self, sample_user_id, sample_org_id, mock_db
    ):
        """Test building list parameters for standard domain objects."""
        filters = {"org_id": str(sample_org_id), "status": "active"}

        params = ParameterBuilder.build_list_params(
            domain_object="task",
            filters=filters,
            user_id=sample_user_id,
            db=mock_db,
        )

        assert params["org_id"] == sample_org_id
        assert params["user_id"] == sample_user_id
        assert params["db"] == mock_db

    def test_build_update_params_standard_domain(
        self, sample_user_id, sample_org_id, sample_task_id, mock_db
    ):
        """Test building update parameters for standard domain objects."""
        data_obj = MagicMock()
        resolved_params = {
            "id": str(sample_task_id),
            "org_id": str(sample_org_id),
            "data": {"summary": "Updated"},
        }

        params = ParameterBuilder.build_update_params(
            domain_object="task",
            obj_id=sample_task_id,
            data_obj=data_obj,
            resolved_params=resolved_params,
            user_id=sample_user_id,
            db=mock_db,
        )

        assert params["task_id"] == sample_task_id
        assert params["task_data"] == data_obj
        assert params["org_id"] == sample_org_id
        assert params["user_id"] == sample_user_id
        assert params["db"] == mock_db

    def test_build_delete_params_standard_domain(
        self, sample_user_id, sample_org_id, sample_task_id, mock_db
    ):
        """Test building delete parameters for standard domain objects."""
        resolved_params = {"id": str(sample_task_id), "org_id": str(sample_org_id)}

        params = ParameterBuilder.build_delete_params(
            domain_object="task",
            obj_id=sample_task_id,
            resolved_params=resolved_params,
            user_id=sample_user_id,
            db=mock_db,
        )

        assert params["task_id"] == sample_task_id
        assert params["org_id"] == sample_org_id
        assert params["user_id"] == sample_user_id
        assert params["db"] == mock_db


# ============================================================================
# ReferenceResolver Tests
# ============================================================================


class TestReferenceResolver:
    """Test suite for ReferenceResolver class."""

    def test_store_and_resolve_simple_reference(self, reference_resolver):
        """Test storing and resolving a simple reference."""
        test_result = {"id": str(uuid7()), "name": "Test Task"}

        reference_resolver.store_result("tx-001", "op-001", test_result)

        # Test same-transaction reference
        resolved = reference_resolver.resolve_value("{{op-001.result.id}}")
        assert resolved == test_result["id"]

        # Test cross-transaction reference
        resolved = reference_resolver.resolve_value("{{tx-001.op-001.result.id}}")
        assert resolved == test_result["id"]

    def test_resolve_nested_field_reference(self, reference_resolver):
        """Test resolving nested field references."""
        test_result = {"data": {"nested": {"field": "value"}}}

        reference_resolver.store_result("tx-001", "op-001", test_result)

        resolved = reference_resolver.resolve_value(
            "{{tx-001.op-001.result.data.nested.field}}"
        )
        assert resolved == "value"

    def test_resolve_array_index_reference(self, reference_resolver):
        """Test resolving array index references."""
        test_result = {"items": [{"id": "first"}, {"id": "second"}]}

        reference_resolver.store_result("tx-001", "op-001", test_result)

        resolved = reference_resolver.resolve_value(
            "{{tx-001.op-001.result.items[0].id}}"
        )
        assert resolved == "first"

    def test_resolve_references_in_dict(self, reference_resolver):
        """Test resolving references within a dictionary."""
        test_result = {"id": "test-id-123", "status": "active"}

        reference_resolver.store_result("tx-001", "op-001", test_result)

        input_dict = {
            "task_id": "{{tx-001.op-001.result.id}}",
            "status": "{{tx-001.op-001.result.status}}",
            "literal": "no-reference",
        }

        resolved = reference_resolver.resolve_value(input_dict)
        assert resolved["task_id"] == "test-id-123"
        assert resolved["status"] == "active"
        assert resolved["literal"] == "no-reference"

    def test_resolve_references_in_list(self, reference_resolver):
        """Test resolving references within a list."""
        test_result = {"id": "test-id-456"}

        reference_resolver.store_result("tx-001", "op-001", test_result)

        input_list = ["{{tx-001.op-001.result.id}}", "literal-value"]

        resolved = reference_resolver.resolve_value(input_list)
        assert resolved[0] == "test-id-456"
        assert resolved[1] == "literal-value"

    def test_resolve_nonexistent_reference(self, reference_resolver):
        """Test resolving a nonexistent reference returns None."""
        resolved = reference_resolver.resolve_value("{{nonexistent.op.result.id}}")
        assert resolved == "{{nonexistent.op.result.id}}"  # Should remain unchanged


# ============================================================================
# DependencyGraph Tests
# ============================================================================


class TestDependencyGraph:
    """Test suite for DependencyGraph class."""

    def test_build_execution_order_no_dependencies(self):
        """Test building execution order with no dependencies."""
        ops = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(data={}),
            ),
            Operation(
                id="op-002",
                operation="create",
                domain_object="project",
                params=CreateParams(data={}),
            ),
            Operation(
                id="op-003", operation="list", domain_object="task", params=ListParams()
            ),
        ]

        sorted_ops = DependencyGraph.build_execution_order(ops)

        assert len(sorted_ops) == 3
        assert all(op in sorted_ops for op in ops)

    def test_build_execution_order_with_dependencies(self):
        """Test building execution order with dependencies."""
        ops = [
            Operation(
                id="op-003",
                operation="create",
                domain_object="task",
                params=CreateParams(data={}),
                depends_on=["op-001", "op-002"],
            ),
            Operation(
                id="op-001",
                operation="create",
                domain_object="project",
                params=CreateParams(data={}),
            ),
            Operation(
                id="op-002",
                operation="create",
                domain_object="team",
                params=CreateParams(data={}),
            ),
        ]

        sorted_ops = DependencyGraph.build_execution_order(ops)

        assert len(sorted_ops) == 3
        # op-003 should come after op-001 and op-002
        assert sorted_ops.index(ops[1]) < sorted_ops.index(
            ops[0]
        )  # op-001 before op-003
        assert sorted_ops.index(ops[2]) < sorted_ops.index(
            ops[0]
        )  # op-002 before op-003

    def test_build_execution_order_circular_dependency_raises_error(self):
        """Test that circular dependencies raise an error."""
        ops = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(data={}),
                depends_on=["op-002"],
            ),
            Operation(
                id="op-002",
                operation="create",
                domain_object="project",
                params=CreateParams(data={}),
                depends_on=["op-001"],
            ),
        ]

        with pytest.raises(ValueError, match="Circular dependency"):
            DependencyGraph.build_execution_order(ops)

    def test_build_execution_order_mixed_with_and_without_ids(self):
        """Test building execution order with mixed operations (some with IDs, some without)."""
        ops = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(data={}),
            ),
            Operation(
                operation="list", domain_object="task", params=ListParams()
            ),  # No ID
            Operation(
                id="op-002",
                operation="get",
                domain_object="task",
                params=GetParams(id="some-id"),
            ),
        ]

        sorted_ops = DependencyGraph.build_execution_order(ops)

        assert len(sorted_ops) == 3


# ============================================================================
# OperationRegistry Tests
# ============================================================================


class TestOperationRegistry:
    """Test suite for OperationRegistry class."""

    def test_registry_has_all_domain_objects(self):
        """Test that registry contains all expected domain objects."""
        registry = OperationRegistry()

        expected_domains = [
            "task",
            "project",
            "team",
            "sprint",
            "feature",
            "doc",
            "deployment_env",
            "team_member",
            "team_reviewer",
            "task_feature",
            "task_deployment_env",
            "task_owner",
            "task_reviewer",
            "feature_doc",
            "project_team",
            "sprint_team",
            "sprint_task",
        ]

        for domain in expected_domains:
            assert registry.supports_domain_object(
                domain
            ), f"Missing domain object: {domain}"

    def test_registry_has_all_operations_for_domain(self):
        """Test that each domain has all CRUD operations."""
        registry = OperationRegistry()

        operations = ["create", "get", "list", "update", "delete"]

        # Test a few key domains
        for domain in ["task", "project", "team"]:
            for operation in operations:
                assert registry.supports_operation(
                    domain, operation
                ), f"Missing operation '{operation}' for domain '{domain}'"

    def test_get_operation_returns_callable(self):
        """Test that get_operation returns a callable function."""
        registry = OperationRegistry()

        op_func = registry.get_operation("task", "create")

        assert op_func is not None
        assert callable(op_func)

    def test_get_operation_unsupported_returns_none(self):
        """Test that get_operation returns None for unsupported operations."""
        registry = OperationRegistry()

        op_func = registry.get_operation("nonexistent_domain", "create")

        assert op_func is None


# ============================================================================
# execute_operation Tests
# ============================================================================


class TestExecuteOperation:
    """Test suite for execute_operation function."""

    @pytest.mark.asyncio
    async def test_execute_operation_unsupported_domain(self, sample_user_id, mock_db):
        """Test executing an operation with unsupported domain object."""
        resolver = ReferenceResolver()
        operation = Operation(
            id="op-001",
            operation="create",
            domain_object="unsupported_domain",
            params=CreateParams(data={}),
        )

        result = await execute_operation(operation, resolver, sample_user_id, mock_db)

        assert result.status == "failure"
        assert result.error_type == "UnsupportedOperation"
        assert "unsupported_domain" in result.error

    @pytest.mark.asyncio
    async def test_execute_operation_with_reference_resolution(
        self, sample_user_id, mock_db, sample_org_id
    ):
        """Test executing an operation with reference resolution."""
        resolver = ReferenceResolver()
        test_id = str(uuid7())
        resolver.store_result("tx-001", "op-001", {"id": test_id})

        operation = Operation(
            id="op-002",
            operation="get",
            domain_object="task",
            params=GetParams(id="{{tx-001.op-001.result.id}}", org_id=sample_org_id),
        )

        # Mock the operation function
        mock_task = MagicMock()
        mock_task.model_dump.return_value = {"id": test_id, "summary": "Test"}

        with patch.object(
            operation_registry,
            "get_operation",
            return_value=AsyncMock(return_value=mock_task),
        ) as mock_get_op:
            result = await execute_operation(
                operation, resolver, sample_user_id, mock_db
            )

            # Check if operation was successful
            assert result.status == "success", f"Operation failed: {result.error}"

            # Verify the get_operation was called
            mock_get_op.assert_called_once_with("task", "get")

            # Verify the result contains the expected data
            assert result.result["id"] == test_id

    @pytest.mark.asyncio
    async def test_execute_operation_not_found_exception(
        self, sample_user_id, mock_db, sample_org_id
    ):
        """Test execute_operation handles NotFound exceptions."""
        from app.core.exceptions.domain_exceptions import TaskNotFoundException

        resolver = ReferenceResolver()
        operation = Operation(
            id="op-001",
            operation="get",
            domain_object="task",
            params=GetParams(id=str(uuid7()), org_id=sample_org_id),
        )

        with patch.object(operation_registry, "get_operation") as mock_get_op:
            mock_get_op.return_value = AsyncMock(
                side_effect=TaskNotFoundException(task_id=uuid7())
            )

            result = await execute_operation(
                operation, resolver, sample_user_id, mock_db
            )

            assert result.status == "failure"
            assert result.error_type == "NotFound"
            assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_operation_unauthorized_exception(
        self, sample_user_id, mock_db, sample_org_id
    ):
        """Test execute_operation handles Unauthorized exceptions."""
        from app.core.exceptions.domain_exceptions import (
            UnauthorizedOrganizationAccessException,
        )

        resolver = ReferenceResolver()
        operation = Operation(
            id="op-001",
            operation="get",
            domain_object="task",
            params=GetParams(id=str(uuid7()), org_id=sample_org_id),
        )

        with patch.object(operation_registry, "get_operation") as mock_get_op:
            mock_get_op.return_value = AsyncMock(
                side_effect=UnauthorizedOrganizationAccessException(
                    org_id=sample_org_id, user_id=sample_user_id
                )
            )

            result = await execute_operation(
                operation, resolver, sample_user_id, mock_db
            )

            assert result.status == "failure"
            assert result.error_type == "Unauthorized"

    @pytest.mark.asyncio
    async def test_execute_operation_already_exists_exception(
        self, sample_user_id, mock_db
    ):
        """Test execute_operation handles AlreadyExists exceptions."""
        from app.core.exceptions.domain_exceptions import (
            ProjectTeamAlreadyExistsException,
        )

        resolver = ReferenceResolver()
        operation = Operation(
            id="op-001",
            operation="create",
            domain_object="project_team",
            params=CreateParams(
                data={"project_id": str(uuid7()), "team_id": str(uuid7())}
            ),
        )

        with patch.object(operation_registry, "get_operation") as mock_get_op:
            mock_get_op.return_value = AsyncMock(
                side_effect=ProjectTeamAlreadyExistsException(
                    project_id=uuid7(), team_id=uuid7(), scope="project"
                )
            )

            result = await execute_operation(
                operation, resolver, sample_user_id, mock_db
            )

            assert result.status == "failure"
            assert result.error_type == "AlreadyExists"

    @pytest.mark.asyncio
    async def test_execute_operation_generic_exception(
        self, sample_user_id, mock_db, sample_org_id
    ):
        """Test execute_operation handles generic exceptions."""
        resolver = ReferenceResolver()
        operation = Operation(
            id="op-001",
            operation="get",
            domain_object="task",
            params=GetParams(id=str(uuid7()), org_id=sample_org_id),
        )

        with patch.object(operation_registry, "get_operation") as mock_get_op:
            mock_get_op.return_value = AsyncMock(
                side_effect=ValueError("Invalid input")
            )

            result = await execute_operation(
                operation, resolver, sample_user_id, mock_db
            )

            assert result.status == "failure"
            assert result.error_type == "ValueError"
            assert "Invalid input" in result.error


# ============================================================================
# execute_transaction_group Tests
# ============================================================================


class TestExecuteTransactionGroup:
    """Test suite for execute_transaction_group function."""

    @pytest.mark.asyncio
    async def test_execute_transaction_group_serial_success(
        self, sample_user_id, mock_db
    ):
        """Test executing a transaction group in serial mode with success."""
        resolver = ReferenceResolver()

        # Mock operations
        operations = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(
                    data={"org_id": str(uuid7()), "team_id": str(uuid7())}
                ),
            ),
            Operation(
                id="op-002", operation="list", domain_object="task", params=ListParams()
            ),
        ]

        tx = TransactionGroup(
            id="tx-001", execution_mode="serial", operations=operations
        )

        # Mock the database begin context
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()

        with patch("app.logic.v1.txs.execute_operation") as mock_exec_op:
            # Mock successful operation results
            mock_exec_op.side_effect = [
                OperationResult(
                    id="op-001",
                    operation="create",
                    domain_object="task",
                    status="success",
                    result={"id": str(uuid7())},
                ),
                OperationResult(
                    id="op-002",
                    operation="list",
                    domain_object="task",
                    status="success",
                    result={"items": []},
                ),
            ]

            result = await execute_transaction_group(
                tx, resolver, sample_user_id, mock_db
            )

            assert result.status == "success"
            assert len(result.operations) == 2
            assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_transaction_group_serial_failure(
        self, sample_user_id, mock_db
    ):
        """Test executing a transaction group in serial mode with failure."""
        resolver = ReferenceResolver()

        operations = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(data={}),
            ),
            Operation(
                id="op-002", operation="list", domain_object="task", params=ListParams()
            ),
        ]

        tx = TransactionGroup(
            id="tx-001", execution_mode="serial", operations=operations
        )

        # Mock the database begin context
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()

        with patch("app.logic.v1.txs.execute_operation") as mock_exec_op:
            # First operation fails
            mock_exec_op.side_effect = [
                OperationResult(
                    id="op-001",
                    operation="create",
                    domain_object="task",
                    status="failure",
                    error="Task creation failed",
                    error_type="ValidationError",
                ),
            ]

            result = await execute_transaction_group(
                tx, resolver, sample_user_id, mock_db
            )

            assert result.status == "failure"
            assert len(result.operations) == 1  # Only first operation executed
            assert "failed" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_transaction_group_parallel_success(
        self, sample_user_id, mock_db
    ):
        """Test executing a transaction group in parallel mode."""
        resolver = ReferenceResolver()

        operations = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(
                    data={"org_id": str(uuid7()), "team_id": str(uuid7())}
                ),
            ),
            Operation(
                id="op-002", operation="list", domain_object="task", params=ListParams()
            ),
        ]

        tx = TransactionGroup(
            id="tx-001", execution_mode="parallel", operations=operations
        )

        # Mock the database begin context
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()

        with patch("app.logic.v1.txs.execute_operation") as mock_exec_op:
            # Mock successful operation results
            mock_exec_op.side_effect = [
                OperationResult(
                    id="op-001",
                    operation="create",
                    domain_object="task",
                    status="success",
                    result={"id": str(uuid7())},
                ),
                OperationResult(
                    id="op-002",
                    operation="list",
                    domain_object="task",
                    status="success",
                    result={"items": []},
                ),
            ]

            result = await execute_transaction_group(
                tx, resolver, sample_user_id, mock_db
            )

            assert result.status == "success"
            assert len(result.operations) == 2
            assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_transaction_group_exception_handling(
        self, sample_user_id, mock_db
    ):
        """Test transaction group handles exceptions properly."""
        resolver = ReferenceResolver()

        operations = [
            Operation(
                id="op-001",
                operation="create",
                domain_object="task",
                params=CreateParams(data={}),
            ),
        ]

        tx = TransactionGroup(
            id="tx-001", execution_mode="serial", operations=operations
        )

        # Mock the database begin context to raise an exception
        mock_db.begin.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("Database error")
        )
        mock_db.begin.return_value.__aexit__ = AsyncMock()

        result = await execute_transaction_group(tx, resolver, sample_user_id, mock_db)

        assert result.status == "failure"
        assert "Database error" in result.error


# ============================================================================
# execute_transactions Tests
# ============================================================================


class TestExecuteTransactions:
    """Test suite for execute_transactions function."""

    @pytest.mark.asyncio
    async def test_execute_transactions_serial_all_success(
        self, sample_user_id, mock_db
    ):
        """Test executing transactions in serial mode with all successes."""
        tx1 = TransactionGroup(
            id="tx-001",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-001",
                    operation="create",
                    domain_object="task",
                    params=CreateParams(
                        data={"org_id": str(uuid7()), "team_id": str(uuid7())}
                    ),
                )
            ],
        )
        tx2 = TransactionGroup(
            id="tx-002",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-002",
                    operation="list",
                    domain_object="task",
                    params=ListParams(),
                )
            ],
        )

        request = TransactionsRequest(execution_mode="serial", txs=[tx1, tx2])

        with patch("app.logic.v1.txs.execute_transaction_group") as mock_exec_tx:
            # Mock successful transaction results
            mock_exec_tx.side_effect = [
                TransactionResult(
                    id="tx-001",
                    status="success",
                    operations=[],
                ),
                TransactionResult(
                    id="tx-002",
                    status="success",
                    operations=[],
                ),
            ]

            response = await execute_transactions(request, sample_user_id, mock_db)

            assert response.status == "success"
            assert len(response.transactions) == 2
            assert all(tx.status == "success" for tx in response.transactions)

    @pytest.mark.asyncio
    async def test_execute_transactions_serial_failure_skips_remaining(
        self, sample_user_id, mock_db
    ):
        """Test executing transactions in serial mode stops and skips remaining on failure."""
        tx1 = TransactionGroup(
            id="tx-001",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-001",
                    operation="create",
                    domain_object="task",
                    params=CreateParams(data={}),
                )
            ],
        )
        tx2 = TransactionGroup(
            id="tx-002",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-002",
                    operation="list",
                    domain_object="task",
                    params=ListParams(),
                )
            ],
        )
        tx3 = TransactionGroup(
            id="tx-003",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-003",
                    operation="get",
                    domain_object="task",
                    params=GetParams(id=str(uuid7())),
                )
            ],
        )

        request = TransactionsRequest(execution_mode="serial", txs=[tx1, tx2, tx3])

        with patch("app.logic.v1.txs.execute_transaction_group") as mock_exec_tx:
            # First succeeds, second fails
            mock_exec_tx.side_effect = [
                TransactionResult(
                    id="tx-001",
                    status="success",
                    operations=[],
                ),
                TransactionResult(
                    id="tx-002",
                    status="failure",
                    operations=[],
                    error="Transaction failed",
                ),
            ]

            response = await execute_transactions(request, sample_user_id, mock_db)

            assert response.status == "failure"
            assert len(response.transactions) == 3
            assert response.transactions[0].status == "success"
            assert response.transactions[1].status == "failure"
            assert response.transactions[2].status == "skipped"

    @pytest.mark.asyncio
    async def test_execute_transactions_parallel_all_execute(
        self, sample_user_id, mock_db
    ):
        """Test executing transactions in parallel mode executes all regardless of failures."""
        tx1 = TransactionGroup(
            id="tx-001",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-001",
                    operation="create",
                    domain_object="task",
                    params=CreateParams(
                        data={"org_id": str(uuid7()), "team_id": str(uuid7())}
                    ),
                )
            ],
        )
        tx2 = TransactionGroup(
            id="tx-002",
            execution_mode="serial",
            operations=[
                Operation(
                    id="op-002",
                    operation="list",
                    domain_object="task",
                    params=ListParams(),
                )
            ],
        )

        request = TransactionsRequest(execution_mode="parallel", txs=[tx1, tx2])

        with patch("app.logic.v1.txs.execute_transaction_group") as mock_exec_tx:
            # One succeeds, one fails - both should be in result
            mock_exec_tx.side_effect = [
                TransactionResult(
                    id="tx-001",
                    status="success",
                    operations=[],
                ),
                TransactionResult(
                    id="tx-002",
                    status="failure",
                    operations=[],
                    error="Failed",
                ),
            ]

            response = await execute_transactions(request, sample_user_id, mock_db)

            assert response.status == "failure"  # Overall status is failure
            assert len(response.transactions) == 2  # Both executed
            assert response.transactions[0].status == "success"
            assert response.transactions[1].status == "failure"
