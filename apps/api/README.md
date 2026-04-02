# Aiden.ai API

FastAPI backend for Aiden.ai with multi-tenancy and RBAC support.

## Architecture

### Multi-Tenancy Model

Every data access is scoped by `tenant_id` and `workspace_id`. No global reads are allowed.

```
Tenant (Organization)
├── Users (belong to a tenant)
├── Workspaces (belong to a tenant)
│   └── Workspace Memberships (link users to workspaces with roles)
```

### Tables

- **tenants**: Organizations with jurisdiction and data residency settings
- **workspaces**: Logical containers within a tenant (IN_HOUSE or LAW_FIRM)
- **users**: App-level user profiles (no real auth yet)
- **workspace_memberships**: Links users to workspaces with RBAC roles
- **policy_profiles**: Policy configurations for workflows, languages, jurisdictions
- **audit_logs**: Append-only audit trail for compliance
- **documents**: Document metadata (title, type, jurisdiction, language, confidentiality)
- **document_versions**: File versions with S3 storage references

### RBAC Roles

- **ADMIN**: Can create/manage resources, policies, users, memberships
- **EDITOR**: Can upload documents, create versions
- **VIEWER**: Read-only access (list, view, download documents)

## Development

### Prerequisites

- Docker Desktop (Windows)
- Python 3.12+
- uv (Python package manager)

### Quick Start (PowerShell)

```powershell
# 1. Start infrastructure services (MinIO + minio-init creates buckets)
docker compose up postgres redis minio minio-init -d

# 2. Navigate to API directory
cd apps/api

# 3. Install dependencies
uv sync

# 4. Run database migrations
uv run alembic upgrade head

# 5. Start the API server
uv run uvicorn src.main:app --reload
```

### Running with Docker

```powershell
# From project root - starts all services
docker compose up

# Or just the API with dependencies
docker compose up api
```

### Database Migrations

```powershell
# Navigate to API directory first
cd apps/api

# Apply all migrations
uv run alembic upgrade head

# Create a new migration (after changing models)
uv run alembic revision --autogenerate -m "description of changes"

# View current migration status
uv run alembic current

# Downgrade one migration
uv run alembic downgrade -1

# View migration history
uv run alembic history
```

### Running Tests

Tests are organized into two categories:
- **Unit tests**: No database required (e.g., JWT utilities)
- **Integration tests**: Require PostgreSQL and MinIO (with minio-init) running

```powershell
# Navigate to API directory
cd apps/api

# ========================================
# Unit Tests (no database required)
# ========================================

# Run JWT utility tests (fast, no DB)
uv run pytest tests/test_auth.py::TestJWTUtils -v

# Run all unit tests
uv run pytest -m unit -v

# ========================================
# Integration Tests (require PostgreSQL + MinIO)
# ========================================

# Start PostgreSQL and MinIO (minio-init creates required buckets)
docker compose up postgres minio minio-init -d

# Run all tests (unit + integration)
uv run pytest

# Run integration tests only
uv run pytest -m integration -v

# Run specific test file
uv run pytest tests/test_bootstrap.py -v

# Run document/extraction tests (require MinIO)
uv run pytest tests/test_documents.py tests/test_extraction.py -v

# Run with coverage
uv run pytest --cov=src

# Run with verbose output
uv run pytest -v
```

### Linting & Type Checking

```powershell
cd apps/api

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy .
```

## Bootstrapping a Tenant

The API supports **zero-friction bootstrap** - you can create a fully functional tenant with admin user and workspace in a single API call, with no database seeding required.

### Bootstrap via API (Recommended)

Use the bootstrap payload when creating a tenant:

```powershell
$body = @{
    name = "Acme Corp"
    primary_jurisdiction = "UAE"
    data_residency_policy = "UAE"
    bootstrap = @{
        admin_user = @{
            email = "admin@acme.com"
            full_name = "Admin User"
        }
        workspace = @{
            name = "Main Workspace"
            workspace_type = "IN_HOUSE"
            jurisdiction_profile = "UAE_DEFAULT"
            default_language = "en"
        }
    }
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "http://localhost:8000/tenants" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

# Save the returned IDs for subsequent calls
$tenantId = $response.tenant_id
$workspaceId = $response.workspace_id
$adminUserId = $response.admin_user_id

Write-Host "Tenant ID: $tenantId"
Write-Host "Workspace ID: $workspaceId"
Write-Host "Admin User ID: $adminUserId"
```

The bootstrap response includes all IDs needed for subsequent API calls:

```json
{
  "tenant_id": "uuid-here",
  "tenant_name": "Acme Corp",
  "workspace_id": "uuid-here",
  "workspace_name": "Main Workspace",
  "admin_user_id": "uuid-here",
  "admin_user_email": "admin@acme.com",
  "created_at": "2025-01-24T..."
}
```

### Using JWT After Bootstrap (Recommended)

After bootstrapping, get a JWT token and use it for subsequent calls:

```powershell
# Get JWT token
$loginBody = @{
    tenant_id = $tenantId
    workspace_id = $workspaceId
    email = "admin@acme.com"
} | ConvertTo-Json

$auth = Invoke-RestMethod -Uri "http://localhost:8000/auth/dev-login" `
    -Method POST -ContentType "application/json" -Body $loginBody

$headers = @{ "Authorization" = "Bearer $($auth.access_token)" }

# List workspaces
Invoke-RestMethod -Uri "http://localhost:8000/tenants/$tenantId/workspaces" `
    -Method GET -Headers $headers

# List workspace members
Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$workspaceId/memberships" `
    -Method GET -Headers $headers
```

### Using Header Auth (Legacy/Debug Mode)

If using `AUTH_MODE=headers`, use the returned IDs as headers:

```powershell
# Set headers for all subsequent requests
$headers = @{
    "X-Tenant-Id" = $tenantId
    "X-Workspace-Id" = $workspaceId
    "X-User-Id" = $adminUserId
}

# List workspaces
Invoke-RestMethod -Uri "http://localhost:8000/tenants/$tenantId/workspaces" `
    -Method GET `
    -Headers @{ "X-Tenant-Id" = $tenantId; "X-User-Id" = $adminUserId }

# List workspace members
Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$workspaceId/memberships" `
    -Method GET `
    -Headers $headers
```

## API Endpoints

### Health Check (No Auth)

- `GET /health` - Health check
- `GET /` - Root endpoint

### Authentication

- `POST /auth/dev-login` - Get JWT token (dev mode, no auth required)
- `GET /auth/me` - Get current user info (requires Bearer token)

### Tenant Management

- `POST /tenants` - Create a new tenant (open for dev, supports bootstrap)
- `GET /tenants/{tenant_id}/workspaces` - List workspaces (requires auth)
- `POST /tenants/{tenant_id}/workspaces` - Create workspace (ADMIN only)
- `POST /tenants/{tenant_id}/users` - Create user (ADMIN only)

### Workspace Management

- `GET /workspaces/{workspace_id}/memberships` - List members (any member)
- `POST /workspaces/{workspace_id}/memberships` - Add member by user_id (ADMIN only)

### Member Management (v2)

- `GET /workspaces/{workspace_id}/members` - List members with user details (VIEWER+)
- `POST /workspaces/{workspace_id}/members` - Invite member by email (ADMIN only)
- `PATCH /workspaces/{workspace_id}/members/{membership_id}` - Update member role (ADMIN only)
- `DELETE /workspaces/{workspace_id}/members/{membership_id}` - Remove member (ADMIN only)

**Member Management Features:**
- Invite users by email - creates user if not exists in tenant
- Update member roles (ADMIN, EDITOR, VIEWER)
- Remove members from workspace
- Last admin protection - cannot remove/demote the last admin
- Tenant isolation enforced on all operations
- Audit logging for all member operations (workspace.member.add, workspace.member.role.update, workspace.member.remove)

### Audit Logging

- `GET /audit` - List audit logs (ADMIN only, tenant-scoped)

### Policy Management

- `POST /policy-profiles` - Create policy profile (ADMIN only)
- `GET /policy-profiles` - List policy profiles (ADMIN only)
- `PATCH /policy-profiles/{policy_id}` - Update policy profile (ADMIN only)
- `POST /workspaces/{workspace_id}/policy-profile` - Attach policy to workspace (ADMIN only)
- `GET /policy/resolve` - Resolve effective policy for current context (ADMIN only)

## Authentication

The API uses httpOnly cookie-based authentication with refresh token rotation for enterprise security.

### Cookie-Based Authentication (Default)

When `AUTH_MODE=jwt` (default), the API uses httpOnly cookies for authentication:

- **Access Token**: Short-lived (default 15 min), stored as httpOnly cookie
- **Refresh Token**: Long-lived (default 7 days), stored as httpOnly cookie, rotated on use
- **No localStorage**: Tokens are never exposed to JavaScript, preventing XSS attacks

#### Quick Start: Login and Make Requests

```powershell
# Step 1: Bootstrap a tenant (no auth required)
$bootstrap = @{
    name = "My Company"
    primary_jurisdiction = "UAE"
    data_residency_policy = "UAE"
    bootstrap = @{
        admin_user = @{ email = "admin@mycompany.com"; full_name = "Admin User" }
        workspace = @{ name = "Main Workspace" }
    }
} | ConvertTo-Json -Depth 3

$tenant = Invoke-RestMethod -Uri "http://localhost:8000/tenants" `
    -Method POST -ContentType "application/json" -Body $bootstrap

# Step 2: Login via dev-login (cookies are set automatically)
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginBody = @{
    tenant_id = $tenant.tenant_id
    workspace_id = $tenant.workspace_id
    email = "admin@mycompany.com"
} | ConvertTo-Json

$auth = Invoke-RestMethod -Uri "http://localhost:8000/auth/dev-login" `
    -Method POST -ContentType "application/json" -Body $loginBody -WebSession $session

Write-Host "Logged in as: $($auth.email) with role: $($auth.role)"
Write-Host "Access token expires in: $($auth.expires_in) seconds"

# Step 3: Use session for protected endpoints (cookies sent automatically)
# Get current user info
Invoke-RestMethod -Uri "http://localhost:8000/auth/me" -WebSession $session

# List workspace memberships
Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$($tenant.workspace_id)/memberships" -WebSession $session
```

#### JWT Token Claims

Both access and refresh tokens contain these claims:
- `sub`: User ID
- `tenant_id`: Tenant ID
- `workspace_id`: Workspace ID
- `role`: User's role (ADMIN, EDITOR, VIEWER)
- `token_version`: For session revocation
- `token_type`: "access" or "refresh"
- `jti`: Unique ID (refresh tokens only, for rotation tracking)
- `exp`: Expiration time
- `iat`: Issue time

#### Auth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/dev-login` | POST | Login, sets cookies, returns user info |
| `/auth/refresh` | POST | Rotate tokens, sets new cookies |
| `/auth/logout` | POST | Logout, clears cookies, revokes session |
| `/auth/logout-all` | POST | Logout everywhere, revokes all sessions |
| `/auth/me` | GET | Get current user info |

#### Dev Login Response

```json
{
  "user_id": "uuid",
  "email": "admin@mycompany.com",
  "role": "ADMIN",
  "expires_in": 900,
  "auth_mode": "cookie"
}
```

#### Refresh Response

```json
{
  "expires_in": 900,
  "auth_mode": "cookie"
}
```

#### Cookie Configuration

| Cookie | Path | httpOnly | SameSite | Secure |
|--------|------|----------|----------|--------|
| `access_token` | `/` | Yes | Lax | Dev: No, Staging/Prod: Yes |
| `refresh_token` | `/auth` | Yes | Lax | Dev: No, Staging/Prod: Yes |

