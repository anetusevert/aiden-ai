# Aiden.ai Operations & Troubleshooting Runbook

**Version:** 1.0  
**Audience:** Engineers, IT, DevOps, Security  
**Last Updated:** January 2026

---

## Table of Contents

1. [Startup Modes](#startup-modes)
2. [Health & Verification Commands](#health--verification-commands)
3. [Authentication Issues](#authentication-issues)
4. [Indexing Issues](#indexing-issues)
5. [LLM Quality Issues](#llm-quality-issues)
6. [Export Failures](#export-failures)
7. [Policy & Access Denials](#policy--access-denials)
8. [Logs & Diagnostics](#logs--diagnostics)
9. [Safe Recovery Procedures](#safe-recovery-procedures)

---

## Startup Modes

### Standard Dev Mode (Cross-Origin)

Use standard mode for typical development with separate frontend and backend origins.

**Start:**
```powershell
.\infra\dev.ps1 up
# or
make up
```

**Configuration:**
```
Web:  http://localhost:3000
API:  http://localhost:8000
```

**Environment Variables:**
| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` |
| `API_ROOT_PATH` | (empty) |
| `ENVIRONMENT` | `dev` |

**When to Use:**
- Daily development
- Frontend and backend work
- API testing with Swagger UI
- When CORS debugging is needed

### HTTPS Proxy / Same-Origin Mode

Use proxy mode for testing secure cookies, same-origin behavior, or production-like setup.

**Start:**
```powershell
.\infra\dev.ps1 proxy-up
```

**Stop:**
```powershell
.\infra\dev.ps1 proxy-down
```

**Configuration:**
```
Web:  https://localhost
API:  https://localhost/api
```

**Environment Variables:**
| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | (unset - same-origin mode) |
| `NEXT_PUBLIC_API_PREFIX` | `/api` |
| `API_ROOT_PATH` | `/api` |
| `CORS_ORIGINS` | `https://localhost,http://localhost:3000` |

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│    └──► https://localhost:443                          │
│             │                                           │
│             ▼                                           │
│  ┌─────────────────┐                                   │
│  │     Caddy       │ (TLS termination)                 │
│  │  Reverse Proxy  │                                   │
│  └────────┬────────┘                                   │
│           │                                             │
│     ┌─────┴─────┐                                      │
│     ▼           ▼                                      │
│  /           /api/*                                    │
│     │           │                                      │
│     ▼           ▼                                      │
│ web-proxy   api-proxy                                  │
│ :3000       :8000                                      │
└─────────────────────────────────────────────────────────┘
```

**When to Use:**
- Testing Secure cookie flag behavior
- Testing SameSite=Lax cookie behavior
- Verifying same-origin API calls
- Production deployment rehearsal
- Debugging authentication across proxy

---

## Health & Verification Commands

### verify

**Command:**
```powershell
.\infra\dev.ps1 verify
```

**What It Does:**
1. ☐ Checks/creates `.env` from `.env.example`
2. ☐ Builds and starts all Docker services
3. ☐ Waits for API health (30 attempts, 2s intervals)
4. ☐ Waits for Web health (20 attempts, 2s intervals)
5. ☐ Runs API tests (pytest)
6. ☐ Runs linters (ruff + eslint)
7. ☐ Prints PASS/FAIL summary

**Expected Output:**
```
========================================
VERIFICATION SUMMARY
========================================
[PASS] Environment file
[PASS] Docker build
[PASS] API health check
[PASS] Web health check
[PASS] API tests
[PASS] Linting
========================================
ALL CHECKS PASSED
========================================
```

**Troubleshooting Failures:**
| Step Failed | Action |
|-------------|--------|
| Environment file | Check `.env.example` exists |
| Docker build | Run `docker compose logs` to see build errors |
| API health | Check `.\infra\dev.ps1 logs-api` |
| Web health | Check `.\infra\dev.ps1 logs-web` |
| API tests | Run `.\infra\dev.ps1 api-test` for details |
| Linting | Run `.\infra\dev.ps1 lint` for details |

### cors-check

**Command:**
```powershell
.\infra\dev.ps1 cors-check
```

**What It Does:**
1. ☐ Verifies API is running
2. ☐ Checks `/health` returns 200
3. ☐ Sends OPTIONS preflight to `/tenants`
4. ☐ Validates `Access-Control-Allow-Origin` includes `http://localhost:3000`
5. ☐ Validates `Access-Control-Allow-Methods` includes POST
6. ☐ Validates `Access-Control-Allow-Credentials` is present

**Expected Headers:**
```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
Access-Control-Allow-Credentials: true
```

**Common Fixes:**
- Ensure `CORS_ORIGINS` in `.env` includes your frontend origin
- Restart API after changing: `docker compose restart api`

### cookie-check

**Command:**
```powershell
.\infra\dev.ps1 cookie-check
```

**What It Does:**
1. ☐ Ensures API is running
2. ☐ Bootstraps a test tenant
3. ☐ Tests `/auth/dev-login`:
   - Verifies `access_token` cookie set
   - Verifies `refresh_token` cookie set
   - Checks `HttpOnly` flag
   - Checks `SameSite=Lax`
   - Checks cookie paths (`/` and `/auth`)
4. ☐ Tests `/auth/me` with cookies
5. ☐ Tests `/auth/refresh` token rotation
6. ☐ Tests `/auth/logout` cookie clearing

**Cookie Validation:**
| Cookie | Path | Flags |
|--------|------|-------|
| `access_token` | `/` | `HttpOnly`, `SameSite=Lax` |
| `refresh_token` | `/auth` (or `/api/auth` behind proxy) | `HttpOnly`, `SameSite=Lax` |

### same-origin-check

**Command:**
```powershell
.\infra\dev.ps1 same-origin-check
```

**What It Does:**
1. ☐ Checks Web API URL configuration
2. ☐ Verifies `NEXT_PUBLIC_API_PREFIX` default (`/api`)
3. ☐ Verifies Web `api.ts` has same-origin helpers:
   - `getApiPrefix()`
   - `isSameOriginMode()`
   - `getApiConfig()`
4. ☐ Verifies API `root_path` configuration in `main.py`
5. ☐ Tests API with `root_path` simulation

**Purpose:** Validates application readiness for deployment behind a reverse proxy.

### proxy-check

**Command:**
```powershell
.\infra\dev.ps1 proxy-check
```

**Prerequisites:** Run `.\infra\dev.ps1 proxy-up` first.

**What It Does:**
1. ☐ Checks proxy services running (`caddy`, `api-proxy`, `web-proxy`)
2. ☐ Checks Web at `https://localhost` returns 200
3. ☐ Checks API health at `https://localhost/api/health` returns 200
4. ☐ Tests cookie auth through proxy:
   - Bootstrap tenant
   - Login via `/api/auth/dev-login`
   - Verify cookies set through proxy
   - Test `/api/auth/me` via proxy
   - Test `/api/auth/refresh` via proxy
5. ☐ Verifies TLS configuration

---

## Authentication Issues

### Token Revoked Behavior

**Symptom:** API returns 401 Unauthorized, user was previously logged in.

**Possible Causes:**
1. Access token expired (15-minute lifetime)
2. Refresh token expired (7-day lifetime)
3. User's `token_version` was incremented (logout-all)
4. Refresh token reuse detected (security measure)

**Diagnosis:**
```powershell
# Check audit logs for auth events
docker compose exec api python -c "
from src.database import SessionLocal
from src.models import AuditLog
db = SessionLocal()
logs = db.query(AuditLog).filter(
    AuditLog.action.like('auth.%')
).order_by(AuditLog.created_at.desc()).limit(10).all()
for log in logs:
    print(f'{log.created_at}: {log.action} - {log.status}')
"
```

**Resolution:**
- Normal expiration → User should re-login
- Token version increment → Expected after logout-all
- Reuse detection → All sessions revoked; user must re-login

### Refresh Reuse Detection

**Symptom:** User logged out of all devices unexpectedly, audit log shows `auth.refresh_reuse_detected`.

**What Happened:**
A previously-revoked refresh token was reused. This is a potential token theft indicator, so Aiden invalidates ALL user sessions as a security precaution.

**Audit Log Entry:**
```
action: auth.refresh_reuse_detected
meta: { "jti": "...", "revoked_count": N }
```

**Resolution:**
1. Investigate potential token compromise
2. User should re-login on all devices
3. Consider password reset if theft suspected

### Logout-All Semantics

**Behavior:**
When a user triggers "Logout All Devices":

1. User's `token_version` is incremented (invalidates all access tokens)
2. All active refresh sessions are revoked (`revoked_at` set)
3. Current session cookies are cleared
4. Audit event logged with session count

**Audit Log Entry:**
```
action: auth.logout_all
status: success
meta: { "revoked_session_count": N }
```

### Cookie Path Mismatches

**Symptom:** Auth works in standard mode but fails behind proxy.

**Check Cookie Paths:**
| Mode | access_token Path | refresh_token Path |
|------|-------------------|-------------------|
| Standard | `/` | `/auth` |
| Proxy | `/` | `/api/auth` |

**Diagnosis:**
```powershell
# In browser DevTools > Application > Cookies
# Verify refresh_token path matches your mode
```

**Common Issues:**
- Mismatch between `API_ROOT_PATH` and expected cookie path
- Caddy not forwarding cookies correctly
- `COOKIE_SECURE=true` but accessing via HTTP

---

## Indexing Issues

### Reindex Started But Status Unchanged

**Symptom:** Admin triggered reindex, but `is_indexed` remains `False`.

**Possible Causes:**
1. Embedding generation failed
2. No chunks exist for the document version
3. Database transaction rolled back

**Diagnosis:**
```powershell
# Check API logs for indexing errors
.\infra\dev.ps1 logs-api | Select-String -Pattern "embed|index|chunk"

# Check document version status directly
docker compose exec api python -c "
from src.database import SessionLocal
from src.models import DocumentVersion
db = SessionLocal()
version = db.query(DocumentVersion).filter_by(id='YOUR_VERSION_ID').first()
print(f'is_indexed: {version.is_indexed}')
print(f'indexed_at: {version.indexed_at}')
print(f'embedding_model: {version.embedding_model}')
"
```

**Resolution:**
1. Verify chunks exist for the version
2. Check embedding provider configuration
3. Retry reindex with `replace=true`

### pgvector Availability

**Symptom:** Vector search fails, errors mention `vector` type.

**Check pgvector Extension:**
```sql
-- In PostgreSQL
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**If Missing:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Docker Compose Note:** The PostgreSQL image should include pgvector. If not:
```yaml
# In docker-compose.yml
postgres:
  image: pgvector/pgvector:pg16
```

### Empty Chunk Cases

**Symptom:** Document uploaded but no chunks created.

**Possible Causes:**
1. Document has no extractable text (scanned PDF)
2. Extraction failed silently
3. Text was all whitespace

**Diagnosis:**
```powershell
# Check chunk count for a version
docker compose exec api python -c "
from src.database import SessionLocal
from src.models import DocumentChunk
db = SessionLocal()
count = db.query(DocumentChunk).filter_by(version_id='YOUR_VERSION_ID').count()
print(f'Chunk count: {count}')
"
```

**Resolution:**
1. Verify PDF has selectable text
2. Check extraction logs in API output
3. Re-upload with text-based PDF

### Safe Reindex Procedures

**Reindex with Skip (Non-Destructive):**
```powershell
# Only generates embeddings for chunks that don't have them
curl -X POST "http://localhost:8000/admin/reindex/{document_id}/{version_id}" \
  -H "Cookie: access_token=..."
```

**Reindex with Replace (Full Regeneration):**
```powershell
# Deletes existing embeddings and regenerates all
curl -X POST "http://localhost:8000/admin/reindex/{document_id}/{version_id}?replace=true" \
  -H "Cookie: access_token=..."
```

**Verify Success:**
```powershell
# Check version status after reindex
curl "http://localhost:8000/documents/{document_id}/versions/{version_id}" \
  -H "Cookie: access_token=..."
# Look for: "is_indexed": true, "indexed_at": "..."
```

---

## LLM Quality Issues

### Stub Provider vs OpenAI Provider

**Identify Active Provider:**
```powershell
.\infra\dev.ps1 llm-status
# or
curl http://localhost:8000/health
# Response includes: "llm_provider": "stub" or "openai"
```

**Stub Provider Indicators:**
- Model name: `stub-v1`
- Responses are deterministic/template-based
- Contains `[Analysis ID: xxxxxxxx]` marker
- Responses may appear repetitive

**OpenAI Provider Indicators:**
- Model name: `gpt-4o-mini`, `gpt-4o`, etc.
- Varied, contextual responses
- Full prompt hash in metadata

### How to Confirm Provider in Use

**Option 1: Health Endpoint**
```powershell
curl http://localhost:8000/health | ConvertFrom-Json | Select-Object llm_provider, llm_model
```

**Option 2: Environment Check**
```powershell
docker compose exec api env | Select-String LLM
```

**Option 3: Response Metadata**
```json
{
  "meta": {
    "provider": "stub",
    "model": "stub-v1",
    "prompt_hash": "abc12345..."
  }
}
```

### Prompt Hash Meaning

**What It Is:**
- SHA256 hash of the combined system + user prompt
- Used for traceability without storing raw prompts
- Appears in response metadata and exports

**Format:**
- Full hash: 64 hex characters (e.g., `a1b2c3d4...`)
- Stub mode: 8 characters (e.g., `a1b2c3d4`)
- Export display: First 16 characters + `...`

**Use Cases:**
- Correlate responses with audit logs
- Debug prompt consistency
- Verify deterministic behavior

### Why Answers May Appear Repetitive

**With Stub Provider:**
- Expected behavior; stub returns template responses
- Same input → same output (deterministic)
- Enable OpenAI provider for varied responses

**With OpenAI Provider:**
- Temperature is set to 0.0 (deterministic)
- Same evidence + question → similar answers
- This is intentional for consistency

**To Enable OpenAI:**
```bash
# In .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-your-api-key-here
```

Then restart: `docker compose restart api`

---

## Export Failures

### Evidence Validation Errors

**Symptom:** Export returns 400 with `error_code: "export_validation_failed"`

**Error Response:**
```json
{
  "error_code": "export_validation_failed",
  "message": "Some evidence chunks are invalid or inaccessible",
  "invalid_count": 2,
  "valid_count": 5
}
```

**Possible Causes:**
1. Chunk IDs don't exist in database
2. Chunks belong to different document/version
3. Chunks belong to different workspace/tenant

**Diagnosis:**
1. Check the workflow result for chunk IDs
2. Verify chunks exist:
```powershell
docker compose exec api python -c "
from src.database import SessionLocal
from src.models import DocumentChunk
db = SessionLocal()
chunk = db.query(DocumentChunk).filter_by(id='CHUNK_ID').first()
print(f'Found: {chunk is not None}')
if chunk:
    print(f'Document ID: {chunk.document_id}')
    print(f'Version ID: {chunk.version_id}')
"
```

### Invalid Chunk References

**Symptom:** Citations reference non-existent chunks.

**Common Causes:**
1. Document was re-indexed, invalidating old chunk IDs
2. Stale workflow result from previous session
3. Document version was deleted

**Resolution:**
1. Re-run the workflow to generate fresh results
2. Export the new result

### Filename Sanitization Rules

**Sanitization Applied:**
| Original | Sanitized |
|----------|-----------|
| `Contract (2024).pdf` | `Contract_2024_` |
| `My File!@#$.docx` | `My_File____` |
| `Very Long Title That Exceeds Fifty Characters In Total` | `Very_Long_Title_That_Exceeds_Fi` |

**Rules:**
1. Keep: alphanumeric, spaces, hyphens, underscores
2. Replace other characters with `_`
3. Truncate to 50 characters
4. Append: `_{workflow}_{date}.docx`

**Final Format:** `{sanitized_title}_{workflow}_{YYYYMMDD}.docx`

---

## Policy & Access Denials

### Workflow Not Allowed

**Symptom:** 403 response with message about workflow not allowed.

**Error Example:**
```json
{
  "detail": "Workflow 'LEGAL_RESEARCH_V1' is not allowed by the current policy"
}
```

**Diagnosis:**
```powershell
# Check effective policy for workspace
curl "http://localhost:8000/policy/resolve" \
  -H "Cookie: access_token=..."
```

**Resolution:**
1. **ADMIN action required:** Update policy profile to include workflow
2. Or attach different policy profile to workspace

**Current Workflows:**
- `LEGAL_RESEARCH_V1`
- `CONTRACT_REVIEW_V1`
- `CLAUSE_REDLINES_V1`

### Role Enforcement

**Role Hierarchy:**
```
ADMIN (3) > EDITOR (2) > VIEWER (1)
```

**Endpoint Requirements:**
| Action | Minimum Role |
|--------|--------------|
| View documents | VIEWER |
| Download documents | VIEWER |
| Export results | VIEWER |
| Upload documents | EDITOR |
| Run workflows | EDITOR |
| Reindex documents | ADMIN |
| Manage members | ADMIN |
| Attach policies | ADMIN |
| View audit logs | ADMIN |

**Check User Role:**
```powershell
curl "http://localhost:8000/auth/me" \
  -H "Cookie: access_token=..."
# Response includes: "role": "VIEWER|EDITOR|ADMIN"
```

### Workspace / Tenant Isolation

**Isolation Guarantees:**
- Users can only access data in workspaces they're members of
- Documents are scoped to `tenant_id` + `workspace_id`
- Cross-tenant access is impossible (enforced at database level)

**If Access Denied:**
1. Verify user is member of the workspace
2. Verify workspace belongs to user's tenant
3. Check membership hasn't been revoked

---

## Logs & Diagnostics

### API Logs

**View API Logs:**
```powershell
.\infra\dev.ps1 logs-api
# or
docker compose logs -f api
```

**Key Log Patterns:**
| Pattern | Meaning |
|---------|---------|
| `INFO:uvicorn.access` | HTTP requests |
| `ERROR:` | Application errors |
| `auth.` | Authentication events |
| `workflow.` | Workflow execution |
| `embed` | Embedding operations |

**Filter by Request ID:**
```powershell
docker compose logs api | Select-String "request_id=YOUR_ID"
```

### Audit Log Interpretation

**Access Audit Logs (ADMIN only):**
```powershell
curl "http://localhost:8000/audit?limit=50" \
  -H "Cookie: access_token=..."
```

**Common Audit Actions:**

| Action | Meaning |
|--------|---------|
| `auth.dev_login` | Development login attempt |
| `auth.logout` | User logged out |
| `auth.logout_all` | All sessions invalidated |
| `auth.refresh_reuse_detected` | Potential token theft |
| `document.upload` | Document uploaded |
| `document.extract.success` | Text extraction succeeded |
| `document.extract.fail` | Text extraction failed |
| `workflow.run.success` | Workflow completed |
| `workflow.run.fail` | Workflow failed |
| `export.contract_review.success` | Export generated |
| `embeddings.reindex.success` | Reindex completed |

**Query Parameters:**
- `workspace_id` - Filter by workspace
- `action` - Filter by action type
- `limit` - Max entries (default 50, max 200)

### Proxy / Caddy Logs

**View Caddy Logs:**
```powershell
.\infra\dev.ps1 proxy-logs
# or
docker compose logs caddy
```

**Key Caddy Log Entries:**
```
"GET /api/health HTTP/2.0" 200     # Successful API request
"GET / HTTP/2.0" 200                # Successful Web request
"TLS handshake error"              # Certificate issue
```

**All Proxy Services:**
```powershell
docker compose --profile proxy logs -f
```

---

## Safe Recovery Procedures

### Clearing Sessions

**Single User Session Clear:**
```powershell
# User should click "Logout" in the UI
# or call:
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Cookie: access_token=...; refresh_token=..."
```

**All Sessions for User (Logout-All):**
```powershell
curl -X POST "http://localhost:8000/auth/logout-all" \
  -H "Cookie: access_token=..."
```

**Database Session Clear (Emergency):**
```sql
-- Revoke all sessions for a user
UPDATE refresh_sessions
SET revoked_at = NOW()
WHERE user_id = 'USER_UUID' AND revoked_at IS NULL;

-- Increment token version to invalidate access tokens
UPDATE users
SET token_version = token_version + 1
WHERE id = 'USER_UUID';
```

### Re-Login Flow

**Standard Re-Login:**
1. User navigates to `/login`
2. Enters tenant ID, workspace ID, email
3. System issues new access + refresh tokens
4. Cookies are set automatically

**Forced Re-Login (After Logout-All):**
1. All existing sessions are invalid
2. User must complete full login flow
3. New session is completely independent

### Non-Destructive Fixes Checklist

**Before making changes, verify:**
- [ ] Issue can be reproduced
- [ ] Audit logs have been reviewed
- [ ] No data will be lost

**Safe Operations:**
| Operation | Impact | Reversible |
|-----------|--------|------------|
| Restart API | Temporary outage | Yes (automatic) |
| Clear browser cookies | User must re-login | Yes (re-login) |
| Logout-all for user | User sessions cleared | Yes (re-login) |
| Reindex document | Updates embeddings | Yes (re-reindex) |
| Attach new policy | Changes permissions | Yes (re-attach old) |

**Avoid Without Backup:**
| Operation | Impact |
|-----------|--------|
| DELETE FROM documents | Permanent data loss |
| DROP TABLE | Permanent data loss |
| Reset database | All data lost |
| Remove docker volumes | All data lost |

### Emergency Contacts

For issues requiring elevated access or database operations, escalate to:
1. Platform administrator
2. Database administrator
3. Security team (for auth/token issues)

---

## Quick Reference

### Common Commands

```powershell
# Start/Stop
.\infra\dev.ps1 up                 # Start standard mode
.\infra\dev.ps1 down               # Stop all services
.\infra\dev.ps1 proxy-up           # Start HTTPS proxy mode
.\infra\dev.ps1 proxy-down         # Stop proxy services

# Health Checks
.\infra\dev.ps1 verify             # Full verification
.\infra\dev.ps1 cors-check         # CORS validation
.\infra\dev.ps1 cookie-check       # Auth cookie validation
.\infra\dev.ps1 proxy-check        # Proxy stack validation

# Logs
.\infra\dev.ps1 logs               # All services
.\infra\dev.ps1 logs-api           # API only
.\infra\dev.ps1 logs-web           # Web only
.\infra\dev.ps1 proxy-logs         # Caddy proxy

# Testing
.\infra\dev.ps1 api-test           # Run API tests
.\infra\dev.ps1 lint               # Run linters

# LLM
.\infra\dev.ps1 llm-status         # Check active provider
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `dev` | Environment (dev/staging/prod) |
| `API_HOST` | `0.0.0.0` | API bind host |
| `API_PORT` | `8000` | API port |
| `API_ROOT_PATH` | (empty) | Root path for proxy mode |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `LLM_PROVIDER` | `stub` | LLM provider (stub/openai) |
| `LLM_MODEL` | (none) | LLM model name |
| `LLM_API_KEY` | (none) | OpenAI API key |
| `JWT_SECRET` | (dev secret) | JWT signing secret |
| `ACCESS_TOKEN_EXPIRES_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRES_DAYS` | `7` | Refresh token lifetime |
| `COOKIE_SECURE` | (auto) | Secure cookie flag |

---

*This runbook documents operational procedures for the Aiden.ai system. For end-user documentation, see the [Review Manual](REVIEW_MANUAL.md).*
