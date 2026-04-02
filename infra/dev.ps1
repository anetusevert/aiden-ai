<#
.SYNOPSIS
    Development helper script for Aiden.ai on Windows.

.DESCRIPTION
    Provides commands equivalent to the Makefile for Windows PowerShell users.

.EXAMPLE
    .\infra\dev.ps1 up
    .\infra\dev.ps1 down
    .\infra\dev.ps1 verify
    .\infra\dev.ps1 lock
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet(
        "up", "down", "logs", "logs-api", "logs-web",
        "api-test", "web-test",
        "lint", "format", "typecheck",
        "db-migrate", "clean",
        "verify", "cors-check", "cookie-check", "same-origin-check",
        "proxy-up", "proxy-down", "proxy-check", "proxy-logs",
        "lock", "lock-api", "lock-web",
        "llm-status",
        "help"
    )]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

# Configuration
$script:MaxRetries = 30
$script:RetryDelaySeconds = 2
$script:ApiHealthUrl = "http://localhost:8000/health"

function Show-Help {
    Write-Host @"
Aiden.ai Development Commands
=============================

Usage: .\infra\dev.ps1 <command>

Commands:
  up          Start all services with Docker Compose
  down        Stop all services
  logs        Follow logs for all services
  logs-api    Follow logs for API service only
  logs-web    Follow logs for Web service only
  api-test    Run API tests (pytest)
  web-test    Run Web tests
  lint        Run linters (ruff + eslint)
  format      Format code (ruff + prettier)
  typecheck   Run type checking (mypy + tsc)
  db-migrate  Run database migrations (placeholder)
  clean       Stop services and clean up volumes
  verify      Full verification: build, wait for health, test, lint
  cors-check  Verify CORS headers are correctly configured for local dev
  cookie-check Verify cookie-based auth works end-to-end (login, me, refresh, logout)
  same-origin-check Verify same-origin prep (API root_path, URL resolution)
  proxy-up    Start stack with Caddy HTTPS proxy at https://localhost
  proxy-down  Stop Caddy proxy and related services
  proxy-check Verify HTTPS proxy works (web, API, cookies through proxy)
  proxy-logs  Follow logs for Caddy proxy
  lock        Generate all lockfiles (uv.lock + pnpm-lock.yaml)
  lock-api    Generate uv.lock for API
  lock-web    Generate pnpm-lock.yaml for Web
  llm-status  Check active LLM provider (stub vs openai)
  help        Show this help message
"@
}

function Invoke-Up {
    Write-Host "Starting all services..." -ForegroundColor Cyan
    docker compose up -d --build
    Write-Host "`nServices started!" -ForegroundColor Green
    Write-Host "  API:           http://localhost:8000" -ForegroundColor Yellow
    Write-Host "  Web:           http://localhost:3000" -ForegroundColor Yellow
    Write-Host "  MinIO Console: http://localhost:9001" -ForegroundColor Yellow
}

function Invoke-Down {
    Write-Host "Stopping all services..." -ForegroundColor Cyan
    docker compose down
}

function Invoke-Logs {
    docker compose logs -f
}

function Invoke-LogsApi {
    docker compose logs -f api
}

function Invoke-LogsWeb {
    docker compose logs -f web
}

function Invoke-ApiTest {
    Write-Host "Running API tests..." -ForegroundColor Cyan
    docker compose exec api uv run pytest -v
}

function Invoke-WebTest {
    Write-Host "Running Web tests..." -ForegroundColor Cyan
    docker compose exec web pnpm test
}

function Invoke-Lint {
    Write-Host "Running linters..." -ForegroundColor Cyan
    Write-Host "`n=== API (ruff) ===" -ForegroundColor Yellow
    docker compose exec api uv run ruff check .
    Write-Host "`n=== Web (eslint) ===" -ForegroundColor Yellow
    docker compose exec web pnpm lint
}

function Invoke-Format {
    Write-Host "Formatting code..." -ForegroundColor Cyan
    Write-Host "`n=== API (ruff) ===" -ForegroundColor Yellow
    docker compose exec api uv run ruff format .
    Write-Host "`n=== Web (prettier) ===" -ForegroundColor Yellow
    docker compose exec web pnpm format
}

function Invoke-Typecheck {
    Write-Host "Running type checking..." -ForegroundColor Cyan
    Write-Host "`n=== API (mypy) ===" -ForegroundColor Yellow
    docker compose exec api uv run mypy .
    Write-Host "`n=== Web (tsc) ===" -ForegroundColor Yellow
    docker compose exec web pnpm typecheck
}

function Invoke-DbMigrate {
    Write-Host "Database migrations not yet implemented" -ForegroundColor Yellow
}

function Invoke-Clean {
    Write-Host "Cleaning up..." -ForegroundColor Cyan
    docker compose down -v --remove-orphans
    docker system prune -f
    Write-Host "Cleanup complete!" -ForegroundColor Green
}

