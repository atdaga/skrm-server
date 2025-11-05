# FIDO2 Test Consistency Update

## Issue Identified

You correctly identified that the FIDO2 route tests were **inconsistent** with the existing codebase testing patterns. Good catch!

## Before: Inconsistent Pattern (❌)

### FIDO2 Tests (Original)
```python
@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI app with auth router."""
    app = FastAPI()
    app.include_router(router)
    return app

# EVERY test needed this boilerplate:
async def test_something(app: FastAPI, client: AsyncClient, mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        # test code...
    finally:
        app.dependency_overrides.clear()
```

**Problems:**
- ❌ Verbose - 5+ lines of boilerplate per test
- ❌ Error-prone - easy to forget try/finally
- ❌ Inconsistent with teams and users tests
- ❌ Hard to maintain - changes require updating many tests

---

## Existing Patterns in Codebase (✅)

### Teams Tests Pattern
```python
@pytest.fixture
def app_with_overrides(async_session, mock_token_data) -> FastAPI:
    """Create a FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_token] = lambda: mock_token_data
    return app

# Tests are clean:
async def test_something(client: AsyncClient):
    response = await client.get("/teams")
    assert response.status_code == 200
```

### Users Tests Pattern
```python
@pytest.fixture
def app_with_overrides(mock_user_detail: UserDetail) -> FastAPI:
    """Create a FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: mock_user_detail
    return app

# Tests are clean:
async def test_something(client: AsyncClient):
    response = await client.get("/users/me")
    assert response.status_code == 200
```

---

## After: Consistent Pattern (✅)

### Updated FIDO2 Tests
```python
@pytest.fixture
def app_with_overrides(mock_user: UserDetail) -> FastAPI:
    """Create a FastAPI app with auth router and dependency overrides."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return app

@pytest.fixture
def app_without_auth() -> FastAPI:
    """Create a FastAPI app without authentication overrides for testing auth failures."""
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
async def client(app_with_overrides: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing with authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_overrides), base_url="http://test"
    ) as ac:
        yield ac

@pytest.fixture
async def client_no_auth(app_without_auth: FastAPI) -> AsyncClient:
    """Create an async HTTP client for testing without authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app_without_auth), base_url="http://test"
    ) as ac:
        yield ac

# Tests are now clean:
async def test_list_credentials_success(client: AsyncClient, mock_user):
    """Test listing user credentials."""
    with patch("app.logic.auth.list_user_credentials", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [...]
        result = await client.get("/auth/fido2/credentials")
        assert result.status_code == 200

# Unauthorized tests are also clean:
async def test_register_begin_unauthorized(client_no_auth: AsyncClient):
    """Test registration fails without authentication."""
    result = await client_no_auth.post("/auth/fido2/register/begin")
    assert result.status_code == 401
```

---

## Key Improvements

### 1. **Fixture-Based Override** ✅
- Override set up **once** in fixtures, not per-test
- Matches teams and users tests pattern
- Cleaner, more maintainable

### 2. **Two Client Fixtures** ✅
- `client` - with authentication (for protected endpoints)
- `client_no_auth` - without authentication (for 401 tests)
- Tests just specify which client they need

### 3. **No Boilerplate in Tests** ✅
Before (per test):
```python
app.dependency_overrides[get_current_user] = lambda: mock_user
try:
    # 3 lines of test code
finally:
    app.dependency_overrides.clear()
```

After (per test):
```python
# Just 3 lines of test code
```

### 4. **Consistent with Codebase** ✅
All route tests now follow the same pattern:
- ✅ `tests/routes/v1/test_teams.py` - uses `app_with_overrides`
- ✅ `tests/routes/v1/test_users.py` - uses `app_with_overrides`
- ✅ `tests/routes/test_fido2_auth.py` - uses `app_with_overrides`

---

## Code Reduction

### Lines Removed
- Removed ~70 lines of repetitive setup/teardown code
- Eliminated 10+ try/finally blocks
- Removed 10+ calls to `app.dependency_overrides.clear()`

### Tests Updated
- **10 tests** cleaned up (removed manual override setup)
- **2 tests** now use `client_no_auth` fixture
- **0 tests broken** - all 16 still pass ✅

---

## Benefits

### Maintainability ⬆️
- Single place to change auth mocking strategy
- Less code duplication
- Easier to understand

### Reliability ⬆️
- No risk of forgetting try/finally
- Fixtures automatically clean up
- Consistent test behavior

### Readability ⬆️
- Tests focus on what they're testing
- Less boilerplate noise
- Intent is clearer

### Consistency ⬆️
- Matches existing codebase patterns
- New developers see familiar patterns
- Easier code reviews

---

## Testing Pattern Summary

### For Protected Endpoints
```python
async def test_something(client: AsyncClient, mock_user):
    # client already has auth override from fixture
    result = await client.get("/auth/fido2/credentials")
    assert result.status_code == 200
```

### For Unauthorized Tests
```python
async def test_something_unauthorized(client_no_auth: AsyncClient):
    # client_no_auth has NO auth override
    result = await client_no_auth.get("/auth/fido2/credentials")
    assert result.status_code == 401
```

### For Public Endpoints (no auth needed)
```python
async def test_something_public(client: AsyncClient):
    # Even though client has auth, public endpoints ignore it
    result = await client.post("/auth/fido2/authenticate/begin", json={...})
    assert result.status_code == 200
```

---

## Test Results

**All 16 tests passing** ✅

```
tests/routes/test_fido2_auth.py ................                         [100%]
============================== 16 passed in 0.21s ==============================
```

---

## Conclusion

The FIDO2 tests now follow the **same consistent pattern** as the rest of the codebase:

1. ✅ Fixture-based dependency overrides
2. ✅ Clean test methods without boilerplate
3. ✅ Separate clients for auth/no-auth scenarios
4. ✅ Consistent with teams and users tests

Great catch on the inconsistency! The codebase is now more maintainable and follows established patterns throughout.

