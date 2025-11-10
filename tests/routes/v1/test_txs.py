"""Unit tests for transaction batch API endpoint."""

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid7

import pytest
from httpx import AsyncClient

from app.routes.v1.txs import router
from app.schemas.txs import TransactionResult, TransactionsResponse


@pytest.fixture
def app_with_overrides(app_with_overrides):
    """Create a FastAPI app with txs router included."""
    app_with_overrides.include_router(router)
    return app_with_overrides


class TestExecuteTransactions:
    """Test suite for POST /txs endpoint."""

    @pytest.mark.asyncio
    async def test_execute_transactions_success(
        self,
        client: AsyncClient,
        test_user_id: UUID,
    ):
        """Test successfully executing a transaction batch."""
        request_data = {
            "execution_mode": "serial",
            "txs": [
                {
                    "id": "tx-001",
                    "execution_mode": "serial",
                    "operations": [
                        {
                            "id": "op-001",
                            "operation": "create",
                            "domain_object": "task",
                            "params": {
                                "data": {
                                    "team_id": str(uuid7()),
                                    "org_id": str(uuid7()),
                                    "summary": "Test Task",
                                }
                            },
                        }
                    ],
                }
            ],
        }

        # Mock the logic layer function
        mock_response = TransactionsResponse(
            status="success",
            transactions=[
                TransactionResult(
                    id="tx-001",
                    status="success",
                    operations=[],
                )
            ],
        )

        with patch(
            "app.routes.v1.txs.txs_logic.execute_transactions", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_response

            response = await client.post("/txs", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["transactions"]) == 1
            assert data["transactions"][0]["id"] == "tx-001"
            assert data["transactions"][0]["status"] == "success"

            # Verify the logic function was called with correct parameters
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args.kwargs["user_id"] == test_user_id
            assert call_args.kwargs["request"].execution_mode == "serial"