**Cookie Attribute Rules:**
- **httpOnly**: Always `true` - prevents JavaScript access (XSS protection)
- **SameSite=Lax**: Explicitly set - cookies sent on top-level navigation, blocked on cross-origin subrequests (CSRF protection)
- **Path**: Access token uses `/` (all routes), refresh token uses `/auth` (only auth endpoints)
- **Secure**: Auto-derived from `ENVIRONMENT` - `false` in dev (allows localhost HTTP), `true` in staging/prod
- **Cookie clearing**: Uses same Path/SameSite/Secure attributes to ensure proper removal

**Note**: The `Secure` flag is enforced in staging/prod even before SSL is configured. In dev, cookies work over HTTP localhost.

#### Verify Cookie Auth

Use the `cookie-check` command to verify cookie-based auth works end-to-end:

```powershell
.\infra\dev.ps1 cookie-check
```

This verifies: login sets cookies, `/auth/me` works with cookies, refresh rotates tokens, logout clears cookies.

### Same-Origin Architecture (Production Target)

The application is designed for same-origin deployment where Web and API are served from the same origin:

```
Production Setup:
  Browser → https://app.example.com/ (Web)
          → https://app.example.com/api/ (API via reverse proxy)

Benefits:
  - No CORS complexity (same origin)
  - Cookies work with SameSite=Lax (no cross-site issues)
  - Simpler security model
```

**API Root Path Configuration:**

When running behind a reverse proxy that mounts the API at `/api`:

```bash
# Set in production
API_ROOT_PATH=/api
```

This configures FastAPI's `root_path` for correct OpenAPI docs and URL generation.

**Verify Same-Origin Prep:**

```powershell
.\infra\dev.ps1 same-origin-check
```

**Current Dev vs Production:**

| Mode | Web URL | API URL | SameSite |
|------|---------|---------|----------|
| Dev (cross-origin) | localhost:3000 | localhost:8000 | Lax works (same site) |
| Prod (same-origin) | app.com | app.com/api | Lax works (same origin) |

**Note**: SameSite=None is only needed for true cross-site scenarios (e.g., embedded iframes from different sites). Our architecture avoids this.

### Refresh Token Rotation

The API implements refresh token rotation for enhanced security:

1. **On Login**: A refresh token with unique `jti` (JWT ID) is issued and stored in `refresh_sessions` table
2. **On Refresh**: The old refresh token is revoked, a new one is issued with a new `jti`
3. **Reuse Detection**: If a revoked refresh token is reused, ALL sessions for that user are revoked (security measure)

```powershell
# Refresh tokens (with session)
Invoke-RestMethod -Uri "http://localhost:8000/auth/refresh" `
    -Method POST -WebSession $session

# Returns new tokens in cookies + expiry info
```

#### Refresh Reuse Detection

If someone replays an old refresh token:
```json
{
  "detail": {
    "error_code": "refresh_reuse_detected",
    "message": "Refresh token reuse detected. All sessions have been revoked for security."
  }
}
```

### Header Authentication (Legacy/Debug Mode)

When `AUTH_MODE=headers`, the API uses X-* headers for authentication (useful for debugging):

| Header | Required For | Description |
|--------|--------------|-------------|
| `X-Tenant-Id` | All except /health, POST /tenants | UUID of the tenant |
| `X-User-Id` | All except /health, POST /tenants | UUID of the acting user |
| `X-Workspace-Id` | Workspace-scoped + ADMIN endpoints | UUID of the workspace |

**Note**: In `AUTH_MODE=jwt` (default), Authorization header is only allowed as fallback in dev environment.

To switch to header mode:
```powershell
$env:AUTH_MODE = "headers"
```

Or in `.env`:
```
AUTH_MODE=headers
```

### Security Guarantees

Both authentication modes enforce:

1. **Tenant Isolation**: User must belong to the specified tenant
2. **Workspace Isolation**: Workspace must belong to the tenant
3. **Membership Checks**: User must be a member of the workspace for workspace-scoped operations
4. **Active User Check**: Inactive users are blocked from all operations
5. **Role Enforcement**: ADMIN role required for create/manage operations

### JWT and Cookie Configuration

Environment variables for authentication configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_MODE` | `jwt` | Authentication mode: `jwt` or `headers` |
| `JWT_SECRET` | (dev default) | Secret key for signing tokens. **Change in production!** |
| `ACCESS_TOKEN_EXPIRES_MINUTES` | `15` | Access token expiration (short-lived) |
| `REFRESH_TOKEN_EXPIRES_DAYS` | `7` | Refresh token expiration (long-lived) |
| `JWT_EXPIRES_MINUTES` | `60` | Legacy: kept for backwards compatibility |
| `AUTH_ALLOW_DEV_LOGIN` | `true` | Enable/disable `/auth/dev-login` endpoint |
| `COOKIE_SECURE` | (auto) | Override Secure flag for cookies (auto-derived from ENVIRONMENT) |

**Cookie Secure Flag Behavior:**

| Environment | Secure Flag |
|-------------|-------------|
| `dev` | `false` (allows localhost without HTTPS) |
| `staging` | `true` (enforced even before SSL) |
| `prod` | `true` (enforced even before SSL) |

**Security Note**: The default `JWT_SECRET` is for development only. In production:
```bash
# Generate a secure secret
openssl rand -hex 32
```

### Session Revocation (Logout All)

The API supports session revocation via the `token_version` mechanism:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/logout-all` | POST | Invalidate all sessions for current user |

When called, `logout-all` increments the user's `token_version`, which invalidates all existing JWT tokens. The user must re-authenticate to get a new token.

```powershell
# Logout from all devices
Invoke-RestMethod -Uri "http://localhost:8000/auth/logout-all" `
    -Method POST -Headers $headers
```

**Use cases:**
- Security response after suspected credential compromise
- Force re-authentication after role/permission changes
- User-initiated "logout everywhere" action

**How it works:**
1. JWT tokens include a `token_version` claim
2. On each request, the API validates that `token.token_version == user.token_version`
3. If they don't match, the request is rejected with HTTP 401
4. `logout-all` increments the user's `token_version`, invalidating all existing tokens

**Error Response (token_revoked):**

When a token is revoked, the API returns a structured error:

```json
{
  "detail": {
    "error_code": "token_revoked",
    "message": "Your session has expired. Please sign in again."
  }
}
```

Web clients should check for `error_code === "token_revoked"` and:
- Clear the local session
- Redirect to login with an info message (not an alert)

### SSO Integration (Future)

The codebase includes an SSO boundary (`src/sso/`) prepared for future enterprise OIDC/SAML integration. See the module docstring for integration notes.

## Environment Configuration

The API supports multiple environments with safety rails to prevent dev features from leaking into production.

### Environment Variable

| Variable | Default | Values | Description |
|----------|---------|--------|-------------|
| `ENVIRONMENT` | `dev` | `dev`, `staging`, `prod` | Current environment |

### Environment Safety Rails

**CRITICAL**: Dev-login is automatically disabled in non-dev environments.

| Environment | `auth_allow_dev_login=true` | `auth_allow_dev_login=false` |
|-------------|----------------------------|------------------------------|
| `dev` | Allowed | Allowed |
| `staging` | **STARTUP ERROR** | Allowed |
| `prod` | **STARTUP ERROR** | Allowed |

This prevents accidental deployment of dev-login to production.

**Startup Error Message:**

When an invalid combination is detected, the application fails with a clear error:

```
CRITICAL SECURITY ERROR: Environment safety rails violation.

  Current configuration:
    ENVIRONMENT = prod
    AUTH_ALLOW_DEV_LOGIN = true

  This combination is forbidden. Dev-login is only allowed in 'dev' environment.

  Remediation (choose one):
    1. Set ENVIRONMENT=dev (for local development)
    2. Set AUTH_ALLOW_DEV_LOGIN=false (for staging/prod)
```

```powershell
# Production environment (dev-login blocked)
$env:ENVIRONMENT = "prod"
$env:AUTH_ALLOW_DEV_LOGIN = "false"

# Development environment (dev-login allowed)
$env:ENVIRONMENT = "dev"
$env:AUTH_ALLOW_DEV_LOGIN = "true"
```

### Health Endpoint

The `/health` endpoint returns the current environment:

```json
{
  "status": "ok",
  "environment": "dev"
}
```

This is useful for monitoring and deployment verification.

## Request Tracing (X-Request-Id)

Every request is assigned a unique request ID for tracing and debugging.

### How It Works

1. **Incoming requests**: If you include an `X-Request-Id` header with a valid UUID, that ID is used
2. **Generated IDs**: If no header is provided (or invalid), a new UUID is generated
3. **Response headers**: The `X-Request-Id` header is always included in responses
4. **Audit logs**: All audit log entries include the request ID for correlation

### Usage Example

```powershell
# Let the server generate a request ID
$response = Invoke-WebRequest -Uri "http://localhost:8000/health"
$response.Headers["X-Request-Id"]  # Returns generated UUID

# Provide your own request ID for tracing
$headers = @{ "X-Request-Id" = "my-trace-id-12345678-1234-1234-1234-123456789012" }
$response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Headers $headers
$response.Headers["X-Request-Id"]  # Returns "my-trace-id-..."
```

### Benefits

- **Debugging**: Correlate logs across services using the same request ID
- **Support**: Users can provide request IDs when reporting issues
- **Audit trail**: All audit log entries are linked to their request ID

## Audit Logging

The API includes enterprise-grade audit logging for compliance and debugging.

### What Gets Logged

All significant actions are recorded in an append-only `audit_logs` table:

| Action | Description |
|--------|-------------|
| `auth.dev_login` | Login attempts (success and failure) |
| `auth.me` | Current user info requests |
| `auth.logout_all` | Session revocation (logout everywhere) |
| `tenant.create` | Tenant creation |
| `workspace.create` | Workspace creation |
| `user.create` | User creation |
| `membership.create` | Membership creation |
| `workflow.run.success` | Workflow executed successfully |
| `workflow.run.fail` | Workflow execution failed |

### Audit Log Fields

Each audit log entry contains:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier |
| `created_at` | Timestamp |
| `tenant_id` | Tenant context |
| `workspace_id` | Workspace context (if applicable) |
| `user_id` | Acting user |
| `request_id` | Request tracing ID |
| `action` | Action identifier |
| `resource_type` | Type of affected resource |
| `resource_id` | ID of affected resource |
| `status` | "success" or "fail" |
| `meta` | Additional context (JSON) - includes `environment` field |
| `ip` | Client IP address |
| `user_agent` | Client User-Agent |

### Querying Audit Logs

Use the `GET /audit` endpoint to query audit logs. Requires ADMIN role.

