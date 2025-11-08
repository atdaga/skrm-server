# Request Context Middleware Usage Examples

This document demonstrates how to use the request context variables (request_id, principal_id, request_time) in your application.

## Overview

The request context middleware automatically populates three context variables for every request:

- **request_id**: A UUID7 unique identifier for the request
- **principal_id**: The user ID extracted from the JWT token's `sub` claim (or `None` if not authenticated)
- **request_time**: UTC timestamp when the request started

## Accessing Context Variables

### 1. Individual Getters

```python
from app.core.context import get_request_id, get_principal_id, get_request_time

@router.get("/example")
async def example_endpoint():
    request_id = get_request_id()  # UUID | None
    principal_id = get_principal_id()  # str | None
    request_time = get_request_time()  # datetime | None

    # Use in your logic
    if principal_id:
        logger.info("User action", user_id=principal_id, request_id=str(request_id))
```

### 2. Get All Context Values at Once

```python
from app.core.context import get_request_context

@router.post("/create-resource")
async def create_resource(data: ResourceCreate):
    context = get_request_context()

    # Access all values
    resource = Resource(
        id=uuid7(),
        created_by=context.principal_id,  # Who created it
        created_at=context.request_time,  # When it was created
        data=data
    )
```

## Use Cases

### 1. Logging and Observability

The middleware automatically adds context to all structlog messages:

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

@router.get("/process-data")
async def process_data():
    logger.info("Starting data processing")  # Automatically includes request_id, principal_id

    try:
        result = await some_long_operation()
        logger.info("Processing complete", result_count=len(result))
    except Exception as e:
        logger.error("Processing failed", error=str(e))  # Error logs have request context

    return result
```

**Example log output (JSON format in production):**
```json
{
  "event": "Starting data processing",
  "logger": "app.routes.v1.data",
  "level": "INFO",
  "timestamp": "2025-11-08T21:30:00.000000Z",
  "request_id": "01933e8d-1234-7abc-def0-123456789abc",
  "principal_id": "01933e8c-5678-7def-9012-fedcba987654",
  "request_time": "2025-11-08T21:30:00.000000Z"
}
```

### 2. Database Auditing

Track who created/modified records and when:

```python
from app.core.context import get_principal_id, get_request_time

@router.post("/tasks")
async def create_task(task_data: TaskCreate, db: AsyncSession):
    principal_id = get_principal_id()
    request_time = get_request_time()

    task = KTask(
        id=uuid7(),
        name=task_data.name,
        description=task_data.description,
        created_by=principal_id,  # Audit: who created it
        last_modified_by=principal_id,  # Audit: who last modified it
        created=request_time,  # Audit: when created
        last_modified=request_time,  # Audit: when last modified
    )

    db.add(task)
    await db.commit()

    return task
```

### 3. Business Logic - Access Current User

No need to pass user ID through multiple layers:

```python
from app.core.context import get_principal_id

async def check_permission(resource_id: UUID) -> bool:
    """Check if the current user has access to a resource."""
    principal_id = get_principal_id()

    if not principal_id:
        return False  # Not authenticated

    # Check if user owns or has access to the resource
    return await has_access(principal_id, resource_id)

@router.get("/protected-resource/{resource_id}")
async def get_protected_resource(resource_id: UUID):
    if not await check_permission(resource_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return await fetch_resource(resource_id)
```

### 4. Request Tracing

Use request_id to trace a request across services or async operations:

```python
from app.core.context import get_request_id
import httpx

@router.post("/trigger-workflow")
async def trigger_workflow(workflow_data: WorkflowCreate):
    request_id = get_request_id()

    # Pass request_id to external services for distributed tracing
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://workflow-engine.example.com/execute",
            json=workflow_data.model_dump(),
            headers={"X-Request-ID": str(request_id)}  # Propagate request ID
        )

    logger.info("Workflow triggered", workflow_id=response.json()["id"])
    return response.json()
```

### 5. Conditional Logic Based on Authentication

```python
from app.core.context import get_principal_id

@router.get("/content")
async def get_content():
    principal_id = get_principal_id()

    if principal_id:
        # Authenticated user - return full content
        return await get_full_content()
    else:
        # Anonymous user - return public content only
        return await get_public_content()
```

## Important Notes

1. **Context Lifetime**: Context variables are automatically set at the start of each request and cleared after the request completes.

2. **None Values**:
   - `principal_id` will be `None` if:
     - No Authorization header is present
     - Token is invalid or expired
     - Token is missing the `sub` claim
   - Other values should always be present during a request

3. **Async Safety**: Context variables are thread-safe and async-safe. They work correctly with concurrent requests.

4. **Testing**: In tests, you can manually set context variables if needed:
   ```python
   from app.core.context import request_id_var, principal_id_var

   def test_with_context():
       request_id_var.set(uuid7())
       principal_id_var.set("test-user-123")

       # Your test code
   ```

5. **Outside Request Context**: If you call getters outside a request (e.g., in background tasks), they will return `None`.

## Integration with Existing Code

The middleware is already integrated in `app/main.py` and runs for all requests. No changes needed to existing endpoints - context variables are automatically available!

To use in new code, simply import the getters:

```python
from app.core.context import get_request_id, get_principal_id, get_request_time
```
