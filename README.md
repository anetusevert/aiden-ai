# Aiden.ai

AI-powered application built as a mono-repo with FastAPI backend and Next.js frontend.

## Baseline Checkpoint (Before Core Domain Work)

Before starting any domain logic, database migrations, or feature development, you **MUST** complete these steps in order:

```powershell
# 1. Run full verification (must pass all checks)
.\infra\dev.ps1 verify

# 2. Generate lockfiles
.\infra\dev.ps1 lock

# 3. Verify lockfiles were created
Test-Path apps/api/uv.lock        # Should return True
Test-Path apps/web/pnpm-lock.yaml # Should return True

# 4. Commit lockfiles to version control
git add apps/api/uv.lock apps/web/pnpm-lock.yaml
git commit -m "chore: add baseline lockfiles"
```

**Do NOT proceed to feature development until:**
- `verify` exits with code 0 (all checks pass)
- Both lockfiles exist and are committed
- Services are running and accessible

## Project Structure

```
├── apps/
│   ├── api/          # FastAPI Python backend
│   └── web/          # Next.js TypeScript frontend
├── infra/            # Docker Compose and dev scripts
├── docs/             # Documentation
└── .github/          # GitHub Actions workflows
```

## Quick Start

See [docs/LOCAL_DEV.md](docs/LOCAL_DEV.md) for detailed setup instructions.

### Prerequisites

- Docker Desktop (with WSL2 on Windows)
- Git

### One-Command Verification

```powershell
# Run full verification (builds, waits for health, tests, lints)
.\infra\dev.ps1 verify
```

### Manual Setup

```powershell
# Copy environment file
Copy-Item .env.example .env

# Start all services
.\infra\dev.ps1 up

# View logs
.\infra\dev.ps1 logs
```

- **API**: http://localhost:8000
- **Web**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

### HTTPS Mode (Same-Origin)

For testing Secure cookies and same-origin configuration:

```powershell
# Start with Caddy HTTPS proxy
.\infra\dev.ps1 proxy-up

# Verify
.\infra\dev.ps1 proxy-check
```

- **Web (HTTPS)**: https://localhost
- **API (HTTPS)**: https://localhost/api

## Generating Lockfiles

After the first successful build, generate and commit lockfiles:

```powershell
# Generate both uv.lock and pnpm-lock.yaml
.\infra\dev.ps1 lock

# Or generate individually:
.\infra\dev.ps1 lock-api   # uv.lock
.\infra\dev.ps1 lock-web   # pnpm-lock.yaml
```

**Important:** Commit `apps/api/uv.lock` and `apps/web/pnpm-lock.yaml` to version control for reproducible builds.

## Development Commands

### Using PowerShell (Windows)

```powershell
.\infra\dev.ps1 up          # Start services
.\infra\dev.ps1 down        # Stop services
.\infra\dev.ps1 verify      # Full verification suite
.\infra\dev.ps1 cors-check  # Verify CORS for browser requests
.\infra\dev.ps1 proxy-up    # Start HTTPS proxy (https://localhost)
.\infra\dev.ps1 proxy-check # Verify HTTPS proxy works
.\infra\dev.ps1 logs        # View logs
.\infra\dev.ps1 api-test    # Run API tests
.\infra\dev.ps1 web-test    # Run web tests
.\infra\dev.ps1 lint        # Run linters
.\infra\dev.ps1 format      # Format code
.\infra\dev.ps1 typecheck   # Run type checking
.\infra\dev.ps1 lock        # Generate lockfiles
```

### Using Make (Linux/macOS/WSL)

```bash
make up          # Start services
make down        # Stop services
make logs        # View logs
make api-test    # Run API tests
make web-test    # Run web tests
make lint        # Run linters
make format      # Format code
make typecheck   # Run type checking
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, uv
- **Frontend**: TypeScript, Next.js 14, React 18
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Storage**: MinIO (S3-compatible)
- **Tooling**: ruff, mypy, pytest, eslint, prettier

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [Local Development Guide](docs/LOCAL_DEV.md) | Developers | Setup and development workflow |
| [End-User Review Manual](docs/REVIEW_MANUAL.md) | Legal users, reviewers | How to use Aiden.ai features |
| [Operations Runbook](docs/OPS_RUNBOOK.md) | Engineers, DevOps | Troubleshooting and operations |
| [Production Readiness Gate](docs/PRODUCTION_READINESS.md) | Legal Ops, IT, Security, Procurement | Enterprise deployment readiness assessment |

## License

Proprietary - All rights reserved.