```powershell
# Get all audit logs for tenant (most recent first)
Invoke-RestMethod -Uri "http://localhost:8000/audit" -Headers $headers

# Filter by workspace
Invoke-RestMethod -Uri "http://localhost:8000/audit?workspace_id=$workspaceId" -Headers $headers

# Filter by action
Invoke-RestMethod -Uri "http://localhost:8000/audit?action=auth.dev_login" -Headers $headers

# Limit results
Invoke-RestMethod -Uri "http://localhost:8000/audit?limit=10" -Headers $headers
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `workspace_id` | UUID (optional) | Filter by workspace (must belong to tenant) |
| `action` | string (optional) | Filter by action (e.g., "auth.dev_login") |
| `limit` | int (optional) | Max entries to return (default: 50, max: 200) |

### Response Format

```json
{
  "items": [
    {
      "id": "uuid",
      "created_at": "2025-01-24T12:00:00Z",
      "tenant_id": "uuid",
      "workspace_id": "uuid",
      "user_id": "uuid",
      "request_id": "uuid",
      "action": "auth.dev_login",
      "resource_type": null,
      "resource_id": null,
      "status": "success",
      "meta": {"email": "admin@example.com", "role": "ADMIN"},
      "ip": "127.0.0.1",
      "user_agent": "Mozilla/5.0 ..."
    }
  ],
  "total": 100,
  "limit": 50
}
```

## Policy Engine

The API includes a policy engine for controlling what workflows, languages, jurisdictions, and features are allowed within workspaces. This enables future support for Saudi Arabia, law firm mode, multilingual capabilities, and custom workflows without requiring refactoring.

### What Are Policy Profiles?

A **Policy Profile** is a tenant-scoped configuration that defines:

- **allowed_workflows**: List of workflow identifiers that can be executed (e.g., `CONTRACT_REVIEW_V1`)
- **allowed_input_languages**: Languages accepted as input (e.g., `en`, `ar`, `mixed`)
- **allowed_output_languages**: Languages for generated output
- **allowed_jurisdictions**: Legal jurisdictions that can be processed (e.g., `UAE`, `DIFC`, `ADGM`, `KSA`)
- **feature_flags**: Boolean flags for enabling/disabling features (e.g., `law_firm_mode`)
- **retrieval**: Configuration for document retrieval (stub for future RAG)
- **generation**: Configuration for LLM generation (stub for future implementation)

### Policy Resolution Order

When resolving the effective policy for a request, the system checks in order:

1. **Workspace Policy**: If the workspace has a `policy_profile_id` set, use that policy
2. **Tenant Default**: If no workspace policy, use the tenant's default policy (`is_default=true`)
3. **Built-in Default**: If neither exists, use a restrictive built-in default (denies all workflows)

### Creating a Policy Profile (PowerShell)

```powershell
# Get JWT token first (see Authentication section)
$headers = @{ "Authorization" = "Bearer $token" }

# Create a policy profile
$policyBody = @{
    name = "Standard UAE Policy"
    description = "Default policy for UAE legal workspaces"
    config = @{
        allowed_workflows = @("CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1")
        allowed_input_languages = @("en", "ar", "mixed")
        allowed_output_languages = @("en", "ar")
        allowed_jurisdictions = @("UAE", "DIFC", "ADGM")
        feature_flags = @{ law_firm_mode = $false; advanced_analytics = $true }
        retrieval = @{ max_chunks = 12 }
        generation = @{ require_citations = $true }
    }
    is_default = $true
} | ConvertTo-Json -Depth 4

$policy = Invoke-RestMethod -Uri "http://localhost:8000/policy-profiles" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $policyBody

Write-Host "Created policy: $($policy.name) with ID: $($policy.id)"
```

### Attaching a Policy to a Workspace (PowerShell)

```powershell
# Attach the policy to a workspace
$attachBody = @{ policy_profile_id = $policy.id } | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$workspaceId/policy-profile" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $attachBody
```

### Resolving the Effective Policy (PowerShell)

```powershell
# Resolve policy for current context (no workflow check)
$resolved = Invoke-RestMethod -Uri "http://localhost:8000/policy/resolve" -Headers $headers
Write-Host "Using policy: $($resolved.policy_profile_name) from source: $($resolved.source)"

# Resolve and check if a specific workflow is allowed
$resolved = Invoke-RestMethod -Uri "http://localhost:8000/policy/resolve?workflow_name=CONTRACT_REVIEW_V1" -Headers $headers
if ($resolved.workflow_allowed) {
    Write-Host "Workflow CONTRACT_REVIEW_V1 is allowed"
} else {
    Write-Host "Workflow denied: $($resolved.workflow_denied_reason)"
}
```

### Policy Configuration Schema

```json
{
  "allowed_workflows": ["CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1"],
  "allowed_input_languages": ["en", "ar", "mixed"],
  "allowed_output_languages": ["en", "ar"],
  "allowed_jurisdictions": ["UAE", "DIFC", "ADGM", "KSA"],
  "feature_flags": {
    "law_firm_mode": false,
    "advanced_analytics": true
  },
  "retrieval": {
    "max_chunks": 12
  },
  "generation": {
    "require_citations": true
  }
}
```

### Workflow Enforcement

**Important**: Workflow endpoints must call `require_workflow_allowed(...)` before executing any workflow logic.

The `require_workflow` dependency provides centralized policy enforcement:

```python
from typing import Annotated
from fastapi import Depends
from src.dependencies import require_workflow
from src.schemas.policy import ResolvedPolicy

@router.post("/contracts/review")
async def review_contract(
    policy: Annotated[ResolvedPolicy, Depends(require_workflow("CONTRACT_REVIEW_V1"))],
):
    # At this point, workflow is confirmed allowed by policy
    # policy.config contains the effective policy settings (jurisdictions, languages, etc.)
    ...
```

If the workflow is not in the `allowed_workflows` list, the request is rejected with HTTP 403.

### Policy Audit Logging

All policy operations are audit logged:

| Action | Description |
|--------|-------------|
| `policy_profile.create` | Policy profile created |
| `policy_profile.update` | Policy profile updated |
| `workspace.policy_profile.attach` | Policy attached to workspace |

### Meta Field Guidelines

The `meta` field contains structured context about the action. **Important**:

- **Never store sensitive data** (passwords, tokens, secrets)
- **Never store document content** (contracts, PII)
- **Keep payloads small** (< 1KB recommended)
- **Use for debugging context** (email, role, error reasons)

Examples of appropriate meta content:
- `{"email": "user@example.com"}` - User identifier
- `{"reason": "user_not_found"}` - Failure reason
- `{"role": "ADMIN"}` - Role context
- `{"workspace_name": "Main"}` - Resource names

### Audit Log Immutability

Audit logs are **append-only**:
- Records are never updated or deleted
- Provides tamper-evident trail for compliance
- Suitable for regulatory requirements (GDPR, SOC2, etc.)

## Document Vault

The API includes a secure, multi-tenant document vault for storing and versioning documents with S3/MinIO storage.

### Features

- **Document Upload**: Upload documents with metadata (title, type, jurisdiction, language, confidentiality)
- **Version Control**: Each document supports multiple versions with automatic version numbering
- **S3 Storage**: Files stored in MinIO (S3-compatible) with secure key generation
- **Policy Enforcement**: Language and jurisdiction constraints enforced at upload time
- **Audit Logging**: All uploads and downloads are audit logged
- **Role-Based Access**: VIEWER can list/download, EDITOR/ADMIN can upload

### Environment Variables for S3/MinIO

The API uses **canonical S3_* environment variables** for all S3/MinIO configuration.
Legacy `AWS_*` variables are supported as fallback but deprecated (a warning is logged on startup).

| Variable | Default | Description |
|----------|---------|-------------|
| `S3_ENDPOINT_URL` | `http://localhost:9000` | Full S3/MinIO endpoint URL |
| `S3_ACCESS_KEY_ID` | `minioadmin` | S3/MinIO access key |
| `S3_SECRET_ACCESS_KEY` | `minioadmin` | S3/MinIO secret key |
| `S3_BUCKET_NAME` | `aiden-storage` | Default bucket name |
| `S3_REGION` | `us-east-1` | AWS region (MinIO ignores this) |
| `S3_USE_SSL` | `false` | Whether to use SSL/TLS |
| `S3_FORCE_PATH_STYLE` | `true` | Force path-style addressing (required for MinIO) |

**Legacy Fallback (Deprecated)**:
If `S3_*` vars are not set, the API falls back to `AWS_*` equivalents with a warning:
- `AWS_ENDPOINT_URL` → `S3_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID` → `S3_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY` → `S3_SECRET_ACCESS_KEY`

**Local Development Setup (PowerShell)**:

```powershell
# Set S3 env vars for local MinIO
$env:S3_ENDPOINT_URL = "http://localhost:9000"
$env:S3_ACCESS_KEY_ID = "minioadmin"
$env:S3_SECRET_ACCESS_KEY = "minioadmin"
$env:S3_BUCKET_NAME = "aiden-storage"
$env:S3_FORCE_PATH_STYLE = "true"
```

Or copy `.env.example` to `.env` which includes all defaults.

### Document Endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/documents` | POST | EDITOR+ | Upload new document |
| `/documents` | GET | VIEWER+ | List documents |
| `/documents/{id}` | GET | VIEWER+ | Get document with versions |
| `/documents/{id}/versions` | POST | EDITOR+ | Upload new version |
| `/documents/{id}/versions/{vid}/download` | GET | VIEWER+ | Download specific version |

### Upload a Document (PowerShell)

```powershell
# Get JWT token first (see Authentication section)
$headers = @{ "Authorization" = "Bearer $token" }

# Prepare multipart form data
$form = @{
    file = Get-Item -Path "contract.pdf"
}

$body = @{
    title = "Employment Contract"
    document_type = "contract"
    jurisdiction = "UAE"
    language = "en"
    confidentiality = "confidential"
}

# Upload using Invoke-RestMethod with multipart
$response = Invoke-RestMethod -Uri "http://localhost:8000/documents" `
    -Method POST `
    -Headers $headers `
    -Form @{
        file = Get-Item "contract.pdf"
        title = "Employment Contract"
        document_type = "contract"
        jurisdiction = "UAE"
        language = "en"
        confidentiality = "confidential"
    }

Write-Host "Document ID: $($response.document.id)"
Write-Host "Version ID: $($response.version.id)"
Write-Host "Version Number: $($response.version.version_number)"
```

### Upload with curl (Git Bash / WSL)

```bash
# Upload a new document
curl -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@contract.pdf" \
  -F "title=Employment Contract" \
  -F "document_type=contract" \
  -F "jurisdiction=UAE" \
  -F "language=en" \
  -F "confidentiality=confidential"

# Upload a new version
curl -X POST http://localhost:8000/documents/$DOC_ID/versions \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@contract_v2.pdf"

# Download a version
curl -O -J http://localhost:8000/documents/$DOC_ID/versions/$VERSION_ID/download \
  -H "Authorization: Bearer $TOKEN"
```

### Document Metadata Fields

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `title` | string | - | Document title |
| `document_type` | string | `contract`, `policy`, `memo`, `regulatory`, `other` | Type of document |
| `jurisdiction` | string | `UAE`, `DIFC`, `ADGM`, `KSA` | Legal jurisdiction |
| `language` | string | `en`, `ar`, `mixed` | Document language |
| `confidentiality` | string | `public`, `internal`, `confidential`, `highly_confidential` | Confidentiality level |

### Policy Enforcement at Upload

When uploading a document, the vault enforces the workspace's policy:

1. **Language Check**: Document `language` must be in `allowed_input_languages`
2. **Jurisdiction Check**: Document `jurisdiction` must be in `allowed_jurisdictions`

If the policy doesn't allow the language or jurisdiction, upload returns HTTP 403:

```json
{
  "detail": "Language 'ar' is not allowed by workspace policy. Allowed languages: ['en']"
}
```

### Example: Set Up Policy That Blocks Arabic Documents

```powershell
# Create restrictive policy
$policyBody = @{
    name = "English Only"
    config = @{
        allowed_workflows = @()
        allowed_input_languages = @("en")  # Only English
        allowed_output_languages = @("en")
        allowed_jurisdictions = @("UAE", "DIFC", "ADGM", "KSA")
        feature_flags = @{}
    }
} | ConvertTo-Json -Depth 4

$policy = Invoke-RestMethod -Uri "http://localhost:8000/policy-profiles" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $policyBody

# Attach to workspace
Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$workspaceId/policy-profile" `
    -Method POST -Headers $headers -ContentType "application/json" `
    -Body (@{ policy_profile_id = $policy.id } | ConvertTo-Json)

# Now Arabic uploads will be blocked!
```

### Storage Structure

Files are stored in MinIO with the following key structure:

```
tenants/{tenant_id}/workspaces/{workspace_id}/documents/{document_id}/versions/{version_id}/{filename}
```

### Audit Events for Document Vault

| Action | Description |
|--------|-------------|
| `document.upload` | New document created with initial version |
| `document.version.upload` | New version added to existing document |
| `document.download` | Document version downloaded |
| `document.extract.success` | Text extraction completed successfully |
| `document.extract.fail` | Text extraction failed |

