# sKrm Server

Backend API for the sKrm application built with FastAPI, featuring structured logging, comprehensive testing, and development best practices.

## Features

- **FastAPI**: Modern, fast web framework for building APIs
- **Async/Await**: Full async support for improved performance
- **Structured Logging**: Using structlog for better log management
- **Type Safety**: Full type hints with mypy validation
- **Code Quality**: Black formatting, isort, and ruff linting
- **Testing**: Comprehensive test suite with pytest
- **Configuration**: Pydantic-based settings management

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [PostgreSQL](https://www.postgresql.org/download/)

### Installation

```bash
# Install dependencies
uv sync

# Copy environment file
cp .env.example .env
```


### Database
```
postgres=# CREATE DATABASE skrm_local;
postgres=# CREATE USER skrm_user WITH ENCRYPTED PASSWORD 'P@ssword12';
postgres=# GRANT ALL PRIVILEGES ON DATABASE skrm_local TO skrm_user;
postgres=# \c skrm_local;
postgres=# GRANT ALL PRIVILEGES ON SCHEMA public TO skrm_user;
postgres=# \q

#### Initial User
```
Username: ***super***

Password: ***P@ssword12***
```
INSERT INTO k_principal (id,"scope",username,primary_email,primary_email_verified,primary_phone,primary_phone_verified,human,enabled,time_zone,name_prefix,first_name,middle_name,last_name,name_suffix,display_name,default_locale,system_role,meta,created,created_by,last_modified,last_modified_by) VALUES
	 ('00000000-0000-0000-0000-000000000000'::uuid,'global','super','super@global.scope',false,NULL,false,true,true,'UTC',NULL,'Super',NULL,'User',NULL,'Super User','en','system_user','{}','2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:35:05.226091','00000000-0000-0000-0000-000000000000'::uuid);

INSERT INTO k_principal_identity (id,principal_id,"password",public_key,device_id,expires,details,created,created_by,last_modified,last_modified_by) VALUES
	 ('0199b6d7-a94f-75e9-a466-fa51620e7181'::uuid,'00000000-0000-0000-0000-000000000000'::uuid,'$2b$12$rdK6qPYTy0OEmjrHSlqsv.GSkqqi2gcJJyMIsMma.SeQS1HwqG002',NULL,NULL,NULL,'{}','2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid,'2025-10-05 21:38:16.33076','00000000-0000-0000-0000-000000000000'::uuid);

```

### Development

You can either use the provided development scripts or run commands directly with uv:

#### Using development scripts

```bash
# Start development server
uv run scripts/dev.py serve

# Run tests
uv run scripts/dev.py test

# Format code
uv run scripts/dev.py format

# Run linting
uv run scripts/dev.py lint

# Clean up test results and build artifacts
uv run scripts/dev.py clean

# Remove all generated files and caches (reset to git state)
uv run scripts/dev.py pristine
```

#### Using uv directly

```bash
# Start development server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest -v --cov=app --cov-report=term-missing

# Format code
uv run black .
uv run isort .
uv run ruff check --fix .

# Run linting
uv run ruff check .
uv run black --check .
uv run isort --check-only .
uv run mypy app

# Clean up test results and build artifacts
rm -rf .pytest_cache .coverage dist build

# Remove all generated files and caches (reset to git state)
rm -rf .pytest_cache .coverage dist build .mypy_cache .ruff_cache .venv
find . -type d -name "__pycache__" -exec rm -rf {} +
```

#### Dependency Management

Always check if your lock file is up-to-date.

```bash
uv lock --check
```

If you manually modify dependencies in `pyproject.toml`, you need to run:

```bash
uv lock
```

This command updates the `uv.lock` file to reflect your changes. The lock file contains exact versions and dependency resolution for reproducible installations across different environments. This ensures all developers and deployment environments use identical dependency versions.

## Authentication & Refresh Tokens

The API implements a dual-strategy refresh token system that supports both web SPAs and mobile applications with optimal security for each platform.

### Overview

**Refresh Token Strategy:**
- **Web Clients (SPAs)**: Refresh tokens are stored in HTTP-only cookies (XSS protection)
- **Mobile Clients (iOS/Android)**: Refresh tokens are returned in response body (stored securely in Keychain/Keystore)

**Client Detection:**
- Preferred: `X-Client-Type: mobile` header
- Fallback: User-Agent patterns (OkHttp, Alamofire, CFNetwork)

### Security Features

1. **HTTP-only Cookies**: Not accessible to JavaScript (XSS protection)
2. **SameSite=Strict**: CSRF protection for web clients
3. **Secure Flag**: Conditional based on environment
   - `False` in development (allows HTTP)
   - `True` in production (HTTPS only)
4. **Token Rotation**: Both access and refresh tokens are rotated on refresh
5. **Path Restriction**: Cookies only sent to `/api/auth` endpoints

### Configuration

The `cookie_secure` setting automatically adjusts based on the `debug` flag:
- When `debug=True`: `cookie_secure` is set to `False` (allows HTTP cookies for local development)
- When `debug=False`: `cookie_secure` defaults to `True` (requires HTTPS)

### Usage Examples

#### Web SPA (JavaScript)

**Login:**
```javascript
// Login - cookie set automatically
const formData = new FormData();
formData.append('username', 'user@example.com');
formData.append('password', 'password123');

const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  credentials: 'include', // Important: sends/receives cookies
  body: formData
});

const { access_token, token_type } = await response.json();
// Refresh token is in HTTP-only cookie, not accessible to JavaScript
// Store access_token in memory or sessionStorage
```

**Refresh Token:**
```javascript
// Refresh - cookie sent automatically
const refreshResponse = await fetch('http://localhost:8000/api/auth/refresh', {
  method: 'POST',
  credentials: 'include', // Cookie sent automatically
});

const { access_token } = await refreshResponse.json();
// New refresh token cookie is set automatically
```

**Logout:**
```javascript
// Logout - clears refresh token cookie
await fetch('http://localhost:8000/api/auth/logout', {
  method: 'POST',
  credentials: 'include',
});
```

**Using Access Token:**
```javascript
// Include access token in Authorization header for API requests
const apiResponse = await fetch('http://localhost:8000/api/v1/some-endpoint', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  },
  credentials: 'include'
});
```

#### Mobile iOS (Swift)

**Login:**
```swift
import Foundation

// Login - include header to identify as mobile client
var request = URLRequest(url: URL(string: "http://localhost:8000/api/auth/login")!)
request.httpMethod = "POST"
request.setValue("mobile", forHTTPHeaderField: "X-Client-Type")
request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

let body = "username=user@example.com&password=password123"
request.httpBody = body.data(using: .utf8)

let (data, _) = try await URLSession.shared.data(for: request)
let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)

// Store refresh_token securely in Keychain
KeychainHelper.store(tokenResponse.refresh_token, forKey: "refresh_token")
// Store access_token in memory
```

**Refresh Token:**
```swift
// Refresh - send token in request body
var refreshRequest = URLRequest(url: URL(string: "http://localhost:8000/api/auth/refresh")!)
refreshRequest.httpMethod = "POST"
refreshRequest.setValue("mobile", forHTTPHeaderField: "X-Client-Type")
refreshRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")

let storedToken = KeychainHelper.retrieve(forKey: "refresh_token")
let refreshBody = ["refresh_token": storedToken]
refreshRequest.httpBody = try JSONEncoder().encode(refreshBody)

let (data, _) = try await URLSession.shared.data(for: refreshRequest)
let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)

// Update stored tokens
KeychainHelper.store(tokenResponse.refresh_token, forKey: "refresh_token")
```

**Token Response Model:**
```swift
struct TokenResponse: Codable {
    let access_token: String
    let token_type: String
    let refresh_token: String
}
```

#### Mobile Android (Kotlin)

**Login:**
```kotlin
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody

// Login - include header to identify as mobile client
val client = OkHttpClient()
val formBody = FormBody.Builder()
    .add("username", "user@example.com")
    .add("password", "password123")
    .build()

val request = Request.Builder()
    .url("http://localhost:8000/api/auth/login")
    .addHeader("X-Client-Type", "mobile")
    .post(formBody)
    .build()

val response = client.newCall(request).execute()
val tokenResponse = JSONObject(response.body?.string() ?: "")

// Store refresh_token securely in EncryptedSharedPreferences or Keystore
val refreshToken = tokenResponse.getString("refresh_token")
SecureStorage.store("refresh_token", refreshToken)
```

**Refresh Token:**
```kotlin
// Refresh - send token in request body
val refreshToken = SecureStorage.retrieve("refresh_token")
val jsonBody = JSONObject().apply {
    put("refresh_token", refreshToken)
}.toString().toRequestBody("application/json".toMediaType())

val refreshRequest = Request.Builder()
    .url("http://localhost:8000/api/auth/refresh")
    .addHeader("X-Client-Type", "mobile")
    .post(jsonBody)
    .build()

val refreshResponse = client.newCall(refreshRequest).execute()
val newTokenResponse = JSONObject(refreshResponse.body?.string() ?: "")

// Update stored tokens
SecureStorage.store("refresh_token", newTokenResponse.getString("refresh_token"))
```

### API Endpoints

**Authentication:**
- `POST /api/auth/login` - Authenticate user and get tokens
- `POST /api/auth/refresh` - Exchange refresh token for new tokens
- `POST /api/auth/logout` - Clear refresh token cookie (web clients)

**Request/Response Format:**

**Login (Web):**
```bash
# Request
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=password123

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": ""  # Empty for web clients (in cookie)
}
# Set-Cookie: refresh_token=eyJ...; HttpOnly; SameSite=Strict; Path=/api/auth
```

**Login (Mobile):**
```bash
# Request
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded
X-Client-Type: mobile

username=user@example.com&password=password123

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": "eyJ..."  # Included in body for mobile
}
```

**Refresh (Web):**
```bash
# Request
POST /api/auth/refresh
Cookie: refresh_token=eyJ...

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": ""  # Empty (new token in cookie)
}
# Set-Cookie: refresh_token=eyJ...; HttpOnly; SameSite=Strict; Path=/api/auth
```

**Refresh (Mobile):**
```bash
# Request
POST /api/auth/refresh
Content-Type: application/json
X-Client-Type: mobile

{"refresh_token": "eyJ..."}

# Response
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "refresh_token": "eyJ..."  # New refresh token in body
}
```

## General API Endpoints

- `GET /` - Hello World endpoint
- `GET /health` - Health check endpoint

See the [Authentication & Refresh Tokens](#authentication--refresh-tokens) section above for authentication endpoints.

## Project Structure

```text
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Configuration management
│   └── logging.py       # Logging setup
├── tests/
│   ├── __init__.py
│   └── test_main.py     # API tests
├── scripts/
│   └── dev.py           # Development scripts
└── pyproject.toml       # Project configuration
```
