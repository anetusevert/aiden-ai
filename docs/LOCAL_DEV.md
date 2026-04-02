# Local Development Guide

This guide walks you through setting up Aiden.ai for local development on Windows with Docker Desktop.

## Prerequisites

### Required Software

1. **Docker Desktop for Windows**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Ensure WSL2 backend is enabled (recommended)
   - After installation, verify: `docker --version` and `docker compose version`

2. **Git for Windows**
   - Download from: https://git-scm.com/download/win

### Optional (for development outside Docker)

- **Python 3.12+** with [uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Node.js 20+** with pnpm (via corepack, see below)

## Quick Start

### 1. Clone the Repository

```powershell
git clone <repository-url>
cd "005 - Aiden.ai"
```

### 2. One-Command Verification (Recommended)

The fastest way to verify everything works:

```powershell
.\infra\dev.ps1 verify
```

This command will:
- Create `.env` from `.env.example` if needed
- Build and start all Docker services
- Wait for API and Web to be healthy
- Run API tests
- Run linters
- Print a clear PASS/FAIL summary

### 3. Manual Setup (Alternative)

```powershell
# Copy the example environment file
Copy-Item .env.example .env

# Start all services
.\infra\dev.ps1 up

# Check service status
docker compose ps

# Check API health
Invoke-RestMethod http://localhost:8000/health
```

## Generating Lockfiles

After your first successful build, generate lockfiles for reproducible builds:

```powershell
# Generate both lockfiles
.\infra\dev.ps1 lock

# Or individually:
.\infra\dev.ps1 lock-api   # generates apps/api/uv.lock
.\infra\dev.ps1 lock-web   # generates apps/web/pnpm-lock.yaml
```

**Important:** Commit these lockfiles to version control:
- `apps/api/uv.lock`
- `apps/web/pnpm-lock.yaml`

## Accessing Services

| Service       | URL                          | Credentials              |
|---------------|------------------------------|--------------------------|
| API           | http://localhost:8000        | -                        |
| API Docs      | http://localhost:8000/docs   | -                        |
| Web           | http://localhost:3000        | -                        |
| MinIO Console | http://localhost:9001        | minioadmin / minioadmin  |
| PostgreSQL    | localhost:5432               | aiden / aiden_dev_password |
| Redis         | localhost:6379               | -                        |

## Development Commands

### Using PowerShell

```powershell
# Verification
.\infra\dev.ps1 verify      # Full verification suite
.\infra\dev.ps1 cors-check  # Verify CORS headers for local dev

# Service management
.\infra\dev.ps1 up          # Start all services
.\infra\dev.ps1 down        # Stop all services
.\infra\dev.ps1 logs        # View logs (all services)
.\infra\dev.ps1 logs-api    # View API logs only
.\infra\dev.ps1 logs-web    # View Web logs only

# HTTPS Proxy (same-origin mode)
.\infra\dev.ps1 proxy-up    # Start HTTPS proxy at https://localhost
.\infra\dev.ps1 proxy-check # Verify proxy works (web, API, cookies)
.\infra\dev.ps1 proxy-down  # Stop proxy services
.\infra\dev.ps1 proxy-logs  # View Caddy proxy logs

# Testing
.\infra\dev.ps1 api-test    # Run API tests (pytest)
.\infra\dev.ps1 web-test    # Run Web tests

# Code quality
.\infra\dev.ps1 lint        # Run linters (ruff + eslint)
.\infra\dev.ps1 format      # Format code (ruff + prettier)
.\infra\dev.ps1 typecheck   # Run type checking (mypy + tsc)

# Lockfiles
.\infra\dev.ps1 lock        # Generate all lockfiles
.\infra\dev.ps1 lock-api    # Generate uv.lock
.\infra\dev.ps1 lock-web    # Generate pnpm-lock.yaml

# Cleanup
.\infra\dev.ps1 clean       # Stop services and remove volumes
```

### Using Make (Linux/macOS/WSL)

```bash
make up          # Start services
make down        # Stop services
make logs        # View logs
make api-test    # Run API tests
make web-test    # Run Web tests
make lint        # Run linters
make format      # Format code
make typecheck   # Type checking
make clean       # Clean up
```

## Hot Reload

Both the API and Web services support hot reload:

- **API**: Changes to files in `apps/api/` are automatically detected by uvicorn
- **Web**: Changes to files in `apps/web/` trigger Next.js fast refresh

## MinIO (S3-Compatible Storage)

### Bucket Initialization

The `minio-init` service automatically creates the required bucket (`aiden-storage`) on startup. This process:
- Waits for MinIO to be ready (with retries and backoff)
- Creates the bucket if it doesn't exist (idempotent)
- Sets public download policy for the bucket

### Verifying MinIO Setup

1. Open MinIO Console: http://localhost:9001
2. Login with `minioadmin` / `minioadmin`
3. Navigate to "Buckets" to see `aiden-storage`

### Manual Bucket Creation (if needed)

If the bucket wasn't created automatically:

```powershell
# Check minio-init logs
docker compose logs minio-init

# Create bucket manually via MinIO Console
# Or restart the init container:
docker compose up -d minio-init
```

## API URL Configuration

The web app supports dual API URLs for proper Docker networking:

| Environment Variable       | Purpose                    | Default Value           |
|---------------------------|----------------------------|-------------------------|
| `NEXT_PUBLIC_API_BASE_URL`| Browser/client requests    | http://localhost:8000   |
| `API_INTERNAL_BASE_URL`   | Server-side (SSR) requests | http://api:8000         |

- **Client-side**: Uses `NEXT_PUBLIC_API_BASE_URL` (accessible from your browser)
- **Server-side**: Uses `API_INTERNAL_BASE_URL` (Docker internal network)

## Running Services Outside Docker

### API (Python/FastAPI)

```powershell
cd apps/api

# Install uv if not installed
# See: https://docs.astral.sh/uv/getting-started/installation/

# Create virtual environment and install dependencies
uv sync

# Run the API
uv run uvicorn src.main:app --reload --port 8000
```

### Web (Next.js)

```powershell
cd apps/web

# Enable pnpm via corepack (Node 16+)
corepack enable
corepack prepare pnpm@latest --activate
pnpm -v

# Install dependencies
pnpm install

# Run the development server
pnpm dev
```

> **Note:** If corepack is unavailable, use the [pnpm standalone installer](https://pnpm.io/installation).

Note: When running outside Docker, both `NEXT_PUBLIC_API_BASE_URL` and `API_INTERNAL_BASE_URL` should point to `http://localhost:8000`.

## Troubleshooting

### CORS Errors (Browser Blocking Requests)

If you see errors like "No 'Access-Control-Allow-Origin' header" in the browser console:

**Quick Check:**

```powershell
.\infra\dev.ps1 cors-check
```

This command will:
1. Ensure the API is running
2. Verify the health endpoint responds
3. Send a CORS preflight request and verify headers

**Manual Verification:**

```powershell
# Check health
Invoke-RestMethod http://localhost:8000/health

# Check CORS headers with preflight request
$headers = @{
    "Origin" = "http://localhost:3000"
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "content-type,authorization"
}
$response = Invoke-WebRequest -Uri "http://localhost:8000/tenants" -Method Options -Headers $headers
$response.Headers["Access-Control-Allow-Origin"]
```

**Common Fixes:**

1. **Check CORS_ORIGINS in .env:**
   ```
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   ```

2. **Restart the API after changing .env:**
   ```powershell
   docker compose restart api
   ```

3. **Verify the setting was applied:**
   ```powershell
   docker compose exec api env | Select-String CORS
   ```

### Docker Desktop Not Starting

1. Ensure virtualization is enabled in BIOS
2. Ensure WSL2 is installed: `wsl --install`
3. Restart Docker Desktop

### Port Already in Use

```powershell
# Find process using port (e.g., 8000)
netstat -ano | findstr :8000

# Kill process by PID
taskkill /PID <pid> /F
```

### Container Build Failures

```powershell
# Clean up and rebuild
docker compose down -v
docker system prune -f
docker compose up -d --build
```

### Verification Fails

If `.\infra\dev.ps1 verify` fails:

1. Check which step failed in the summary
2. View detailed logs: `.\infra\dev.ps1 logs`
3. For API issues: `.\infra\dev.ps1 logs-api`
4. For Web issues: `.\infra\dev.ps1 logs-web`

### API Cannot Connect to Database

1. Check if PostgreSQL container is healthy: `docker compose ps`
2. Check PostgreSQL logs: `docker compose logs postgres`
3. Ensure environment variables are correctly set

### MinIO Bucket Not Created

1. Check MinIO init logs: `docker compose logs minio-init`
2. Verify MinIO is healthy: `docker compose ps`
3. Manually create bucket via MinIO Console: http://localhost:9001

## Project Structure

```
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── src/             # Source code
│   │   ├── tests/           # Tests
│   │   ├── Dockerfile
│   │   ├── pyproject.toml   # Dependencies (uv)
│   │   └── uv.lock          # Lockfile (commit this!)
│   └── web/                 # Next.js frontend
│       ├── src/
│       │   ├── app/         # Next.js app router
│       │   └── lib/         # Shared utilities (api.ts)
│       ├── Dockerfile
│       ├── package.json     # Dependencies (pnpm)
│       └── pnpm-lock.yaml   # Lockfile (commit this!)
├── infra/
│   └── dev.ps1              # PowerShell dev script
├── docs/
│   └── LOCAL_DEV.md         # This file
├── .github/
│   └── workflows/           # CI/CD
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

## Establishing Baseline (Required Before Feature Development)

Before starting any feature development, you **must** establish a verified baseline:

### Step 1: Run Verification

```powershell
.\infra\dev.ps1 verify
```

This must exit with **ALL CHECKS PASSED**. If any check fails, resolve the issue before continuing.

### Step 2: Generate Lockfiles

```powershell
.\infra\dev.ps1 lock
```

This generates:
- `apps/api/uv.lock` (Python dependencies)
- `apps/web/pnpm-lock.yaml` (Node dependencies)

### Step 3: Commit Lockfiles

```powershell
# Verify files exist
Test-Path apps/api/uv.lock
Test-Path apps/web/pnpm-lock.yaml

# Stage and commit
git add apps/api/uv.lock apps/web/pnpm-lock.yaml
git commit -m "chore: add baseline lockfiles"
```

### Baseline Confirmation

Your baseline is confirmed when:
- `.\infra\dev.ps1 verify` passes all checks
- Both lockfiles exist and are committed
- Services are running (API at :8000, Web at :3000, MinIO at :9001)

**Only after baseline is confirmed should you proceed to feature development.**

## HTTPS Local Development (Caddy Proxy)

For testing Secure cookies and same-origin configuration locally, use the Caddy reverse proxy.

### Starting the HTTPS Proxy Stack

```powershell
# Start the full stack with Caddy HTTPS proxy
.\infra\dev.ps1 proxy-up

# Verify everything works
.\infra\dev.ps1 proxy-check
```

### Accessing Services via HTTPS

| Service       | URL                              |
|---------------|----------------------------------|
| Web (HTTPS)   | https://localhost                |
| API (HTTPS)   | https://localhost/api            |
| API Health    | https://localhost/api/health     |
| API Docs      | https://localhost/api/docs       |

### Certificate Warning

On first access, your browser will show a certificate warning because Caddy uses a self-signed certificate for localhost. This is expected for local development.

**To proceed:**
1. Click "Advanced" or "Show Details"
2. Click "Proceed to localhost (unsafe)" or "Accept the Risk and Continue"

### Trusting Caddy's Local CA (Optional)

For a smoother experience without certificate warnings, you can trust Caddy's local CA:

**Windows (PowerShell as Administrator):**

```powershell
# Find the Caddy data volume
docker volume inspect aiden-ai_caddy_data

# The CA certificate is at: <volume_path>/caddy/pki/authorities/local/root.crt
# Copy it out and install:

# 1. Copy the cert from container
docker cp aiden-caddy:/data/caddy/pki/authorities/local/root.crt C:\Temp\caddy-root.crt

# 2. Open Certificate Manager
certmgr.msc

# 3. Navigate to: Trusted Root Certification Authorities > Certificates
# 4. Right-click > All Tasks > Import
# 5. Import C:\Temp\caddy-root.crt
# 6. Restart browser
```

### Same-Origin Mode Benefits

When running behind the Caddy proxy:

- **No CORS issues**: Web and API are on the same origin (https://localhost)
- **SameSite=Lax works**: Cookies don't need SameSite=None
- **Secure cookies**: Can test with `COOKIE_SECURE=true`
- **Production-like**: Mirrors how staging/prod will be configured

### Testing Secure Cookies

To test Secure cookie behavior under local TLS:

```powershell
# Set in .env or environment
$env:COOKIE_SECURE="true"

# Restart proxy stack
.\infra\dev.ps1 proxy-down
.\infra\dev.ps1 proxy-up

# Verify cookies have Secure flag
.\infra\dev.ps1 proxy-check
```

### Proxy Stack Architecture

```
Browser → https://localhost:443 → Caddy
                                    ├── / → web-proxy:3000 (Next.js)
                                    └── /api/* → api-proxy:8000 (FastAPI)
```

- `web-proxy`: Next.js configured for same-origin mode (no NEXT_PUBLIC_API_BASE_URL)
- `api-proxy`: FastAPI configured with API_ROOT_PATH=/api
- `caddy`: TLS termination and routing

### Stopping the Proxy

```powershell
.\infra\dev.ps1 proxy-down
```

### Logs

```powershell
# Caddy logs
.\infra\dev.ps1 proxy-logs

# All proxy services
docker compose --profile proxy logs -f
```

## Next Steps

After establishing baseline:

1. Explore the API documentation at http://localhost:8000/docs
2. Check the web application at http://localhost:3000
3. For HTTPS testing, use: `.\infra\dev.ps1 proxy-up`
4. Start building features!

## Related Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [End-User Review Manual](REVIEW_MANUAL.md) | Legal users, reviewers | How to use Aiden.ai features |
| [Operations Runbook](OPS_RUNBOOK.md) | Engineers, DevOps | Troubleshooting and operations |
| [Production Readiness Gate](PRODUCTION_READINESS.md) | Legal Ops, IT, Security, Procurement | Enterprise deployment readiness assessment |