## Text Extraction

The API automatically extracts text from uploaded documents for future search, citations, and analysis.

### What It Does

- **PDF Extraction**: Uses PyMuPDF (preferred) or pdfminer.six (fallback) to extract native text
- **DOCX Extraction**: Uses python-docx to extract paragraph and table text
- **Chunking**: Splits extracted text into stable chunks (~800-1200 characters) with character offsets
- **Arabic Support**: Text is stored as-is, no reshaping or bidi transformations applied

### What It Does NOT Do

- **No OCR**: Only native/embedded text is extracted (scanned PDFs will have empty text)
- **No Embeddings**: Vector search is not implemented yet (planned for future)
- **No RAG/Retrieval**: This is the foundation for future retrieval features

### Extraction Flow

1. User uploads document (PDF/DOCX)
2. Document is stored in MinIO, upload succeeds
3. Text extraction runs synchronously after upload
4. If extraction succeeds: `document_texts` and `document_chunks` records are created
5. If extraction fails: upload still succeeds, audit log records the failure

### Text Extraction Endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/documents/{id}/versions/{vid}/text` | GET | VIEWER+ | Get extracted text metadata |
| `/documents/{id}/versions/{vid}/chunks` | GET | VIEWER+ | Get text chunks with offsets |

### Get Extracted Text (PowerShell)

```powershell
# Get metadata only (default)
$text = Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId/versions/$versionId/text" `
    -Headers $headers

Write-Host "Extraction method: $($text.extraction_method)"
Write-Host "Page count: $($text.page_count)"
Write-Host "Text length: $($text.text_length) characters"

# Include full extracted text
$textFull = Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId/versions/$versionId/text?include_text=true" `
    -Headers $headers

Write-Host "Extracted text: $($textFull.extracted_text.Substring(0, 200))..."
```

### Get Document Chunks (PowerShell)

```powershell
# Get all chunks for a document version
$chunks = Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId/versions/$versionId/chunks" `
    -Headers $headers

Write-Host "Total chunks: $($chunks.chunk_count)"

foreach ($chunk in $chunks.chunks) {
    Write-Host "Chunk $($chunk.chunk_index): chars $($chunk.char_start)-$($chunk.char_end)"
    Write-Host "  Text: $($chunk.text.Substring(0, [Math]::Min(100, $chunk.text.Length)))..."
}
```

### Extraction Response Schema

**GET /documents/{id}/versions/{vid}/text**

```json
{
  "id": "uuid",
  "version_id": "uuid",
  "extraction_method": "pymupdf",
  "page_count": 5,
  "text_length": 12345,
  "created_at": "2025-01-24T...",
  "extracted_text": null
}
```

With `include_text=true`:
```json
{
  "id": "uuid",
  "version_id": "uuid",
  "extraction_method": "pymupdf",
  "page_count": 5,
  "text_length": 12345,
  "created_at": "2025-01-24T...",
  "extracted_text": "Full extracted text here..."
}
```

**GET /documents/{id}/versions/{vid}/chunks**

```json
{
  "version_id": "uuid",
  "document_id": "uuid",
  "chunk_count": 10,
  "chunks": [
    {
      "id": "uuid",
      "chunk_index": 0,
      "text": "Chunk text content...",
      "char_start": 0,
      "char_end": 1024,
      "page_start": null,
      "page_end": null
    }
  ]
}
```

### Extraction Methods

| Method | Library | Used For |
|--------|---------|----------|
| `pymupdf` | PyMuPDF (fitz) | PDF (preferred) |
| `pdfminer` | pdfminer.six | PDF (fallback) |
| `docx` | python-docx | DOCX files |
| `unsupported` | - | Other file types |

### Chunk Properties

- **Size**: ~800-1200 characters per chunk (configurable)
- **Boundaries**: Splits on paragraph/newline/sentence boundaries when possible
- **Deterministic**: Same input always produces identical chunks
- **Offsets**: `char_start` and `char_end` are character positions in full text
- **Pages**: `page_start` and `page_end` are optional (not always available)

## Hybrid Search (Embeddings + Full-Text)

The API provides hybrid search over document chunks combining semantic vector search with PostgreSQL full-text search.

### Features

- **Automatic Embedding Generation**: When documents are uploaded and extracted, embeddings are automatically generated for all chunks
- **Vector Search**: Semantic similarity search using pgvector (PostgreSQL-native cosine distance)
- **Keyword Search**: PostgreSQL full-text search (`tsvector`/`tsquery`) for English, ILIKE fallback for Arabic
- **Hybrid Ranking**: Weighted combination (60% vector, 40% keyword) with score normalization
- **Policy Enforcement**: Search respects policy constraints (allowed jurisdictions, languages)
- **Tenant Isolation**: Search results are strictly scoped to tenant/workspace

### Embedding Provider

The current implementation uses a **Deterministic Hash Embedding Provider** for development:

| Property | Value |
|----------|-------|
| Model Name | `deterministic_hash_v1` |
| Dimension | 384 |
| Deterministic | Yes (same text → same embedding) |
| Network Calls | None |
| Semantic Understanding | Limited (hash-based, not neural) |

**Important**: This provider is designed for development and testing only. For production semantic search, integrate a real embedding model (e.g., OpenAI, Sentence Transformers) by implementing the `EmbeddingProvider` interface. The provider swap is seamless - only the embedding generation changes; storage and search remain the same (pgvector).

The provider works by:
1. Tokenizing text into words and character n-grams
2. Hashing tokens to fixed buckets (dimension 384)
3. Accumulating signed contributions
4. L2 normalizing the result to unit length

### Indexing Status

Each document version tracks its indexing status:

| Field | Type | Description |
|-------|------|-------------|
| `is_indexed` | boolean | Whether embeddings have been generated for this version |
| `indexed_at` | timestamp | When the version was last indexed |
| `embedding_model` | text | Model used for embedding generation |

**Important after migration**: When migrating to new embedding storage (e.g., from binary to pgvector), existing embeddings may be lost. Run admin reindex on all documents to regenerate embeddings:

```powershell
# Reindex a specific document version
Invoke-RestMethod -Uri "http://localhost:8000/admin/reindex/$docId/$versionId?replace=true" `
    -Method POST -Headers $headers
```

By default, search only returns results from **indexed versions** (`is_indexed=True`). To include unindexed versions, use the `include_unindexed=true` parameter.

### Search Endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/search/chunks` | GET | VIEWER+ | Hybrid search over document chunks |
| `/admin/reindex/{document_id}/{version_id}` | POST | ADMIN | Regenerate embeddings for a version |

### Search Chunks (PowerShell)

```powershell
# Basic search
$results = Invoke-RestMethod -Uri "http://localhost:8000/search/chunks?q=employment contract salary" `
    -Headers $headers

Write-Host "Found $($results.total) results"
foreach ($r in $results.results) {
    Write-Host "[$($r.final_score.ToString('F3'))] $($r.document_title) - Chunk $($r.chunk_index)"
    Write-Host "  Snippet: $($r.snippet.Substring(0, [Math]::Min(100, $r.snippet.Length)))..."
}

# Search with filters
$results = Invoke-RestMethod -Uri "http://localhost:8000/search/chunks" `
    -Headers $headers `
    -Body @{
        q = "confidentiality non-disclosure"
        limit = 20
        document_type = "contract"
        jurisdiction = "UAE"
    }

# Search with limit
Invoke-RestMethod -Uri "http://localhost:8000/search/chunks?q=legal terms&limit=5" -Headers $headers

# Include unindexed versions (for debugging/testing)
Invoke-RestMethod -Uri "http://localhost:8000/search/chunks?q=legal terms&include_unindexed=true" -Headers $headers
```

### Search Response Schema

```json
{
  "query": "employment contract",
  "total": 5,
  "results": [
    {
      "chunk_id": "uuid",
      "chunk_index": 2,
      "snippet": "The Employee agrees to work...",
      "document_id": "uuid",
      "version_id": "uuid",
      "document_title": "Employment Agreement",
      "document_type": "contract",
      "jurisdiction": "UAE",
      "language": "en",
      "char_start": 1024,
      "char_end": 2048,
      "page_start": 1,
      "page_end": 1,
      "vector_score": 0.85,
      "keyword_score": 0.72,
      "final_score": 0.798
    }
  ]
}
```

### Admin Reindex (PowerShell)

```powershell
# Reindex a document version (skip existing embeddings)
Invoke-RestMethod -Uri "http://localhost:8000/admin/reindex/$docId/$versionId" `
    -Method POST -Headers $headers

# Force reindex (replace all embeddings)
Invoke-RestMethod -Uri "http://localhost:8000/admin/reindex/$docId/$versionId?replace=true" `
    -Method POST -Headers $headers
```

### Reindex Response Schema

```json
{
  "document_id": "uuid",
  "version_id": "uuid",
  "chunks_indexed": 5,
  "chunks_skipped": 0,
  "embedding_model": "deterministic_hash_v1"
}
```

### Audit Events for Search

| Action | Description |
|--------|-------------|
| `search.chunks.success` | Chunk search completed successfully |
| `search.chunks.fail` | Chunk search failed |
| `embeddings.index.success` | Embeddings generated for chunks |
| `embeddings.index.fail` | Embedding generation failed |
| `embeddings.reindex.success` | Admin reindex completed |
| `embeddings.reindex.fail` | Admin reindex failed |

### Database Schema

The hybrid search uses:

1. **document_chunk_embeddings**: Stores vector embeddings for each chunk
   - One embedding per chunk (unique constraint)
   - Linked to tenant/workspace/document/version/chunk
   - **Embedding stored as native pgvector `vector(384)` type**
   - Similarity computed in PostgreSQL using pgvector's `<=>` cosine distance operator

2. **document_chunks.text_search_vector**: Generated `tsvector` column
   - Automatically computed from chunk text
   - GIN-indexed for fast full-text search
   - Uses English configuration (`to_tsvector('english', text)`)

### Vector Search Implementation

Vector similarity is computed **inside PostgreSQL** using pgvector operators, NOT in Python:

```sql
-- pgvector cosine distance operator
SELECT *, (1 - (embedding <=> query_vector)) AS similarity
FROM document_chunk_embeddings
ORDER BY similarity DESC
LIMIT 50;
```

This ensures:
- **Efficiency**: No data transfer for similarity computation
- **Scalability**: PostgreSQL handles the heavy lifting
- **Correctness**: Native pgvector operators are optimized and tested

### Production Provider Swap

To use a real embedding model in production:

1. Implement the `EmbeddingProvider` interface:
   ```python
   class OpenAIEmbeddingProvider(EmbeddingProvider):
       @property
       def dimension(self) -> int:
           return 384  # or 1536 for text-embedding-3-small
       
       @property
       def model_name(self) -> str:
           return "openai_text-embedding-3-small"
       
       def embed_text(self, text: str) -> list[float]:
           # Call OpenAI API
           ...
   ```

2. Configure the provider in settings or dependency injection

3. Run admin reindex to regenerate embeddings

### Future Enhancements

- Add pgvector IVFFlat or HNSW index for large-scale vector search
- Implement cross-encoder reranking
- Add Arabic-specific text processing
- Citation highlighting in search results

## Global Legal Corpus (Operator-Only)

The API includes a global legal corpus feature for storing and searching baseline laws and regulations across GCC jurisdictions. This is a platform-level feature, separate from tenant/workspace documents.

### Features

- **Platform-Wide Access**: Legal instruments are globally accessible to all tenants as baseline evidence
- **Manual Ingestion Only**: No web crawlers in v0 - operators upload documents manually
- **GCC Jurisdictions**: Supports UAE, DIFC, ADGM, KSA, Oman, Bahrain, Qatar, Kuwait
- **Hybrid Search**: Same semantic + keyword search as workspace documents
- **Audit Logging**: All operations are audit logged
- **Strict Access Control**: Only platform administrators can manage the corpus

### Platform Operator Setup

To manage the global legal corpus, a user must have `is_platform_admin = true`. This is a platform-level permission separate from workspace RBAC roles.

#### Automatic Bootstrap (Recommended)

Set the `PLATFORM_ADMIN_EMAIL` environment variable to automatically designate a platform admin on startup:

```bash
# .env file
PLATFORM_ADMIN_EMAIL=operator@platform.com
```

**Behavior:**
- On startup (dev/staging): If user with this email exists, `is_platform_admin=true` is set automatically
- If user doesn't exist: A warning is logged (user is NOT auto-created)
- In production: Bootstrap is BLOCKED unless `GLOBAL_CORPUS_ENABLED_IN_PROD=true`
- All bootstrap actions are logged

This removes the need for manual SQL commands.

#### Manual Method (Database)

If you prefer manual setup:

```sql
UPDATE users SET is_platform_admin = true WHERE email = 'operator@platform.com';
```

#### Rotating Platform Admins

To rotate platform admin access:

1. Set `PLATFORM_ADMIN_EMAIL` to the new admin email
2. Restart the application
3. Revoke old admin:
   ```sql
   UPDATE users SET is_platform_admin = false WHERE email = 'old_admin@platform.com';
   ```

#### Disabling Global Corpus in Production

To completely disable global corpus management in production:

1. Ensure `GLOBAL_CORPUS_ENABLED_IN_PROD=false` (default)
2. Remove `PLATFORM_ADMIN_EMAIL` from production config
3. Revoke all platform admins via SQL

### Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GLOBAL_CORPUS_ENABLED_IN_PROD` | `false` | Enable global corpus management in production |
| `PLATFORM_ADMIN_EMAIL` | `null` | Email of user to auto-designate as platform admin on startup |