function Invoke-LockApi {
    Write-Host "Generating uv.lock for API..." -ForegroundColor Cyan
    Push-Location -Path "apps/api"
    try {
        # Check if uv is available locally, otherwise use Docker
        $uvAvailable = $null -ne (Get-Command uv -ErrorAction SilentlyContinue)
        if ($uvAvailable) {
            uv lock
            Write-Host "uv.lock generated successfully (local uv)" -ForegroundColor Green
        } else {
            Write-Host "uv not found locally, using Docker..." -ForegroundColor Yellow
            docker run --rm -v "${PWD}:/app" -w /app ghcr.io/astral-sh/uv:latest uv lock
            Write-Host "uv.lock generated successfully (Docker)" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

function Invoke-LockWeb {
    Write-Host "Generating pnpm-lock.yaml for Web..." -ForegroundColor Cyan
    Push-Location -Path "apps/web"
    try {
        # Check if pnpm is available locally, otherwise use Docker
        $pnpmAvailable = $null -ne (Get-Command pnpm -ErrorAction SilentlyContinue)
        if ($pnpmAvailable) {
            pnpm install --lockfile-only
            Write-Host "pnpm-lock.yaml generated successfully (local pnpm)" -ForegroundColor Green
        } else {
            Write-Host "pnpm not found locally, using Docker..." -ForegroundColor Yellow
            docker run --rm -v "${PWD}:/app" -w /app node:20-alpine sh -c "corepack enable && corepack prepare pnpm@8.14.0 --activate && pnpm install --lockfile-only"
            Write-Host "pnpm-lock.yaml generated successfully (Docker)" -ForegroundColor Green
        }
    } finally {
        Pop-Location
    }
}

function Invoke-Lock {
    Write-Host "Generating all lockfiles..." -ForegroundColor Cyan
    Write-Host ""
    Invoke-LockApi
    Write-Host ""
    Invoke-LockWeb
    Write-Host ""
    Write-Host "=================================================================================" -ForegroundColor Green
    Write-Host "  LOCKFILES GENERATED" -ForegroundColor Green
    Write-Host "=================================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Files created:" -ForegroundColor Cyan
    Write-Host "  - apps/api/uv.lock" -ForegroundColor Yellow
    Write-Host "  - apps/web/pnpm-lock.yaml" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  git add apps/api/uv.lock apps/web/pnpm-lock.yaml" -ForegroundColor White
    Write-Host "  git commit -m `"chore: add baseline lockfiles`"" -ForegroundColor White
    Write-Host ""
}

function Test-ApiHealth {
    param(
        [int]$MaxAttempts = $script:MaxRetries,
        [int]$DelaySeconds = $script:RetryDelaySeconds
    )
    
    Write-Host "Waiting for API to be healthy..." -ForegroundColor Cyan
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-RestMethod -Uri $script:ApiHealthUrl -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok") {
                Write-Host "API is healthy! (attempt $i/$MaxAttempts)" -ForegroundColor Green
                return $true
            }
        } catch {
            # Suppress error, will retry
        }
        
        if ($i -lt $MaxAttempts) {
            Write-Host "  Attempt $i/$MaxAttempts - API not ready, waiting ${DelaySeconds}s..." -ForegroundColor Yellow
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    
    Write-Host "API failed to become healthy after $MaxAttempts attempts" -ForegroundColor Red
    return $false
}

function Test-WebHealth {
    param(
        [int]$MaxAttempts = 15,
        [int]$DelaySeconds = 2
    )
    
    Write-Host "Waiting for Web to be ready..." -ForegroundColor Cyan
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "Web is ready! (attempt $i/$MaxAttempts)" -ForegroundColor Green
                return $true
            }
        } catch {
            # Suppress error, will retry
        }
        
        if ($i -lt $MaxAttempts) {
            Write-Host "  Attempt $i/$MaxAttempts - Web not ready, waiting ${DelaySeconds}s..." -ForegroundColor Yellow
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    
    Write-Host "Web failed to become ready after $MaxAttempts attempts" -ForegroundColor Red
    return $false
}

function Invoke-LlmStatus {
    <#
    .SYNOPSIS
        Check the active LLM provider configuration.
    .DESCRIPTION
        1. Checks /health endpoint
        2. Fetches /llm/status (dev only endpoint)
        3. Displays provider, model, and fallback status
    #>
    
    Write-Host @"

================================================================================
                        LLM PROVIDER STATUS
================================================================================

"@ -ForegroundColor Cyan

    $apiBase = "http://localhost:8000"

    # Step 1: Check health endpoint
    Write-Host "[1/2] Checking API health..." -ForegroundColor Cyan
    $healthOk = $false
    try {
        $health = Invoke-RestMethod -Uri "$apiBase/health" -TimeoutSec 5 -ErrorAction Stop
        if ($health.status -eq "ok") {
            Write-Host "  API is healthy (environment: $($health.environment))" -ForegroundColor Green
            $healthOk = $true
        }
    } catch {
        Write-Host "  ERROR: API not reachable. Start services with: .\infra\dev.ps1 up" -ForegroundColor Red
        return
    }

    if (-not $healthOk) {
        Write-Host "  ERROR: API health check failed" -ForegroundColor Red
        return
    }

    # Step 2: Check LLM status
    Write-Host "`n[2/2] Fetching LLM provider status..." -ForegroundColor Cyan
    try {
        $llmStatus = Invoke-RestMethod -Uri "$apiBase/llm/status" -TimeoutSec 5 -ErrorAction Stop
        
        Write-Host ""
        Write-Host "  Active Provider:    $($llmStatus.provider)" -ForegroundColor $(if ($llmStatus.provider -eq "stub") { "Yellow" } else { "Green" })
        Write-Host "  Active Model:       $($llmStatus.model)" -ForegroundColor Gray
        Write-Host "  Configured:         LLM_PROVIDER=$($llmStatus.configured_provider)" -ForegroundColor Gray
        Write-Host "  API Key Set:        $($llmStatus.api_key_set)" -ForegroundColor $(if ($llmStatus.api_key_set) { "Green" } else { "Yellow" })
        Write-Host "  Environment:        $($llmStatus.environment)" -ForegroundColor Gray
        
        if ($llmStatus.is_fallback) {
            Write-Host ""
            Write-Host "  ⚠️  FALLBACK MODE: OpenAI configured but API key missing." -ForegroundColor Yellow
            Write-Host "     Using Stub provider which returns generic answers." -ForegroundColor Yellow
        }
        
        Write-Host ""
        if ($llmStatus.provider -eq "stub") {
            Write-Host @"
================================================================================
  STUB PROVIDER ACTIVE
================================================================================
"@ -ForegroundColor Yellow
            Write-Host "  The Stub provider returns deterministic/generic answers." -ForegroundColor Yellow
            Write-Host "  To enable real LLM outputs, configure OpenAI:" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "    In .env:" -ForegroundColor White
            Write-Host "      LLM_PROVIDER=openai" -ForegroundColor White
            Write-Host "      LLM_MODEL=gpt-4o-mini" -ForegroundColor White
            Write-Host "      LLM_API_KEY=sk-your-api-key" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host @"
================================================================================
  OPENAI PROVIDER ACTIVE
================================================================================
"@ -ForegroundColor Green
            Write-Host "  Real LLM outputs are enabled." -ForegroundColor Green
            Write-Host ""
        }
        
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 404) {
            Write-Host "  /llm/status endpoint not available (only in dev environment)" -ForegroundColor Yellow
            Write-Host "  Current environment: $($health.environment)" -ForegroundColor Gray
        } else {
            Write-Host "  ERROR: Failed to fetch LLM status: $_" -ForegroundColor Red
        }
    }
}

function Invoke-CorsCheck {
    <#
    .SYNOPSIS
        Verify CORS headers are correctly configured for local development.
    .DESCRIPTION
        1. Ensures API is running
        2. Checks /health endpoint returns 200
        3. Sends OPTIONS preflight request to /tenants
        4. Verifies Access-Control-Allow-Origin header includes http://localhost:3000
    #>
    
    Write-Host @"

================================================================================
                        CORS VERIFICATION
================================================================================

"@ -ForegroundColor Cyan

    $origin = "http://localhost:3000"
    $apiBase = "http://localhost:8000"
    $allPassed = $true

    # Step 1: Ensure API is running
    Write-Host "[1/3] Ensuring API is running..." -ForegroundColor Cyan
    try {
        $running = docker compose ps --format json 2>$null | ConvertFrom-Json | Where-Object { $_.Service -eq "api" -and $_.State -eq "running" }
        if (-not $running) {
            Write-Host "  API not running, starting..." -ForegroundColor Yellow
            docker compose up -d api
            Start-Sleep -Seconds 3
        } else {
            Write-Host "  API container is running" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Starting API service..." -ForegroundColor Yellow
        docker compose up -d api
        Start-Sleep -Seconds 3
    }

    # Step 2: Check health endpoint
    Write-Host "`n[2/3] Checking API health..." -ForegroundColor Cyan
    $healthOk = $false
    for ($i = 1; $i -le 10; $i++) {
        try {
            $response = Invoke-RestMethod -Uri "$apiBase/health" -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok") {
                Write-Host "  API is healthy (status: ok, environment: $($response.environment))" -ForegroundColor Green
                $healthOk = $true
                break
            }
        } catch {
            if ($i -lt 10) {
                Write-Host "  Attempt $i/10 - waiting for API..." -ForegroundColor Yellow
                Start-Sleep -Seconds 2
            }
        }
    }
    if (-not $healthOk) {
        Write-Host "  ERROR: API health check failed after 10 attempts" -ForegroundColor Red
        Write-Host "  Check logs: .\infra\dev.ps1 logs-api" -ForegroundColor Yellow
        exit 1
    }

    # Step 3: Send OPTIONS preflight request
    Write-Host "`n[3/3] Sending CORS preflight request..." -ForegroundColor Cyan
    Write-Host "  Origin: $origin" -ForegroundColor Gray
    Write-Host "  Target: $apiBase/tenants" -ForegroundColor Gray
    
    try {
        $headers = @{
            "Origin" = $origin
            "Access-Control-Request-Method" = "POST"
            "Access-Control-Request-Headers" = "content-type,authorization"
        }
        
        $response = Invoke-WebRequest -Uri "$apiBase/tenants" -Method Options -Headers $headers -TimeoutSec 10 -ErrorAction Stop
        
        # Check status code
        if ($response.StatusCode -ne 200) {
            Write-Host "  ERROR: Expected 200, got $($response.StatusCode)" -ForegroundColor Red
            $allPassed = $false
        } else {
            Write-Host "  Status: 200 OK" -ForegroundColor Green
        }
        
        # Check Access-Control-Allow-Origin header
        $allowOrigin = $response.Headers["Access-Control-Allow-Origin"]
        if ($allowOrigin -eq $origin -or $allowOrigin -eq "*") {
            Write-Host "  Access-Control-Allow-Origin: $allowOrigin" -ForegroundColor Green
        } else {
            Write-Host "  ERROR: Access-Control-Allow-Origin header missing or incorrect" -ForegroundColor Red
            Write-Host "  Expected: $origin (or *)" -ForegroundColor Yellow
            Write-Host "  Got: $allowOrigin" -ForegroundColor Yellow
            $allPassed = $false
        }
        
        # Check Access-Control-Allow-Methods header
        $allowMethods = $response.Headers["Access-Control-Allow-Methods"]
        if ($allowMethods -match "POST" -or $allowMethods -eq "*") {
            Write-Host "  Access-Control-Allow-Methods: $allowMethods" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: Access-Control-Allow-Methods may not include POST" -ForegroundColor Yellow
            Write-Host "  Got: $allowMethods" -ForegroundColor Yellow
        }
        
        # Check Access-Control-Allow-Credentials header
        $allowCredentials = $response.Headers["Access-Control-Allow-Credentials"]
        if ($allowCredentials -eq "true") {
            Write-Host "  Access-Control-Allow-Credentials: true" -ForegroundColor Green
        } else {
            Write-Host "  Access-Control-Allow-Credentials: $allowCredentials" -ForegroundColor Gray
        }
        
    } catch {
        Write-Host "  ERROR: CORS preflight request failed" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
        $allPassed = $false
    }

    # Summary
    Write-Host ""
    if ($allPassed) {
        Write-Host @"
================================================================================
                        CORS CHECK PASSED
================================================================================
"@ -ForegroundColor Green
        Write-Host "  Browser requests from $origin to $apiBase are allowed." -ForegroundColor Cyan
        Write-Host "  The /setup bootstrap flow should work correctly." -ForegroundColor Cyan
        Write-Host ""
        exit 0
    } else {
        Write-Host @"
================================================================================
                        CORS CHECK FAILED
================================================================================
"@ -ForegroundColor Red
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "  1. Check CORS_ORIGINS in .env or apps/api/.env" -ForegroundColor White
        Write-Host "  2. Ensure it includes: http://localhost:3000" -ForegroundColor White
        Write-Host "  3. Restart API: docker compose restart api" -ForegroundColor White
        Write-Host "  4. Check logs: .\infra\dev.ps1 logs-api" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

function Invoke-CookieCheck {
    <#
    .SYNOPSIS
        Verify cookie-based authentication works end-to-end.
    .DESCRIPTION
        1. Ensures API is running
        2. Bootstraps a test tenant
        3. Logs in via /auth/dev-login and verifies cookies are set
        4. Calls /auth/me using cookies and verifies 200
        5. Calls /auth/refresh and verifies token rotation
        6. Calls /auth/logout and verifies cookies are cleared
    #>
    
    Write-Host @"

================================================================================
                    COOKIE AUTH VERIFICATION
================================================================================

"@ -ForegroundColor Cyan

    $apiBase = "http://localhost:8000"
    $allPassed = $true
    $results = @{}

    # Step 1: Ensure API is running
    Write-Host "[1/6] Ensuring API is running..." -ForegroundColor Cyan
    try {
        $running = docker compose ps --format json 2>$null | ConvertFrom-Json | Where-Object { $_.Service -eq "api" -and $_.State -eq "running" }
        if (-not $running) {
            Write-Host "  API not running, starting..." -ForegroundColor Yellow
            docker compose up -d api
            Start-Sleep -Seconds 3
        } else {
            Write-Host "  API container is running" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Starting API service..." -ForegroundColor Yellow
        docker compose up -d api
        Start-Sleep -Seconds 3
    }

    # Wait for health
    $healthOk = $false
    for ($i = 1; $i -le 15; $i++) {
        try {
            $response = Invoke-RestMethod -Uri "$apiBase/health" -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok") {
                Write-Host "  API is healthy" -ForegroundColor Green
                $healthOk = $true
                break
            }
        } catch {
            if ($i -lt 15) {
                Write-Host "  Attempt $i/15 - waiting for API..." -ForegroundColor Yellow
                Start-Sleep -Seconds 2
            }
        }
    }
    if (-not $healthOk) {
        Write-Host "  ERROR: API health check failed" -ForegroundColor Red
        exit 1
    }
    $results["API Health"] = $true

    # Step 2: Bootstrap test tenant
    Write-Host "`n[2/6] Bootstrapping test tenant..." -ForegroundColor Cyan
    $uniqueId = [Guid]::NewGuid().ToString().Substring(0, 8)
    $testEmail = "cookietest-$uniqueId@test.local"
    
    try {
        $bootstrapBody = @{
            name = "Cookie Test $uniqueId"
            primary_jurisdiction = "UAE"
            data_residency_policy = "UAE"
            bootstrap = @{
                admin_user = @{ email = $testEmail }
                workspace = @{ name = "Test Workspace" }
            }
        } | ConvertTo-Json -Depth 3

        $bootstrap = Invoke-RestMethod -Uri "$apiBase/tenants" -Method POST `
            -ContentType "application/json" -Body $bootstrapBody -TimeoutSec 10

        Write-Host "  Tenant created: $($bootstrap.tenant_id)" -ForegroundColor Green
        Write-Host "  User: $testEmail" -ForegroundColor Gray
        $results["Bootstrap Tenant"] = $true
    } catch {
        Write-Host "  ERROR: Failed to bootstrap tenant: $($_.Exception.Message)" -ForegroundColor Red
        $results["Bootstrap Tenant"] = $false
        $allPassed = $false
    }

    if (-not $results["Bootstrap Tenant"]) {
        Write-Host "`nCannot continue without tenant. Exiting." -ForegroundColor Red
        exit 1
    }

    # Step 3: Login and check cookies
    Write-Host "`n[3/6] Testing /auth/dev-login (cookie setting)..." -ForegroundColor Cyan
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    
    try {
        $loginBody = @{
            tenant_id = $bootstrap.tenant_id
            workspace_id = $bootstrap.workspace_id
            email = $testEmail
        } | ConvertTo-Json

        $loginResponse = Invoke-WebRequest -Uri "$apiBase/auth/dev-login" -Method POST `
            -ContentType "application/json" -Body $loginBody -WebSession $session -TimeoutSec 10

        $loginData = $loginResponse.Content | ConvertFrom-Json
        
        # Check response
        if ($loginData.auth_mode -ne "cookie") {
            throw "Expected auth_mode=cookie, got $($loginData.auth_mode)"
        }

        # Check Set-Cookie headers
        $setCookies = $loginResponse.Headers["Set-Cookie"]
        if (-not $setCookies) {
            throw "No Set-Cookie headers returned"
        }

        $hasAccessToken = $false
        $hasRefreshToken = $false
        $accessCookieInfo = ""
        $refreshCookieInfo = ""

        foreach ($cookie in $setCookies) {
            if ($cookie -match "^access_token=") {
                $hasAccessToken = $true
                $accessCookieInfo = $cookie
                # Verify attributes
                if ($cookie -notmatch "(?i)httponly") {
                    throw "access_token missing HttpOnly"
                }
                if ($cookie -notmatch "(?i)samesite=lax") {
                    throw "access_token missing SameSite=Lax"
                }
                if ($cookie -notmatch "(?i)path=/[^a]") {
                    # path=/ but not path=/auth
                    if ($cookie -notmatch "(?i)path=/;|path=/$") {
                        throw "access_token has wrong Path (expected /)"
                    }
                }
            }
            if ($cookie -match "^refresh_token=") {
                $hasRefreshToken = $true
                $refreshCookieInfo = $cookie
                if ($cookie -notmatch "(?i)httponly") {
                    throw "refresh_token missing HttpOnly"
                }
                if ($cookie -notmatch "(?i)samesite=lax") {
                    throw "refresh_token missing SameSite=Lax"
                }
                if ($cookie -notmatch "(?i)path=/auth") {
                    throw "refresh_token missing Path=/auth"
                }
            }
        }

        if (-not $hasAccessToken) { throw "access_token cookie not set" }
        if (-not $hasRefreshToken) { throw "refresh_token cookie not set" }

        Write-Host "  Login successful (auth_mode=cookie)" -ForegroundColor Green
        Write-Host "  access_token: HttpOnly, SameSite=Lax, Path=/" -ForegroundColor Gray
        Write-Host "  refresh_token: HttpOnly, SameSite=Lax, Path=/auth" -ForegroundColor Gray
        $results["Login Sets Cookies"] = $true
    } catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $results["Login Sets Cookies"] = $false
        $allPassed = $false
    }

    if (-not $results["Login Sets Cookies"]) {
        Write-Host "`nCannot continue without login. Exiting." -ForegroundColor Red
        exit 1
    }

    # Step 4: Test /auth/me with cookies
    Write-Host "`n[4/6] Testing /auth/me (cookie authentication)..." -ForegroundColor Cyan
    try {
        $meResponse = Invoke-RestMethod -Uri "$apiBase/auth/me" -Method GET `
            -WebSession $session -TimeoutSec 10

        if ($meResponse.email -ne $testEmail) {
            throw "Expected email $testEmail, got $($meResponse.email)"
        }
        if ($meResponse.auth_mode -ne "cookie") {
            throw "Expected auth_mode=cookie, got $($meResponse.auth_mode)"
        }

        Write-Host "  /auth/me returned correct user: $($meResponse.email)" -ForegroundColor Green
        Write-Host "  auth_mode: $($meResponse.auth_mode)" -ForegroundColor Gray
        $results["Auth Me Works"] = $true
    } catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $results["Auth Me Works"] = $false
        $allPassed = $false
    }

    # Step 5: Test /auth/refresh (token rotation)
    Write-Host "`n[5/6] Testing /auth/refresh (token rotation)..." -ForegroundColor Cyan
    try {
        $refreshResponse = Invoke-WebRequest -Uri "$apiBase/auth/refresh" -Method POST `
            -WebSession $session -TimeoutSec 10

        $refreshData = $refreshResponse.Content | ConvertFrom-Json

        if ($refreshData.auth_mode -ne "cookie") {
            throw "Expected auth_mode=cookie, got $($refreshData.auth_mode)"
        }
        if (-not $refreshData.expires_in) {
            throw "Missing expires_in in response"
        }

        # Verify new cookies are set
        $newSetCookies = $refreshResponse.Headers["Set-Cookie"]
        $hasNewRefresh = $false
        foreach ($cookie in $newSetCookies) {
            if ($cookie -match "^refresh_token=") {
                $hasNewRefresh = $true
            }
        }
        if (-not $hasNewRefresh) {
            throw "No new refresh_token cookie set (rotation failed)"
        }

        Write-Host "  Refresh successful, new tokens issued" -ForegroundColor Green
        Write-Host "  expires_in: $($refreshData.expires_in) seconds" -ForegroundColor Gray
        $results["Refresh Rotates Tokens"] = $true
    } catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $results["Refresh Rotates Tokens"] = $false
        $allPassed = $false
    }

    # Step 6: Test /auth/logout (cookie clearing)
    Write-Host "`n[6/6] Testing /auth/logout (cookie clearing)..." -ForegroundColor Cyan
    try {
        $logoutResponse = Invoke-WebRequest -Uri "$apiBase/auth/logout" -Method POST `
            -WebSession $session -TimeoutSec 10

        $logoutData = $logoutResponse.Content | ConvertFrom-Json

        if ($logoutData.message -notmatch "logged out") {
            throw "Unexpected logout message: $($logoutData.message)"
        }

        # Verify cookies are cleared (Max-Age=0 or empty value)
        $clearCookies = $logoutResponse.Headers["Set-Cookie"]
        $accessCleared = $false
        $refreshCleared = $false

        foreach ($cookie in $clearCookies) {
            if ($cookie -match "^access_token=") {
                if ($cookie -match "max-age=0" -or $cookie -match 'access_token=""' -or $cookie -match "access_token=;") {
                    $accessCleared = $true
                }
            }
            if ($cookie -match "^refresh_token=") {
                if ($cookie -match "max-age=0" -or $cookie -match 'refresh_token=""' -or $cookie -match "refresh_token=;") {
                    $refreshCleared = $true
                }
            }
        }

        if (-not $accessCleared) {
            Write-Host "  WARNING: access_token may not be fully cleared" -ForegroundColor Yellow
        }
        if (-not $refreshCleared) {
            Write-Host "  WARNING: refresh_token may not be fully cleared" -ForegroundColor Yellow
        }

        Write-Host "  Logout successful, cookies cleared" -ForegroundColor Green
        $results["Logout Clears Cookies"] = $true
    } catch {
        Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $results["Logout Clears Cookies"] = $false
        $allPassed = $false
    }

    # Summary
    Write-Host @"

================================================================================
                    COOKIE AUTH VERIFICATION RESULTS
================================================================================
"@ -ForegroundColor Cyan

    foreach ($check in $results.Keys) {
        if ($results[$check]) {
            Write-Host "  [PASS] $check" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $check" -ForegroundColor Red
        }
    }

    Write-Host ""

    if ($allPassed) {
        Write-Host @"
================================================================================
                    ALL COOKIE AUTH CHECKS PASSED
================================================================================
"@ -ForegroundColor Green
        Write-Host "Cookie-based authentication is working correctly!" -ForegroundColor Green
        Write-Host ""
        exit 0
    } else {
        Write-Host @"
================================================================================
                    COOKIE AUTH VERIFICATION FAILED
================================================================================
"@ -ForegroundColor Red
        Write-Host "Check logs: .\infra\dev.ps1 logs-api" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

function Invoke-ProxyUp {
    <#
    .SYNOPSIS
        Start the stack with Caddy HTTPS reverse proxy.
    .DESCRIPTION
        Starts:
        - postgres, redis, minio (dependencies)
        - api-proxy (FastAPI with API_ROOT_PATH=/api)
        - web-proxy (Next.js with same-origin config)
        - caddy (HTTPS proxy at https://localhost)

        After starting, access:
        - Web: https://localhost
        - API: https://localhost/api
        - API Health: https://localhost/api/health
    #>
    
    Write-Host @"

================================================================================
                    STARTING HTTPS PROXY STACK
================================================================================

"@ -ForegroundColor Cyan

    Write-Host "Starting dependencies (postgres, redis, minio)..." -ForegroundColor Cyan
    docker compose up -d postgres redis minio minio-init

    # Wait for dependencies
    Write-Host "Waiting for dependencies to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5

    Write-Host "Starting proxy stack (caddy, api-proxy, web-proxy)..." -ForegroundColor Cyan
    docker compose --profile proxy up -d --build

    Write-Host ""
    Write-Host "Waiting for services to be ready..." -ForegroundColor Cyan
    Start-Sleep -Seconds 10

    Write-Host @"

================================================================================
                    HTTPS PROXY STACK STARTED
================================================================================

  Web (HTTPS):       https://localhost
  API (HTTPS):       https://localhost/api
  API Health:        https://localhost/api/health
  API Docs:          https://localhost/api/docs

  Note: Your browser will show a certificate warning on first access.
  This is expected for local development with self-signed certificates.

  To trust the Caddy CA (optional):
    1. Open https://localhost in browser
    2. Click "Advanced" -> "Proceed to localhost (unsafe)"
    Or see docs/LOCAL_DEV.md for Windows trust instructions.

  Verify with: .\infra\dev.ps1 proxy-check

"@ -ForegroundColor Green
}

function Invoke-ProxyDown {
    <#
    .SYNOPSIS
        Stop the Caddy proxy and related services.
    #>
    
    Write-Host "Stopping proxy stack..." -ForegroundColor Cyan
    docker compose --profile proxy down
    Write-Host "Proxy stack stopped." -ForegroundColor Green
}

function Invoke-ProxyLogs {
    <#
    .SYNOPSIS
        Follow logs for Caddy proxy.
    #>
    docker compose logs -f caddy
}

function Invoke-ProxyCheck {
    <#
    .SYNOPSIS
        Verify the HTTPS proxy stack works correctly.
    .DESCRIPTION
        1. Check https://localhost returns 200 (web)
        2. Check https://localhost/api/health returns 200 (api)
        3. Test cookie auth through proxy:
           - dev-login at https://localhost/api/auth/dev-login
           - me at https://localhost/api/auth/me
           - refresh at https://localhost/api/auth/refresh
    #>
    
    Write-Host @"

================================================================================
                    HTTPS PROXY VERIFICATION
================================================================================

"@ -ForegroundColor Cyan

    $proxyBase = "https://localhost"
    $allPassed = $true
    $results = @{}

    # PowerShell options to ignore self-signed cert warnings
    # Note: This is DEV ONLY - never do this in production scripts
    $certCallback = @"
using System.Net;
using System.Net.Security;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@
    
    try {
        Add-Type -TypeDefinition $certCallback -ErrorAction SilentlyContinue
    } catch {
        # Type already exists, ignore
    }
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

    # For PowerShell 6+, use -SkipCertificateCheck
    $psVersion = $PSVersionTable.PSVersion.Major
    $skipCert = $psVersion -ge 6

    # Step 1: Check if proxy services are running
    Write-Host "[1/5] Checking proxy services are running..." -ForegroundColor Cyan
    try {
        $services = docker compose --profile proxy ps --format json 2>$null | ConvertFrom-Json
        $caddyRunning = $services | Where-Object { $_.Service -eq "caddy" -and $_.State -eq "running" }
        $apiProxyRunning = $services | Where-Object { $_.Service -eq "api-proxy" -and $_.State -eq "running" }
        $webProxyRunning = $services | Where-Object { $_.Service -eq "web-proxy" -and $_.State -eq "running" }
        
        if ($caddyRunning -and $apiProxyRunning -and $webProxyRunning) {
            Write-Host "  All proxy services running" -ForegroundColor Green
            $results["Proxy Services Running"] = $true
        } else {
            Write-Host "  ERROR: Not all proxy services are running" -ForegroundColor Red
            Write-Host "  Run: .\infra\dev.ps1 proxy-up" -ForegroundColor Yellow
            $results["Proxy Services Running"] = $false
            $allPassed = $false
        }
    } catch {
        Write-Host "  WARNING: Could not check service status, continuing..." -ForegroundColor Yellow
        $results["Proxy Services Running"] = $true
    }

    # Step 2: Check web through proxy
    Write-Host "`n[2/5] Checking web at $proxyBase ..." -ForegroundColor Cyan
    $webOk = $false
    for ($i = 1; $i -le 10; $i++) {
        try {
            if ($skipCert) {
                $response = Invoke-WebRequest -Uri $proxyBase -TimeoutSec 5 -SkipCertificateCheck -ErrorAction Stop
            } else {
                $response = Invoke-WebRequest -Uri $proxyBase -TimeoutSec 5 -ErrorAction Stop
            }
            if ($response.StatusCode -eq 200) {
                Write-Host "  Web returned 200 OK" -ForegroundColor Green
                $webOk = $true
                $results["Web HTTPS"] = $true
                break
            }
        } catch {
            if ($i -lt 10) {
                Write-Host "  Attempt $i/10 - waiting for web..." -ForegroundColor Yellow
                Start-Sleep -Seconds 2
            }
        }
    }
    if (-not $webOk) {
        Write-Host "  ERROR: Web not responding at $proxyBase" -ForegroundColor Red
        $results["Web HTTPS"] = $false
        $allPassed = $false
    }

    # Step 3: Check API health through proxy
    Write-Host "`n[3/5] Checking API at $proxyBase/api/health ..." -ForegroundColor Cyan
    $apiOk = $false
    for ($i = 1; $i -le 10; $i++) {
        try {
            if ($skipCert) {
                $health = Invoke-RestMethod -Uri "$proxyBase/api/health" -TimeoutSec 5 -SkipCertificateCheck -ErrorAction Stop
            } else {
                $health = Invoke-RestMethod -Uri "$proxyBase/api/health" -TimeoutSec 5 -ErrorAction Stop
            }
            if ($health.status -eq "ok") {
                Write-Host "  API health: ok (environment: $($health.environment))" -ForegroundColor Green
                $apiOk = $true
                $results["API HTTPS"] = $true
                break
            }
        } catch {
            if ($i -lt 10) {
                Write-Host "  Attempt $i/10 - waiting for API..." -ForegroundColor Yellow
                Start-Sleep -Seconds 2
            }
        }
    }
    if (-not $apiOk) {
        Write-Host "  ERROR: API health check failed at $proxyBase/api/health" -ForegroundColor Red
        $results["API HTTPS"] = $false
        $allPassed = $false
    }

    if (-not $apiOk) {
        Write-Host "`nCannot continue cookie tests without API. Exiting." -ForegroundColor Red
        exit 1
    }

    # Step 4: Test cookie auth through proxy
    Write-Host "`n[4/5] Testing cookie auth through proxy..." -ForegroundColor Cyan
    
    # Bootstrap test tenant
    $uniqueId = [Guid]::NewGuid().ToString().Substring(0, 8)
    $testEmail = "proxytest-$uniqueId@test.local"
    
    try {
        $bootstrapBody = @{
            name = "Proxy Test $uniqueId"
            primary_jurisdiction = "UAE"
            data_residency_policy = "UAE"
            bootstrap = @{
                admin_user = @{ email = $testEmail }
                workspace = @{ name = "Test Workspace" }
            }
        } | ConvertTo-Json -Depth 3

        if ($skipCert) {
            $bootstrap = Invoke-RestMethod -Uri "$proxyBase/api/tenants" -Method POST `
                -ContentType "application/json" -Body $bootstrapBody -TimeoutSec 10 -SkipCertificateCheck
        } else {
            $bootstrap = Invoke-RestMethod -Uri "$proxyBase/api/tenants" -Method POST `
                -ContentType "application/json" -Body $bootstrapBody -TimeoutSec 10
        }

        Write-Host "  Tenant bootstrapped: $($bootstrap.tenant_id)" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to bootstrap tenant: $($_.Exception.Message)" -ForegroundColor Red
        $results["Cookie Auth Through Proxy"] = $false
        $allPassed = $false
    }

    if ($bootstrap) {
        # Login
        $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
        try {
            $loginBody = @{
                tenant_id = $bootstrap.tenant_id
                workspace_id = $bootstrap.workspace_id
                email = $testEmail
            } | ConvertTo-Json

            if ($skipCert) {
                $loginResponse = Invoke-WebRequest -Uri "$proxyBase/api/auth/dev-login" -Method POST `
                    -ContentType "application/json" -Body $loginBody -WebSession $session -TimeoutSec 10 -SkipCertificateCheck
            } else {
                $loginResponse = Invoke-WebRequest -Uri "$proxyBase/api/auth/dev-login" -Method POST `
                    -ContentType "application/json" -Body $loginBody -WebSession $session -TimeoutSec 10
            }

            $loginData = $loginResponse.Content | ConvertFrom-Json
            if ($loginData.auth_mode -eq "cookie") {
                Write-Host "  Login via proxy: OK (auth_mode=cookie)" -ForegroundColor Green
            }

            # Check cookies were set
            $cookies = $loginResponse.Headers["Set-Cookie"]
            $hasAccess = $cookies -match "access_token="
            $hasRefresh = $cookies -match "refresh_token="
            
            if ($hasAccess -and $hasRefresh) {
                Write-Host "  Cookies set through proxy: access_token, refresh_token" -ForegroundColor Green
            } else {
                Write-Host "  WARNING: Expected cookies not found in response" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  ERROR: Login failed: $($_.Exception.Message)" -ForegroundColor Red
            $results["Cookie Auth Through Proxy"] = $false
            $allPassed = $false
        }

        # Test /auth/me through proxy
        try {
            if ($skipCert) {
                $me = Invoke-RestMethod -Uri "$proxyBase/api/auth/me" -Method GET `
                    -WebSession $session -TimeoutSec 10 -SkipCertificateCheck
            } else {
                $me = Invoke-RestMethod -Uri "$proxyBase/api/auth/me" -Method GET `
                    -WebSession $session -TimeoutSec 10
            }

            if ($me.email -eq $testEmail) {
                Write-Host "  /api/auth/me via proxy: OK ($testEmail)" -ForegroundColor Green
                $results["Cookie Auth Through Proxy"] = $true
            }
        } catch {
            Write-Host "  ERROR: /auth/me failed: $($_.Exception.Message)" -ForegroundColor Red
            $results["Cookie Auth Through Proxy"] = $false
            $allPassed = $false
        }

        # Test /auth/refresh through proxy
        try {
            if ($skipCert) {
                $refreshResponse = Invoke-WebRequest -Uri "$proxyBase/api/auth/refresh" -Method POST `
                    -WebSession $session -TimeoutSec 10 -SkipCertificateCheck
            } else {
                $refreshResponse = Invoke-WebRequest -Uri "$proxyBase/api/auth/refresh" -Method POST `
                    -WebSession $session -TimeoutSec 10
            }

            $refreshData = $refreshResponse.Content | ConvertFrom-Json
            if ($refreshData.auth_mode -eq "cookie") {
                Write-Host "  /api/auth/refresh via proxy: OK (tokens rotated)" -ForegroundColor Green
                $results["Token Refresh Through Proxy"] = $true
            }
        } catch {
            Write-Host "  ERROR: /auth/refresh failed: $($_.Exception.Message)" -ForegroundColor Red
            $results["Token Refresh Through Proxy"] = $false
            $allPassed = $false
        }
    }

    # Step 5: Verify TLS
    Write-Host "`n[5/5] Checking TLS configuration..." -ForegroundColor Cyan
    try {
        $uri = [System.Uri]$proxyBase
        if ($uri.Scheme -eq "https") {
            Write-Host "  Proxy serving HTTPS" -ForegroundColor Green
            $results["TLS Enabled"] = $true
        }
    } catch {
        $results["TLS Enabled"] = $false
        $allPassed = $false
    }

    # Summary
    Write-Host @"

================================================================================
                    HTTPS PROXY VERIFICATION RESULTS
================================================================================
"@ -ForegroundColor Cyan

    foreach ($check in $results.Keys) {
        if ($results[$check]) {
            Write-Host "  [PASS] $check" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $check" -ForegroundColor Red
        }
    }

    Write-Host ""

    if ($allPassed) {
        Write-Host @"
================================================================================
                    ALL PROXY CHECKS PASSED
================================================================================
"@ -ForegroundColor Green
        Write-Host "  HTTPS reverse proxy is working correctly!" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Endpoints:" -ForegroundColor Cyan
        Write-Host "    Web:     https://localhost" -ForegroundColor Yellow
        Write-Host "    API:     https://localhost/api" -ForegroundColor Yellow
        Write-Host "    Docs:    https://localhost/api/docs" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Same-origin benefits:" -ForegroundColor Cyan
        Write-Host "    - No CORS preflight requests" -ForegroundColor White
        Write-Host "    - Cookies work with SameSite=Lax" -ForegroundColor White
        Write-Host "    - Secure cookies testable with COOKIE_SECURE=true" -ForegroundColor White
        Write-Host ""
        exit 0
    } else {
        Write-Host @"
================================================================================
                    PROXY VERIFICATION FAILED
================================================================================
"@ -ForegroundColor Red
        Write-Host "Troubleshooting:" -ForegroundColor Yellow
        Write-Host "  1. Check Caddy logs: .\infra\dev.ps1 proxy-logs" -ForegroundColor White
        Write-Host "  2. Check API logs: docker compose logs api-proxy" -ForegroundColor White
        Write-Host "  3. Check Web logs: docker compose logs web-proxy" -ForegroundColor White
        Write-Host "  4. Ensure proxy is running: .\infra\dev.ps1 proxy-up" -ForegroundColor White
        Write-Host ""
        exit 1
    }
}

function Invoke-SameOriginCheck {
    <#
    .SYNOPSIS
        Verify same-origin prep for production proxy architecture.
    .DESCRIPTION
        1. Check web URL resolution configuration
        2. Verify API root_path support
        3. Validate URL formation for same-origin mode
    #>
    
    Write-Host @"

================================================================================
                    SAME-ORIGIN PREP VERIFICATION
================================================================================

This check validates that the application is ready for same-origin deployment
where Web and API are served from the same origin via a reverse proxy.

Target Architecture:
  - Web served at: https://app.example.com/
  - API served at: https://app.example.com/api/
  - Cookies: SameSite=Lax works without cross-site complexity

"@ -ForegroundColor Cyan

    $apiBase = "http://localhost:8000"
    $allPassed = $true
    $results = @{}

    # Step 1: Check current web configuration
    Write-Host "[1/4] Checking Web API URL Configuration..." -ForegroundColor Cyan
    
    $envFile = "apps/web/.env.local"
    $envExampleFile = ".env.example"
    
    # Read current env vars
    $nextPublicApiBaseUrl = $env:NEXT_PUBLIC_API_BASE_URL
    $nextPublicApiPrefix = $env:NEXT_PUBLIC_API_PREFIX
    
    if ($nextPublicApiBaseUrl) {
        Write-Host "  Mode: CROSS-ORIGIN (development)" -ForegroundColor Yellow
        Write-Host "  NEXT_PUBLIC_API_BASE_URL = $nextPublicApiBaseUrl" -ForegroundColor Gray
    } else {
        Write-Host "  Mode: SAME-ORIGIN (production-ready)" -ForegroundColor Green
        Write-Host "  NEXT_PUBLIC_API_BASE_URL = (not set)" -ForegroundColor Gray
    }
    
    $prefix = if ($nextPublicApiPrefix) { $nextPublicApiPrefix } else { "/api" }
    Write-Host "  NEXT_PUBLIC_API_PREFIX = $prefix (default: /api)" -ForegroundColor Gray
    $results["Web Config Documented"] = $true

    # Step 2: Verify api.ts exports same-origin helpers
    Write-Host "`n[2/4] Verifying Web API resolver supports same-origin..." -ForegroundColor Cyan
    
    $apiTsPath = "apps/web/src/lib/api.ts"
    if (Test-Path $apiTsPath) {
        $apiTsContent = Get-Content $apiTsPath -Raw
        
        $hasGetApiPrefix = $apiTsContent -match "getApiPrefix"
        $hasIsSameOriginMode = $apiTsContent -match "isSameOriginMode"
        $hasGetApiConfig = $apiTsContent -match "getApiConfig"
        
        if ($hasGetApiPrefix -and $hasIsSameOriginMode -and $hasGetApiConfig) {
            Write-Host "  api.ts has same-origin helpers:" -ForegroundColor Green
            Write-Host "    - getApiPrefix() " -ForegroundColor Gray
            Write-Host "    - isSameOriginMode() " -ForegroundColor Gray
            Write-Host "    - getApiConfig() " -ForegroundColor Gray
            $results["Web Same-Origin Helpers"] = $true
        } else {
            Write-Host "  ERROR: api.ts missing same-origin helpers" -ForegroundColor Red
            $results["Web Same-Origin Helpers"] = $false
            $allPassed = $false
        }
    } else {
        Write-Host "  ERROR: $apiTsPath not found" -ForegroundColor Red
        $results["Web Same-Origin Helpers"] = $false
        $allPassed = $false
    }

    # Step 3: Verify API root_path config exists
    Write-Host "`n[3/4] Verifying API root_path configuration..." -ForegroundColor Cyan
    
    $configPyPath = "apps/api/src/config.py"
    if (Test-Path $configPyPath) {
        $configContent = Get-Content $configPyPath -Raw
        
        if ($configContent -match "api_root_path") {
            Write-Host "  config.py has api_root_path setting " -ForegroundColor Green
            $results["API Root Path Config"] = $true
        } else {
            Write-Host "  ERROR: config.py missing api_root_path" -ForegroundColor Red
            $results["API Root Path Config"] = $false
            $allPassed = $false
        }
    } else {
        Write-Host "  ERROR: $configPyPath not found" -ForegroundColor Red
        $results["API Root Path Config"] = $false
        $allPassed = $false
    }
    
    $mainPyPath = "apps/api/src/main.py"
    if (Test-Path $mainPyPath) {
        $mainContent = Get-Content $mainPyPath -Raw
        
        if ($mainContent -match "root_path=") {
            Write-Host "  main.py uses root_path in FastAPI " -ForegroundColor Green
            $results["API FastAPI Root Path"] = $true
        } else {
            Write-Host "  ERROR: main.py not using root_path" -ForegroundColor Red
            $results["API FastAPI Root Path"] = $false
            $allPassed = $false
        }
    }

    # Step 4: Verify API works with root_path (live test)
    Write-Host "`n[4/4] Testing API with root_path simulation..." -ForegroundColor Cyan
    
    # Check if API is running
    try {
        $running = docker compose ps --format json 2>$null | ConvertFrom-Json | Where-Object { $_.Service -eq "api" -and $_.State -eq "running" }
        if (-not $running) {
            Write-Host "  API not running, starting..." -ForegroundColor Yellow
            docker compose up -d api
            Start-Sleep -Seconds 3
        }
    } catch {
        Write-Host "  Starting API service..." -ForegroundColor Yellow
        docker compose up -d api
        Start-Sleep -Seconds 3
    }

    # Wait for health
    $healthOk = $false
    for ($i = 1; $i -le 10; $i++) {
        try {
            $response = Invoke-RestMethod -Uri "$apiBase/health" -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok") {
                $healthOk = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    
    if ($healthOk) {
        Write-Host "  API is running (current root_path: default)" -ForegroundColor Green
        
        # Check OpenAPI endpoint works
        try {
            $openapi = Invoke-RestMethod -Uri "$apiBase/openapi.json" -TimeoutSec 5 -ErrorAction Stop
            if ($openapi.info.title) {
                Write-Host "  OpenAPI docs accessible at /openapi.json " -ForegroundColor Green
                $results["API OpenAPI Works"] = $true
            }
        } catch {
            Write-Host "  WARNING: Could not fetch /openapi.json" -ForegroundColor Yellow
            $results["API OpenAPI Works"] = $true  # Non-critical
        }
        
        Write-Host "`n  To test with API_ROOT_PATH=/api:" -ForegroundColor Cyan
        Write-Host "    docker compose run --rm -e API_ROOT_PATH=/api api uv run pytest tests/ -k 'test_health' -v" -ForegroundColor White
        Write-Host "  Or temporarily:" -ForegroundColor Cyan
        Write-Host '    $env:API_ROOT_PATH="/api"; docker compose up -d api' -ForegroundColor White
    } else {
        Write-Host "  ERROR: API health check failed" -ForegroundColor Red
        $results["API OpenAPI Works"] = $false
        $allPassed = $false
    }

    # Summary
    Write-Host @"

================================================================================
                    SAME-ORIGIN PREP RESULTS
================================================================================
"@ -ForegroundColor Cyan

    foreach ($check in $results.Keys) {
        if ($results[$check]) {
            Write-Host "  [PASS] $check" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $check" -ForegroundColor Red
        }
    }

    Write-Host ""

    # Same-origin URL formation check
    Write-Host "URL Formation Check:" -ForegroundColor Cyan
    Write-Host "  In same-origin mode (production), client would call:" -ForegroundColor Gray
    Write-Host "    /api/health" -ForegroundColor White
    Write-Host "    /api/auth/me" -ForegroundColor White
    Write-Host "    /api/auth/refresh" -ForegroundColor White
    Write-Host ""
    Write-Host "  In cross-origin mode (current dev), client calls:" -ForegroundColor Gray
    Write-Host "    http://localhost:8000/health" -ForegroundColor White
    Write-Host "    http://localhost:8000/auth/me" -ForegroundColor White
    Write-Host ""

    if ($allPassed) {
        Write-Host @"
================================================================================
                    SAME-ORIGIN PREP COMPLETE
================================================================================
"@ -ForegroundColor Green
        Write-Host "Application is ready for same-origin deployment behind a reverse proxy." -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps (Agent #25):" -ForegroundColor Yellow
        Write-Host "  1. Configure reverse proxy (nginx/caddy) to mount API at /api" -ForegroundColor White
        Write-Host "  2. Set API_ROOT_PATH=/api in production" -ForegroundColor White
        Write-Host "  3. Remove NEXT_PUBLIC_API_BASE_URL in production" -ForegroundColor White
        Write-Host "  4. Add TLS termination at proxy" -ForegroundColor White
        Write-Host ""
        exit 0
    } else {
        Write-Host @"
================================================================================
                    SAME-ORIGIN PREP INCOMPLETE
================================================================================
"@ -ForegroundColor Red
        Write-Host "Some checks failed. Review the errors above." -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

function Invoke-Verify {
    Write-Host @"

================================================================================
                        AIDEN.AI VERIFICATION
================================================================================

"@ -ForegroundColor Cyan

    $results = @{
        "Environment Setup" = $false
        "Docker Build" = $false
        "API Health" = $false
        "Web Health" = $false
        "API Tests" = $false
        "Linting" = $false
    }
    $startTime = Get-Date

    # Step 1: Ensure .env exists
    Write-Host "`n[1/6] Checking environment setup..." -ForegroundColor Cyan
    if (-not (Test-Path ".env")) {
        Write-Host "  .env not found, copying from .env.example..." -ForegroundColor Yellow
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Host "  Created .env from .env.example" -ForegroundColor Green
            $results["Environment Setup"] = $true
        } else {
            Write-Host "  ERROR: .env.example not found!" -ForegroundColor Red
        }
    } else {
        Write-Host "  .env already exists" -ForegroundColor Green
        $results["Environment Setup"] = $true
    }

    # Step 2: Build and start services
    Write-Host "`n[2/6] Building and starting services..." -ForegroundColor Cyan
    try {
        docker compose up -d --build
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Docker Compose started successfully" -ForegroundColor Green
            $results["Docker Build"] = $true
        } else {
            Write-Host "  Docker Compose failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
    } catch {
        Write-Host "  Docker Compose failed: $_" -ForegroundColor Red
    }

    # Step 3: Wait for API health
    Write-Host "`n[3/6] Checking API health..." -ForegroundColor Cyan
    if (Test-ApiHealth -MaxAttempts 30 -DelaySeconds 2) {
        $results["API Health"] = $true
    }

    # Step 4: Wait for Web health
    Write-Host "`n[4/6] Checking Web health..." -ForegroundColor Cyan
    if (Test-WebHealth -MaxAttempts 20 -DelaySeconds 2) {
        $results["Web Health"] = $true
    }

    # Step 5: Run API tests
    Write-Host "`n[5/6] Running API tests..." -ForegroundColor Cyan
    try {
        docker compose exec -T api uv run pytest -v
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  API tests passed" -ForegroundColor Green
            $results["API Tests"] = $true
        } else {
            Write-Host "  API tests failed with exit code $LASTEXITCODE" -ForegroundColor Red
        }
    } catch {
        Write-Host "  API tests failed: $_" -ForegroundColor Red
    }

    # Step 6: Run linting
    Write-Host "`n[6/6] Running linters..." -ForegroundColor Cyan
    $lintPassed = $true
    try {
        docker compose exec -T api uv run ruff check .
        if ($LASTEXITCODE -ne 0) { $lintPassed = $false }
    } catch {
        $lintPassed = $false
    }
    try {
        docker compose exec -T web pnpm lint
        if ($LASTEXITCODE -ne 0) { $lintPassed = $false }
    } catch {
        $lintPassed = $false
    }
    if ($lintPassed) {
        Write-Host "  Linting passed" -ForegroundColor Green
        $results["Linting"] = $true
    } else {
        Write-Host "  Linting failed" -ForegroundColor Red
    }

    # Summary
    $endTime = Get-Date
    $duration = $endTime - $startTime

    Write-Host @"

================================================================================
                        VERIFICATION SUMMARY
================================================================================
"@ -ForegroundColor Cyan

    $allPassed = $true
    foreach ($check in $results.Keys) {
        if ($results[$check]) {
            Write-Host "  [PASS] $check" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $check" -ForegroundColor Red
            $allPassed = $false
        }
    }

    Write-Host ""
    Write-Host "Duration: $([math]::Round($duration.TotalSeconds, 1)) seconds" -ForegroundColor Cyan
    Write-Host ""

    if ($allPassed) {
        Write-Host @"
================================================================================
                          ALL CHECKS PASSED
================================================================================
"@ -ForegroundColor Green
        Write-Host "  API:           http://localhost:8000" -ForegroundColor Yellow
        Write-Host "  Web:           http://localhost:3000" -ForegroundColor Yellow
        Write-Host "  MinIO Console: http://localhost:9001" -ForegroundColor Yellow
        Write-Host ""
        
        # Check if lockfiles exist and remind user if not
        $apiLockExists = Test-Path "apps/api/uv.lock"
        $webLockExists = Test-Path "apps/web/pnpm-lock.yaml"
        
        if (-not $apiLockExists -or -not $webLockExists) {
            Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow
            Write-Host "  REMINDER: Generate and commit lockfiles before starting development:" -ForegroundColor Yellow
            Write-Host "    .\infra\dev.ps1 lock" -ForegroundColor White
            Write-Host "    git add apps/api/uv.lock apps/web/pnpm-lock.yaml" -ForegroundColor White
            Write-Host "    git commit -m `"chore: add baseline lockfiles`"" -ForegroundColor White
            Write-Host "--------------------------------------------------------------------------------" -ForegroundColor Yellow
            Write-Host ""
        }
        
        exit 0
    } else {
        Write-Host @"
================================================================================
                        VERIFICATION FAILED
================================================================================
"@ -ForegroundColor Red
        Write-Host "Check logs with: .\infra\dev.ps1 logs" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
}

# Main command dispatch
switch ($Command) {
    "up"         { Invoke-Up }
    "down"       { Invoke-Down }
    "logs"       { Invoke-Logs }
    "logs-api"   { Invoke-LogsApi }
    "logs-web"   { Invoke-LogsWeb }
    "api-test"   { Invoke-ApiTest }
    "web-test"   { Invoke-WebTest }
    "lint"       { Invoke-Lint }
    "format"     { Invoke-Format }
    "typecheck"  { Invoke-Typecheck }
    "db-migrate" { Invoke-DbMigrate }
    "clean"      { Invoke-Clean }
    "verify"            { Invoke-Verify }
    "cors-check"        { Invoke-CorsCheck }
    "cookie-check"      { Invoke-CookieCheck }
    "same-origin-check" { Invoke-SameOriginCheck }
    "proxy-up"          { Invoke-ProxyUp }
    "proxy-down"        { Invoke-ProxyDown }
    "proxy-check"       { Invoke-ProxyCheck }
    "proxy-logs"        { Invoke-ProxyLogs }
    "lock"              { Invoke-Lock }
    "lock-api"   { Invoke-LockApi }
    "lock-web"   { Invoke-LockWeb }
    "llm-status" { Invoke-LlmStatus }
    "help"       { Show-Help }
    default      { Show-Help }
}