**Security**: By default, global corpus management is disabled in production. Set `GLOBAL_CORPUS_ENABLED_IN_PROD=true` after proper review.

### Global Legal Corpus Guardrails

#### Source Provenance (User Trust)

All global legal search results include explicit provenance metadata to ensure users never confuse global law with workspace documents:

| Field | Description |
|-------|-------------|
| `source_type` | Always `"global_legal"` for global corpus results |
| `source_label` | Human-readable label, e.g., "Saudi Companies Law (2022)" |
| `jurisdiction` | Jurisdiction code (required for all global legal) |
| `published_at` | Official publication date |
| `effective_at` | Effective date of the law |
| `official_source_url` | Link to official government source |

#### Policy-Aware Search (Global ≠ Unrestricted)

Global legal search respects workspace policy constraints:

- **Jurisdiction Filtering**: Results are filtered by `allowed_jurisdictions` from the workspace policy
- **Language Filtering**: Results are filtered by `allowed_input_languages` from the workspace policy

**Example**: A workspace with policy `allowed_jurisdictions: ["KSA"]` will NOT see UAE laws in global search results.

**Design Principle**: Global ≠ unrestricted. Policy is still the gate.

#### Frontend Visual Distinction

The web UI displays global legal results with:

- **"Global Law" badge**: Blue badge with jurisdiction (e.g., "Global Law — KSA")
- **Distinct styling**: Subtle blue background to differentiate from workspace documents
- **Official source links**: "View Official Source" links to government websites

### Legal Instrument Endpoints

| Endpoint | Method | Access | Description |
|----------|--------|--------|-------------|
| `/global/legal-instruments` | POST | Platform Admin | Create legal instrument |
| `/global/legal-instruments` | GET | Platform Admin | List legal instruments |
| `/global/legal-instruments/{id}` | GET | Platform Admin | Get instrument with versions |
| `/global/legal-instruments/{id}/versions` | POST | Platform Admin | Upload new version |
| `/global/legal-instruments/{id}/versions/{vid}/reindex` | POST | Platform Admin | Reindex version |

### Search Endpoint

| Endpoint | Method | Access | Description |
|----------|--------|--------|-------------|
| `/global/search/chunks` | POST | Any Authenticated User | Search global legal corpus |

### Create Legal Instrument (PowerShell)

```powershell
# Requires platform admin user with JWT token
$headers = @{ "Authorization" = "Bearer $token" }

# Create instrument with initial version
$form = @{
    jurisdiction = "UAE"
    instrument_type = "federal_law"
    title = "Federal Law No. 1 of 2024"
    title_ar = "القانون الاتحادي رقم 1 لسنة 2024"
    official_source_url = "https://example.gov.ae/law/1"
    published_at = "2024-01-15"
    effective_at = "2024-02-01"
    version_label = "v1.0"
    language = "en"
}

Invoke-RestMethod -Uri "http://localhost:8000/global/legal-instruments" `
    -Method POST -Headers $headers `
    -Form @{
        jurisdiction = "UAE"
        instrument_type = "federal_law"
        title = "Federal Law No. 1 of 2024"
        version_label = "v1.0"
        language = "en"
        file = Get-Item "law_document.pdf"
    }
```

### Search Global Corpus (PowerShell)

```powershell
# Available to any authenticated user (not just platform admins)
$searchBody = @{
    query = "employment contract termination"
    limit = 10
    jurisdiction = "UAE"
} | ConvertTo-Json

$results = Invoke-RestMethod -Uri "http://localhost:8000/global/search/chunks" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $searchBody

foreach ($r in $results.results) {
    Write-Host "[$($r.final_score.ToString('F3'))] $($r.instrument_title)"
    Write-Host "  Jurisdiction: $($r.jurisdiction) | Type: $($r.instrument_type)"
    Write-Host "  Snippet: $($r.snippet.Substring(0, [Math]::Min(100, $r.snippet.Length)))..."
}
```

### Search Response Schema

```json
{
  "query": "employment",
  "total": 5,
  "results": [
    {
      "chunk_id": "uuid",
      "chunk_index": 0,
      "snippet": "The employment provisions...",
      "instrument_id": "uuid",
      "version_id": "uuid",
      "instrument_title": "Federal Law No. 1 of 2024",
      "instrument_title_ar": "القانون الاتحادي رقم 1 لسنة 2024",
      "instrument_type": "federal_law",
      "jurisdiction": "UAE",
      "language": "en",
      "published_at": "2024-01-15",
      "effective_at": "2024-02-01",
      "official_source_url": "https://example.gov.ae/law/1",
      "char_start": 0,
      "char_end": 1024,
      "vector_score": 0.85,
      "keyword_score": 0.72,
      "final_score": 0.798,
      "source_type": "global_legal",
      "source_label": "Federal Law No. 1 of 2024 (2024)"
    }
  ]
}
```

### Jurisdiction Enum

| Value | Description |
|-------|-------------|
| `UAE` | United Arab Emirates (Federal) |
| `DIFC` | Dubai International Financial Centre |
| `ADGM` | Abu Dhabi Global Market |
| `KSA` | Kingdom of Saudi Arabia |
| `OMAN` | Sultanate of Oman |
| `BAHRAIN` | Kingdom of Bahrain |
| `QATAR` | State of Qatar |
| `KUWAIT` | State of Kuwait |

### Instrument Types

| Value | Description |
|-------|-------------|
| `law` | General law |
| `federal_law` | Federal law |
| `local_law` | Local/emirate law |
| `decree` | Decree |
| `royal_decree` | Royal decree (KSA) |
| `regulation` | Regulation |
| `ministerial_resolution` | Ministerial resolution |
| `circular` | Circular |
| `guideline` | Guideline |
| `directive` | Directive |
| `order` | Order |
| `other` | Other |

### Audit Events

| Action | Description |
|--------|-------------|
| `global_legal.create` | Legal instrument created |
| `global_legal.version.upload` | Version uploaded |
| `global_legal.reindex` | Version reindexed |
| `global_legal.search` | Global corpus searched |

### Verification Tests

Run these tests to verify Global Legal Corpus functionality:

```powershell
cd apps/api

# Full verification suite (recommended first)
.\infra\dev.ps1 verify

# Global Legal Corpus: Policy enforcement tests (deny-by-default)
uv run pytest tests/test_global_legal.py::TestPolicyEnforcement -v

# Workspace search: Provenance field tests (source_type, source_label)
uv run pytest tests/test_search.py::TestSearchProvenanceFields -v

# All global legal tests
uv run pytest tests/test_global_legal.py -v

# Platform admin bootstrap tests
uv run pytest tests/test_global_legal.py::TestPlatformAdminBootstrap -v
```

**Key Test Scenarios:**
- `test_ksa_only_workspace_cannot_retrieve_uae_laws` - Jurisdiction policy enforcement
- `test_global_search_deny_by_default_when_policy_empty` - Empty policy returns zero results
- `test_global_search_respects_allowed_input_languages` - Language policy enforcement
- `test_workspace_search_includes_source_type_and_label` - Provenance completeness

### Data Isolation

**Important**: The global legal corpus is completely separate from tenant/workspace documents:

1. **No tenant_id/workspace_id**: Legal instruments have no tenant scope
2. **Separate tables**: Uses `legal_instruments`, `legal_chunks`, etc. (not `documents`)
3. **Platform admin only**: Only users with `is_platform_admin=true` can modify
4. **Search separation**: `/global/search/chunks` only searches global corpus, `/search/chunks` only searches workspace documents

### Staging Ingestion Workflow

To ingest baseline legal corpus in staging:

1. Create a platform admin user:
   ```sql
   UPDATE users SET is_platform_admin = true WHERE email = 'ops@company.com';
   ```

2. Set environment variable:
   ```bash
   GLOBAL_CORPUS_ENABLED_IN_PROD=true  # Only if environment is 'prod'
   ```

3. Use the web UI at `/operator/legal-corpus` or API to upload documents

4. Verify indexing status via API or UI

### Safety Warnings

- **Completeness**: The global corpus does NOT claim to be complete. Always verify with official sources.
- **Currency**: Laws change. Track effective dates and update versions accordingly.
- **Provenance**: Use `official_source_url` to link to official government sources.
- **No Legal Advice**: The corpus is for information only, not legal advice.

## Contract Review Workflow (CONTRACT_REVIEW_V1)

The API includes a contract review workflow that analyzes a specific contract document and produces structured findings with citations.

### Features

- **Structured Findings**: Each finding includes title, severity, category, issue, recommendation, and citations
- **Policy Enforcement**: Requires CONTRACT_REVIEW_V1 in the workspace's allowed_workflows
- **Strict Citations**: Every finding must have valid citations to contract excerpts
- **Review Modes**: quick (20 chunks), standard (40), deep (80) for different analysis depths
- **Focus Areas**: Optionally focus on specific categories (liability, termination, payment, etc.)
- **Bilingual Support**: Findings can be generated in English or Arabic

### Enabling CONTRACT_REVIEW_V1 in Policy

To use the contract review workflow, you must enable it in your policy profile:

```powershell
# Create or update policy profile to allow CONTRACT_REVIEW_V1
$policyBody = @{
    name = "Contract Review Enabled Policy"
    config = @{
        allowed_workflows = @("CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1")
        allowed_input_languages = @("en", "ar")
        allowed_output_languages = @("en", "ar")
        allowed_jurisdictions = @("UAE", "DIFC", "ADGM", "KSA")
        feature_flags = @{}
    }
    is_default = $true
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://localhost:8000/policy-profiles" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $policyBody
```

### Calling /workflows/contract-review (PowerShell)

```powershell
# Get JWT token first (see Authentication section)
$headers = @{ "Authorization" = "Bearer $token" }

# Basic contract review request
$reviewBody = @{
    document_id = $documentId
    version_id = $versionId
    review_mode = "standard"
    output_language = "en"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/contract-review" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $reviewBody

# Display findings
Write-Host "Summary: $($result.summary)"
Write-Host ""
Write-Host "Findings:"
foreach ($finding in $result.findings) {
    Write-Host "  [$($finding.severity)] $($finding.title)"
    Write-Host "    Category: $($finding.category)"
    Write-Host "    Issue: $($finding.issue)"
    Write-Host "    Recommendation: $($finding.recommendation)"
    Write-Host "    Citations: $($finding.citations -join ', ')"
}

# Review with focus areas
$focusedRequest = @{
    document_id = $documentId
    version_id = $versionId
    review_mode = "deep"
    focus_areas = @("liability", "termination", "payment")
    output_language = "en"
} | ConvertTo-Json -Depth 3

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/contract-review" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $focusedRequest
```

### Request Schema

```json
{
  "document_id": "uuid",
  "version_id": "uuid",
  "review_mode": "standard",
  "focus_areas": ["liability", "termination", "payment"],
  "output_language": "en"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | ID of the document to review (required) |
| `version_id` | string | ID of the specific version to review (required) |
| `review_mode` | string | Review depth: "quick", "standard", "deep" (default: "standard") |
| `focus_areas` | list | Focus categories (optional): "liability", "termination", "governing_law", "payment", "ip", "confidentiality" |
| `output_language` | string | Output language: "en" or "ar" (default: "en") |

### Response Schema

```json
{
  "summary": "Contract review identified 3 findings requiring attention [1][2][3]...",
  "findings": [
    {
      "finding_id": "uuid",
      "title": "Liability Clause Review",
      "severity": "high",
      "category": "liability",
      "issue": "The liability clause limits damages to contract value [1].",
      "recommendation": "Negotiate higher liability cap [1].",
      "citations": [1],
      "evidence": [
        {
          "chunk_id": "uuid",
          "snippet": "Liability shall not exceed...",
          "char_start": 1024,
          "char_end": 1256
        }
      ]
    }
  ],
  "meta": {
    "model": "stub-v1",
    "provider": "stub",
    "evidence_chunk_count": 15,
    "request_id": "uuid",
    "output_language": "en",
    "review_mode": "standard",
    "removed_findings_count": 0,
    "strict_citations_failed": false
  },
  "insufficient_sources": false
}
```

### Strict Citation Enforcement

The contract review workflow enforces strict citation requirements:

**Rules:**

1. **Every finding must have valid citations**: Each finding must reference valid evidence indices [1] to [N].
2. **Findings without valid citations are removed**: If a finding has no valid citations, it is removed from the response.
3. **Summary must contain citations**: If the summary has no citations but findings exist, it is regenerated from finding citations.
4. **Invalid citation indices are filtered**: Citations referencing non-existent evidence (e.g., [99] when only 10 chunks exist) are ignored.

**Response Metadata:**

| Field | Type | Description |
|-------|------|-------------|
| `removed_findings_count` | int | Number of findings removed due to invalid citations |
| `strict_citations_failed` | bool | `true` if all findings were removed due to citation rules |
| `validation_warnings` | list | Warnings about removed findings and citation issues |

**Example Response with Removed Findings:**

```json
{
  "summary": "Contract review identified 2 findings [1][2].",
  "findings": [...],
  "meta": {
    "removed_findings_count": 1,
    "strict_citations_failed": false,
    "validation_warnings": [
      "Removed finding without valid citations: 'Invalid Clause'"
    ]
  }
}
```

### Role Requirement

Contract review requires **EDITOR role or higher**. VIEWERs can read documents but cannot run analysis workflows.

### Audit Events

| Action | Description |
|--------|-------------|
| `workflow.run.success` | Contract review completed successfully |
| `workflow.run.fail` | Contract review failed (policy denial, document not found, error) |

The audit log includes:
- `workflow`: "CONTRACT_REVIEW_V1"
- `document_id`: Document being reviewed
- `version_id`: Version being reviewed
- `evidence_chunk_count`: Number of chunks analyzed
- `findings_count`: Number of findings returned
- `removed_findings_count`: Findings removed due to citation issues
- `strict_citations_failed`: Whether all findings were removed

## Clause Redlines Workflow (CLAUSE_REDLINES_V1)

The API includes a clause redlines workflow that detects clauses in contracts and suggests redlines based on a static clause library.

### Features

- **Clause Detection v2**: Enhanced heuristic-based detection of 8 clause types (governing_law, termination, liability, indemnity, confidentiality, payment, ip, force_majeure)
- **Jurisdiction-Specific Templates**: Clause library with recommended text for UAE, DIFC, ADGM, KSA
- **Strict Citation Rules**: Claims about the contract must be cited; template text is clearly labeled
- **Policy Enforcement**: Requires CLAUSE_REDLINES_V1 in the workspace's allowed_workflows
- **Role Required**: EDITOR or higher

### Clause Detection v2 Improvements

The clause detection system uses deterministic heuristics (no ML or external APIs) to identify clause types. Version 2 introduces significant quality improvements:

#### 1. Heading Detection
- Detects clause headings using regex patterns (e.g., "1.2 TERMINATION", "GOVERNING LAW")
- Numbered heading patterns: `^\s*\d+(\.\d+)*\s+[A-Z]`
- Common clause title keywords boost detection score significantly
- Helps prioritize chunks that contain actual clause sections vs. passing mentions

#### 2. Neighbor Chunk Inclusion
- When selecting evidence for a clause type, includes adjacent chunks (chunk_index-1 and chunk_index+1)
- Provides better context for LLM-based redline generation
- Maximum 5 evidence chunks per clause type
- De-duplicated to avoid redundancy

#### 3. Negative Scoring
- Penalizes chunks that are unlikely to contain substantive clause content:
  - Signature blocks ("IN WITNESS WHEREOF", "By: ___")
  - Annex/Schedule/Appendix headers
  - Table of contents sections
  - Definitions sections (standalone)
  - Recitals/Whereas clauses
- These chunks are excluded from evidence selection

#### 4. Confidence Calibration
Each clause detection now includes:

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | float | Raw confidence score (0.0 to 1.0) |
| `confidence_level` | string | Calibrated level: "high", "medium", or "low" |
| `confidence_reason` | string | Human-readable explanation (e.g., "Matched heading + 3 trigger(s)") |

**Confidence Level Thresholds:**
- **high**: confidence >= 0.7
- **medium**: confidence >= 0.4
- **low**: confidence < 0.4

#### Status Semantics (v2)
The `status` field is now determined by confidence level:

| Status | Condition |
|--------|-----------|
| `found` | confidence_level is "high" or "medium" |
| `insufficient_evidence` | confidence_level is "low" but some evidence exists |
| `missing` | No evidence found at all |

**Important**: Clause detection is heuristic and best-effort. It may produce false positives/negatives on complex or unusual contracts. The confidence level and reason provide transparency into detection quality.

### Enabling CLAUSE_REDLINES_V1 in Policy

To use the clause redlines workflow, you must enable it in your policy profile:

```powershell
# Create or update policy profile to allow CLAUSE_REDLINES_V1
$policyBody = @{
    name = "Clause Redlines Enabled Policy"
    config = @{
        allowed_workflows = @("CLAUSE_REDLINES_V1", "CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1")
        allowed_input_languages = @("en", "ar")
        allowed_output_languages = @("en", "ar")
        allowed_jurisdictions = @("UAE", "DIFC", "ADGM", "KSA")
        feature_flags = @{}
    }
    is_default = $true
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://localhost:8000/policy-profiles" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $policyBody
```

### Calling /workflows/clause-redlines (PowerShell)

```powershell
# Get JWT token first (see Authentication section)
$headers = @{ "Authorization" = "Bearer $token" }

# Basic clause redlines request
$redlinesBody = @{
    document_id = $documentId
    version_id = $versionId
    jurisdiction = "UAE"
    output_language = "en"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/clause-redlines" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $redlinesBody

# Display items
Write-Host "Summary: $($result.summary)"
Write-Host ""
Write-Host "Clause Redline Items:"
foreach ($item in $result.items) {
    Write-Host "  [$($item.severity)] $($item.clause_type): $($item.status)"
    if ($item.issue) {
        Write-Host "    Issue: $($item.issue)"
    }
    if ($item.suggested_redline) {
        Write-Host "    Suggested: $($item.suggested_redline)"
    }
    Write-Host "    Citations: $($item.citations -join ', ')"
}

# Request with playbook hint and specific clause types
$focusedRequest = @{
    document_id = $documentId
    version_id = $versionId
    jurisdiction = "DIFC"
    clause_types = @("liability", "termination", "indemnity")
    playbook_hint = "Focus on DIFC-specific requirements and English law principles."
    output_language = "en"
} | ConvertTo-Json -Depth 3

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/clause-redlines" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $focusedRequest
```

### Request Schema

```json
{
  "document_id": "uuid",
  "version_id": "uuid",
  "jurisdiction": "UAE",
  "clause_types": ["governing_law", "liability", "termination"],
  "playbook_hint": "Optional guidance text",
  "output_language": "en"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | ID of the document to analyze (required) |
| `version_id` | string | ID of the specific version to analyze (required) |
| `jurisdiction` | string | Jurisdiction for templates: "UAE", "DIFC", "ADGM", "KSA" (defaults to document jurisdiction) |
| `clause_types` | list | Optional list of clause types to analyze (default: all 8 types) |
| `playbook_hint` | string | Optional hint to guide analysis (optional) |
| `output_language` | string | Output language: "en" or "ar" (default: "en") |

### Response Schema

```json
{
  "summary": "Clause analysis identified 4 items requiring attention [1][2][3]...",
  "items": [
    {
      "clause_type": "governing_law",
      "status": "found",
      "confidence": 0.85,
      "confidence_level": "high",
      "confidence_reason": "Matched heading + 3 trigger(s)",
      "issue": "The governing law clause specifies UAE jurisdiction [1].",
      "suggested_redline": "Recommended Text: This Agreement shall be governed by UAE law...",
      "rationale": "The current clause [1] is acceptable but could be more detailed.",
      "severity": "low",
      "citations": [1],
      "evidence": [
        {
          "chunk_id": "uuid",
          "snippet": "This agreement shall be governed by...",
          "char_start": 1024,
          "char_end": 1256
        }
      ]
    }
  ],
  "meta": {
    "model": "stub-v1",
    "provider": "stub",
    "evidence_chunk_count": 15,
    "request_id": "uuid",
    "output_language": "en",
    "jurisdiction": "UAE",
    "downgraded_count": 0,
    "removed_count": 0,
    "strict_citations_failed": false
  },
  "insufficient_sources": false
}
```

**New v2 fields in items:**

| Field | Type | Description |
|-------|------|-------------|
| `confidence_level` | string | Calibrated confidence: "high", "medium", or "low" |
| `confidence_reason` | string | Explanation of confidence score (e.g., "Matched heading + 2 trigger(s)") |

### Template Text vs Contract Claims

**Important distinction**:

- **Contract Claims**: Any statement about what the contract says MUST be cited with [1], [2], etc.
  - Example: "The liability clause limits damages to contract value [1]."
  
- **Template Text**: Recommended clause language from the clause library does NOT need citations.
  - These are clearly labeled with "Recommended Text:" prefix
  - Example: "Recommended Text: This Agreement shall be governed by and construed in accordance with the laws of the United Arab Emirates."

**What happens if citation rules are violated**:

1. Items with uncited contract claims are downgraded to `status="insufficient_evidence"`
2. The `downgraded_count` in meta tracks how many items were affected
3. If too many items fail citation validation, `strict_citations_failed` is set to `true`

### Clause Types Analyzed

| Clause Type | Description | Risk Triggers |
|-------------|-------------|---------------|
| `governing_law` | Jurisdiction and applicable law | "governing law", "governed by", "courts of" |
| `termination` | Termination provisions | "termination", "notice period", "breach" |
| `liability` | Liability limitations | "liability", "limitation", "shall not exceed" |
| `indemnity` | Indemnification clauses | "indemnify", "hold harmless", "defend" |
| `confidentiality` | Confidentiality obligations | "confidential", "non-disclosure", "trade secrets" |
| `payment` | Payment terms | "payment", "invoice", "net 30", "late payment" |
| `ip` | Intellectual property rights | "intellectual property", "copyright", "license" |
| `force_majeure` | Force majeure clauses | "force majeure", "act of god", "beyond control" |

### Audit Events

| Action | Description |
|--------|-------------|
| `workflow.run.success` | Clause redlines completed successfully |
| `workflow.run.fail` | Clause redlines failed (policy denial, document not found, error) |

The audit log includes:
- `workflow`: "CLAUSE_REDLINES_V1"
- `document_id`: Document being analyzed
- `version_id`: Version being analyzed
- `evidence_chunk_count`: Number of chunks analyzed
- `item_count`: Number of clause items returned
- `downgraded_count`: Items downgraded due to citation issues
- `strict_citations_failed`: Whether many items failed citation validation

## DOCX Export (Enterprise-Grade)

The API provides DOCX export capability for workflow results, generating legally-usable, auditable, and editable Microsoft Word documents.

### Features

- **Enterprise-Ready**: Professional Word documents with no external styling dependencies
- **Fully Traceable**: Every export includes LLM provider, model, prompt hash, and environment
- **Auditable**: All exports are logged in the audit trail
- **Deterministic**: Same workflow result always produces consistent document structure
- **No Re-processing**: Export only serializes existing results; no LLM calls are made

### Export Endpoints

| Endpoint | Method | Role | Description |
|----------|--------|------|-------------|
| `/exports/contract-review` | POST | VIEWER+ | Export contract review results to DOCX |
| `/exports/clause-redlines` | POST | VIEWER+ | Export clause redlines results to DOCX |

### Export Request Schema

Both endpoints accept the same structure:

```json
{
  "document_metadata": {
    "document_id": "uuid",
    "version_id": "uuid",
    "document_title": "Employment Agreement",
    "version_number": 1,
    "workspace_name": "Corporate Legal",
    "tenant_name": "Acme Corporation",
    "jurisdiction": "UAE"
  },
  "workflow_result": {
    // Complete workflow response (ContractReviewResponse or ClauseRedlinesResponse)
  }
}
```

### Exportable Statuses

Only `success` and `insufficient_sources` workflow results can be exported. Other statuses (e.g., `generation_failed`, `citation_violation`) return HTTP 400.

### DOCX Document Structure

1. **Cover Page**
   - Title ("Contract Review Memo" or "Clause Redlines Memo")
   - Document title, version, workspace, tenant
   - Jurisdiction, generated timestamp (UTC)
   - Confidentiality notice

2. **Executive Summary**
   - Workflow summary text with citations
   - Disclaimer paragraph if `insufficient_sources`

3. **Findings / Clause Analysis**
   - Contract Review: Table per finding (severity, category, issue, recommendation, citations)
   - Clause Redlines: Section per clause type (status, confidence, recommended text, citations)

4. **Citations Section**
   - Numbered list [1], [2], etc.
   - Source document name, version, chunk reference

5. **Evidence Appendix**
   - Full snippet text for each citation
   - Chunk metadata (char offsets)

6. **Traceability Footer (MANDATORY)**
   - Workflow name
   - Result status
   - LLM provider and model
   - Prompt hash
   - "Generated by Aiden.ai"
   - Environment (dev/staging/prod)

### Export Example (PowerShell)

```powershell
# Assume $result contains a ContractReviewResponse from /workflows/contract-review
$exportBody = @{
    document_metadata = @{
        document_id = $documentId
        version_id = $versionId
        document_title = "Employment Agreement"
        version_number = 1
        workspace_name = "Corporate Legal"
        tenant_name = "Acme Corp"
        jurisdiction = "UAE"
    }
    workflow_result = $result
} | ConvertTo-Json -Depth 10

$docxResponse = Invoke-WebRequest -Uri "http://localhost:8000/exports/contract-review" `
    -Method POST -Headers $headers -ContentType "application/json" `
    -Body $exportBody -OutFile "contract_review.docx"
```

### Audit Events

| Action | Description |
|--------|-------------|
| `export.contract_review.success` | Contract review DOCX export completed |
| `export.contract_review.fail` | Contract review export failed |
| `export.clause_redlines.success` | Clause redlines DOCX export completed |
| `export.clause_redlines.fail` | Clause redlines export failed |

### Legal Disclaimer

**IMPORTANT**: Exported documents contain a legal disclaimer stating:
- The document does NOT constitute legal advice
- Users should consult qualified legal counsel
- Accuracy depends on source document quality
- Aiden.ai makes no warranties regarding completeness or reliability

### Security Hardening

Export endpoints validate client-supplied payloads to prevent tampering:

1. **Evidence Chunk Validation**: All evidence `chunk_id` values in the payload are verified against the database:
   - Chunks must exist in the `document_chunks` table
   - Chunks must belong to the specified `document_id` and `version_id`
   - Chunks must belong to the caller's workspace (tenant isolation enforced)

2. **Invalid Reference Handling**: If any evidence chunk is invalid or not found:
   - HTTP 400 is returned with `error_code: "export_validation_failed"`
   - Message: "Export payload references evidence not found in this document version."

3. **Audit Logging**: All export operations include:
   - `workflow_name`: The workflow type
   - `result_status`: The workflow result status
   - `prompt_hash`: For traceability
   - `evidence_count`: Number of evidence chunks in payload
   - `invalid_reference_count`: 0 on success, >0 indicates validation failure

**Future Enhancement** (not yet implemented): Cross-check `prompt_hash` against workflow audit logs to verify the export payload matches a previously executed workflow.

### Running Export Tests

```powershell
# Run export tests
cd apps/api
uv run pytest tests/test_exports.py -v

# Run with Docker
docker compose run --rm api uv run pytest tests/test_exports.py -v
```

## Workflow Result Status (Enterprise Readiness)

All workflow responses include an explicit `meta.status` field for machine-readable outcomes:

| Status | Description |
|--------|-------------|
| `success` | Workflow completed successfully with valid output |
| `insufficient_sources` | Not enough evidence/sources for confident output |
| `policy_denied` | Request blocked by policy enforcement (HTTP 403) |
| `citation_violation` | Output reduced/failed due to strict citation enforcement |
| `validation_failed` | LLM returned invalid JSON or parse failed |
| `generation_failed` | LLM provider error or other generation failure |

### Example Response with Status

```json
{
  "answer_text": "Based on the sources [1][2]...",
  "meta": {
    "status": "success",
    "model": "gpt-4o-mini",
    "provider": "openai",
    "prompt_hash": "a1b2c3d4e5f6...",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini"
  }
}
```

### Prompt/Model Fingerprinting

Each workflow response includes fingerprinting fields for traceability:

| Field | Description |
|-------|-------------|
| `prompt_hash` | SHA256 hash of the final prompt (raw prompt NOT stored for privacy) |
| `llm_provider` | LLM provider identifier |
| `llm_model` | LLM model identifier |

These fields are also included in workflow audit logs for compliance.

## Legal Research Workflow (LEGAL_RESEARCH_V1)

The API includes a legal research workflow that retrieves relevant document chunks and generates cited answers using an LLM.

### Features

- **Cited Answers**: Every claim in the answer includes inline citations [1], [2], etc.
- **Policy Enforcement**: Requires LEGAL_RESEARCH_V1 in the workspace's allowed_workflows
- **No Hallucination**: The LLM is instructed to only cite information from provided sources
- **Bilingual Support**: Answers can be generated in English or Arabic
- **Insufficient Sources**: If fewer than 3 relevant chunks are found, returns a message instead of unreliable answer
- **Strict Citation Enforcement**: Paragraphs without citations are automatically removed (see below)

### Strict Citation Enforcement

The legal research workflow enforces strict citation requirements to ensure trustworthy, well-sourced answers:

**Rules:**

1. **Every paragraph must have citations**: Each paragraph in the answer must contain at least one valid citation marker like [1], [2], etc.
2. **Uncited paragraphs are removed**: If a paragraph has no valid citation, it is automatically stripped from the final answer.
3. **Downgrade to insufficient**: If all paragraphs are removed (or the remaining content is too short), the answer is downgraded to "Insufficient sources in your workspace to answer confidently."
4. **Footer-only citations don't count**: If citations only appear in a "References" section at the end, but paragraphs above have no inline citations, those paragraphs are removed.

**Response Metadata:**

The response `meta` object includes enforcement details:

| Field | Type | Description |
|-------|------|-------------|
| `strict_citation_enforced` | bool | Always `true` - strict enforcement is applied |
| `removed_paragraph_count` | int | Number of paragraphs removed due to missing citations |
| `strict_citations_failed` | bool | `true` if answer was downgraded due to citation rules |
| `citation_count_used` | int | Number of unique citations in the final answer |
| `validation_warnings` | list | Warnings about removed paragraphs and invalid citations |

**Example Response with Removed Paragraphs:**

```json
{
  "answer_text": "The notice period is 30 days as specified in the contract [1]. This is confirmed by the policy document [2].",
  "citations": [...],
  "meta": {
    "strict_citation_enforced": true,
    "removed_paragraph_count": 1,
    "strict_citations_failed": false,
    "citation_count_used": 2,
    "validation_warnings": [
      "Removed uncited paragraph: 'General introduction about employment law...'"
    ]
  }
}
```

**Example Downgraded Response:**

```json
{
  "answer_text": "Insufficient sources in your workspace to answer confidently.",
  "citations": [],
  "insufficient_sources": true,
  "meta": {
    "strict_citation_enforced": true,
    "removed_paragraph_count": 3,
    "strict_citations_failed": true,
    "citation_count_used": 0,
    "validation_warnings": [
      "Removed uncited paragraph: 'Based on the sources...'",
      "Removed uncited paragraph: 'The legal position...'",
      "Answer downgraded: insufficient cited content after strict enforcement"
    ]
  }
}
```

**Why Strict Enforcement?**

- **Trustworthiness**: Every statement can be traced to a source document
- **No Hallucination**: Claims without citations are filtered out
- **Professional Use**: Legal professionals need reliable, verifiable answers
- **Transparency**: The `removed_paragraph_count` shows what was filtered

### Enabling LEGAL_RESEARCH_V1 in Policy

To use the legal research workflow, you must enable it in your policy profile:

```powershell
# Create or update policy profile to allow LEGAL_RESEARCH_V1
$policyBody = @{
    name = "Research Enabled Policy"
    config = @{
        allowed_workflows = @("LEGAL_RESEARCH_V1")
        allowed_input_languages = @("en", "ar")
        allowed_output_languages = @("en", "ar")
        allowed_jurisdictions = @("UAE", "DIFC", "ADGM", "KSA")
        feature_flags = @{}
    }
    is_default = $true
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://localhost:8000/policy-profiles" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $policyBody
```

### Calling /workflows/legal-research (PowerShell)

```powershell
# Get JWT token first (see Authentication section)
$headers = @{ "Authorization" = "Bearer $token" }

# Basic research request
$researchBody = @{
    question = "What is the notice period for employment contract termination under UAE law?"
    limit = 10
    output_language = "en"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/legal-research" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $researchBody

# Display answer with citations
Write-Host "Answer: $($result.answer_text)"
Write-Host ""
Write-Host "Citations:"
foreach ($citation in $result.citations) {
    Write-Host "  [$($citation.citation_index)] $($citation.document_title) (chars $($citation.char_start)-$($citation.char_end))"
}

# Research with filters
$filteredRequest = @{
    question = "What are the confidentiality requirements?"
    limit = 15
    filters = @{
        jurisdiction = "DIFC"
        document_type = "contract"
    }
    output_language = "en"
} | ConvertTo-Json -Depth 3

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/legal-research" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $filteredRequest

# Request Arabic output
$arabicRequest = @{
    question = "What are the notice requirements?"
    output_language = "ar"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/workflows/legal-research" `
    -Method POST -Headers $headers -ContentType "application/json" -Body $arabicRequest
```

### Request Schema

```json
{
  "question": "What is the notice period for contract termination?",
  "limit": 10,
  "filters": {
    "document_type": "contract",
    "jurisdiction": "UAE",
    "language": "en"
  },
  "output_language": "en"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `question` | string | The legal question to research (required) |
| `limit` | int | Max evidence chunks to retrieve (default: 10, max: 50) |
| `filters.document_type` | string | Filter by document type (optional) |
| `filters.jurisdiction` | string | Filter by jurisdiction (optional) |
| `filters.language` | string | Filter by language (optional) |
| `output_language` | string | Output language: "en" or "ar" (default: "en") |

### Response Schema

```json
{
  "answer_text": "Based on the provided sources [1][2], the notice period is 30 days...",
  "citations": [
    {
      "citation_index": 1,
      "chunk_id": "uuid",
      "document_id": "uuid",
      "version_id": "uuid",
      "document_title": "Employment Contract",
      "char_start": 1024,
      "char_end": 2048,
      "page_start": 1,
      "page_end": 1
    }
  ],
  "evidence": [
    {
      "chunk_id": "uuid",
      "snippet": "The notice period shall be 30 days...",
      "document_title": "Employment Contract",
      "final_score": 0.85
    }
  ],
  "meta": {
    "model": "stub-v1",
    "provider": "stub",
    "chunk_count": 5,
    "request_id": "uuid",
    "output_language": "en",
    "validation_warnings": null
  },
  "insufficient_sources": false
}
```

### Insufficient Sources Behavior

If fewer than 3 relevant document chunks are found, the endpoint returns:

```json
{
  "answer_text": "Insufficient sources in your workspace to answer confidently.",
  "citations": [],
  "evidence": [],
  "insufficient_sources": true,
  "meta": {
    "model": "none",
    "provider": "none",
    "chunk_count": 0,
    "output_language": "en"
  }
}
```

This prevents the LLM from generating unreliable answers when there isn't enough evidence.

### LLM Provider Configuration (Provider Relay)

The API implements an **LLM Provider Relay** that intelligently selects the appropriate LLM backend based on configuration and environment. This provides a safe switching mechanism with clear UX signals and deterministic fallbacks.

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `stub` | Provider: "stub" (testing) or "openai" |
| `LLM_MODEL` | (provider default) | Model name (e.g., "gpt-4o-mini") |
| `LLM_API_KEY` | (none) | API key (required for OpenAI) |
| `ENVIRONMENT` | `dev` | Affects fallback behavior |

#### Provider Relay Behavior Matrix

| ENVIRONMENT | LLM_PROVIDER | LLM_API_KEY | Result |
|-------------|--------------|-------------|--------|
| any | `stub` | any | StubLLMProvider (always) |
| any | `openai` | set | OpenAILLMProvider |
| `dev` | `openai` | missing | **Falls back to Stub** with loud warning |
| `staging` | `openai` | missing | **STARTUP ERROR** (hard fail) |
| `prod` | `openai` | missing | **STARTUP ERROR** (hard fail) |
| any | unknown | any | **STARTUP ERROR** (config error) |

#### Checking LLM Status

In development, you can check the active LLM provider:

```powershell
# Via API endpoint (dev only)
Invoke-RestMethod -Uri "http://localhost:8000/llm/status"

# Via dev script
.\infra\dev.ps1 llm-status
```

Response example:
```json
{
  "provider": "stub",
  "model": "stub-v1",
  "configured_provider": "openai",
  "api_key_set": false,
  "environment": "dev",
  "is_fallback": true
}
```

#### Stub Provider

The default `stub` provider returns deterministic output without making external API calls:

- Returns answers with citations [1], [2], etc. based on provided evidence
- Produces consistent output for the same input
- Never makes network calls
- Suitable for testing and development

**When using Stub provider, the web UI displays a banner:**
> "Demo mode: Using Stub LLM (generic answers). Configure OpenAI to enable real outputs."

#### Enabling OpenAI

To use OpenAI for real LLM outputs:

```powershell
# PowerShell
$env:LLM_PROVIDER = "openai"
$env:LLM_MODEL = "gpt-4o-mini"
$env:LLM_API_KEY = "sk-your-api-key"
```

Or in `.env`:
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-your-api-key
```

#### Why This Design?

1. **Safe by default**: Stub provider never makes external calls, tests are deterministic
2. **No silent failures**: Missing API key in prod causes loud startup error, not silent fallback
3. **Dev-friendly**: In dev, missing key falls back to stub with clear warning logs
4. **Obvious UX**: Frontend shows banner when using stub, no confusion about output quality

**Important**: Tests always use the stub provider and never make external API calls.

### Audit Events

| Action | Description |
|--------|-------------|
| `workflow.run.success` | Research completed successfully |
| `workflow.run.fail` | Research failed (policy denial, error, etc.) |

The audit log includes:
- `workflow`: "LEGAL_RESEARCH_V1"
- `question_hash`: SHA256 hash of the question (not the raw question for privacy)
- `chunk_count`: Number of evidence chunks retrieved
- `model`/`provider`: LLM used
- `insufficient_sources`: Whether the answer was based on insufficient evidence

### Policy Constraints

The research workflow respects policy constraints:

1. **Workflow Allowlist**: LEGAL_RESEARCH_V1 must be in `allowed_workflows`
2. **Jurisdiction Filter**: Requested jurisdiction must be in `allowed_jurisdictions`
3. **Language Filter**: Requested language must be in `allowed_input_languages`
4. **Output Language**: Requested output language must be in `allowed_output_languages`

If any constraint is violated, the endpoint returns HTTP 403.

## Example API Requests (PowerShell)

### Complete Bootstrap + JWT Workflow Example

```powershell
# Step 1: Bootstrap a new tenant
$bootstrap = @{
    name = "Law Firm LLC"
    primary_jurisdiction = "DIFC"
    data_residency_policy = "UAE"
    bootstrap = @{
        admin_user = @{ email = "partner@lawfirm.com"; full_name = "Senior Partner" }
        workspace = @{ name = "Corporate"; workspace_type = "LAW_FIRM"; jurisdiction_profile = "DIFC_DEFAULT"; default_language = "en" }
    }
} | ConvertTo-Json -Depth 3

$tenant = Invoke-RestMethod -Uri "http://localhost:8000/tenants" -Method POST -ContentType "application/json" -Body $bootstrap

# Step 2: Get JWT token
$loginBody = @{
    tenant_id = $tenant.tenant_id
    workspace_id = $tenant.workspace_id
    email = "partner@lawfirm.com"
} | ConvertTo-Json

$auth = Invoke-RestMethod -Uri "http://localhost:8000/auth/dev-login" -Method POST -ContentType "application/json" -Body $loginBody
$headers = @{ "Authorization" = "Bearer $($auth.access_token)" }

# Step 3: Check current user
$me = Invoke-RestMethod -Uri "http://localhost:8000/auth/me" -Headers $headers
Write-Host "Logged in as: $($me.email) with role: $($me.role)"

# Step 4: Create another user
$newUser = Invoke-RestMethod -Uri "http://localhost:8000/tenants/$($tenant.tenant_id)/users" `
    -Method POST -Headers $headers -ContentType "application/json" `
    -Body (@{ email = "associate@lawfirm.com"; full_name = "Associate" } | ConvertTo-Json)

# Step 5: Add user to workspace with EDITOR role
Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$($tenant.workspace_id)/memberships" `
    -Method POST -Headers $headers -ContentType "application/json" `
    -Body (@{ user_id = $newUser.id; role = "EDITOR" } | ConvertTo-Json)

# Step 6: Create a second workspace
$newWorkspace = Invoke-RestMethod -Uri "http://localhost:8000/tenants/$($tenant.tenant_id)/workspaces" `
    -Method POST -Headers $headers -ContentType "application/json" `
    -Body (@{ name = "Litigation"; workspace_type = "LAW_FIRM"; jurisdiction_profile = "DIFC_DEFAULT"; default_language = "en" } | ConvertTo-Json)

Write-Host "Created workspace: $($newWorkspace.name) with ID: $($newWorkspace.id)"

# Step 7: Login as the new user for the new workspace
# First, add admin to new workspace
Invoke-RestMethod -Uri "http://localhost:8000/workspaces/$($newWorkspace.id)/memberships" `
    -Method POST -Headers $headers -ContentType "application/json" `
    -Body (@{ user_id = $newUser.id; role = "EDITOR" } | ConvertTo-Json)

# Get token for new user in new workspace
$newUserLogin = @{
    tenant_id = $tenant.tenant_id
    workspace_id = $newWorkspace.id
    email = "associate@lawfirm.com"
} | ConvertTo-Json

$newUserAuth = Invoke-RestMethod -Uri "http://localhost:8000/auth/dev-login" -Method POST -ContentType "application/json" -Body $newUserLogin
$newUserHeaders = @{ "Authorization" = "Bearer $($newUserAuth.access_token)" }

$newUserMe = Invoke-RestMethod -Uri "http://localhost:8000/auth/me" -Headers $newUserHeaders
Write-Host "Associate logged in with role: $($newUserMe.role) in workspace: $($newWorkspace.name)"
```

### Create Tenant Without Bootstrap

```powershell
$body = @{
    name = "Simple Tenant"
    primary_jurisdiction = "KSA"
    data_residency_policy = "KSA"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/tenants" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**Note**: Without bootstrap, you'll need to manually create users, workspaces, and memberships via direct database access or additional API development.

## Using curl (Git Bash / WSL)

### Bootstrap Tenant

```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "primary_jurisdiction": "UAE",
    "data_residency_policy": "UAE",
    "bootstrap": {
      "admin_user": {"email": "admin@acme.com", "full_name": "Admin"},
      "workspace": {"name": "Main", "workspace_type": "IN_HOUSE", "jurisdiction_profile": "UAE_DEFAULT", "default_language": "en"}
    }
  }'
```

### Subsequent Calls

```bash
# Using the IDs from bootstrap response
TENANT_ID="your-tenant-uuid"
WORKSPACE_ID="your-workspace-uuid"
USER_ID="your-admin-uuid"

# List workspaces
curl http://localhost:8000/tenants/$TENANT_ID/workspaces \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "X-User-Id: $USER_ID"

# List memberships
curl http://localhost:8000/workspaces/$WORKSPACE_ID/memberships \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "X-Workspace-Id: $WORKSPACE_ID" \
  -H "X-User-Id: $USER_ID"

# Create new user (ADMIN only)
curl -X POST http://localhost:8000/tenants/$TENANT_ID/users \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "X-Workspace-Id: $WORKSPACE_ID" \
  -H "X-User-Id: $USER_ID" \
  -d '{"email": "newuser@acme.com", "full_name": "New User"}'
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Missing or invalid request data (UUID format, missing fields) |
| 401 | Authentication failed (missing token, invalid token, expired token, invalid credentials) |
| 403 | Access denied (tenant/workspace mismatch, insufficient role, user not in tenant, inactive user, not a workspace member) |
| 404 | Resource not found (tenant, workspace, user) |
| 409 | Conflict (duplicate name/email) |

## Request Context (Dev Auth)

The centralized `RequestContext` provides:

```python
@dataclass
class RequestContext:
    tenant: Tenant      # Always present for protected routes
    user: User          # Always present for protected routes
    workspace: Workspace | None  # Present for workspace-scoped routes
    membership: WorkspaceMembership | None  # Present for workspace-scoped routes
    
    @property
    def role(self) -> str | None:
        """User's role in current workspace"""
    
    def has_role(self, minimum_role: str) -> bool:
        """Check if user has at least the specified role"""
```

Use `require_admin()`, `require_editor()`, or `require_viewer()` dependencies for role enforcement.
