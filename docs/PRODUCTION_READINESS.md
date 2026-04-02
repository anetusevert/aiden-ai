# Aiden.ai Production Readiness Gate

**Version:** 1.0  
**Document Type:** Enterprise Readiness Assessment  
**Audience:** Legal Operations, IT, Security, Procurement, Compliance  
**Last Updated:** January 2026  
**Classification:** Internal / Pre-Deployment Review

---

## 1. Purpose & Scope

### What This Document Is

This document is an authoritative assessment of the current production readiness state of Aiden.ai. It describes:

- What capabilities are implemented and validated
- What security and compliance controls are in place
- What limitations exist
- Under what conditions the system can be responsibly deployed

This document is **not** a roadmap, marketing material, or feature specification. It describes only what exists today.

### Who This Document Is For

| Audience | Primary Concern |
|----------|-----------------|
| **Legal Operations** | Workflow reliability, output traceability, audit requirements |
| **IT / Infrastructure** | Deployment modes, health monitoring, recovery procedures |
| **Security** | Authentication, session management, data isolation |
| **Procurement** | Deployment constraints, licensing dependencies, vendor risk |
| **Compliance** | Audit trails, data residency policy, evidence handling |

### What Decisions This Supports

This document supports decisions regarding:

1. **Pilot Authorization**: Can we deploy to a controlled group of internal users?
2. **Production Gate**: What additional controls are required for broader deployment?
3. **Risk Acceptance**: What limitations must be acknowledged before use?
4. **Vendor Assessment**: What can we verify about the system's controls?

---

## 2. Deployment Modes (Current)

### Supported Deployment Modes

| Mode | Status | Description |
|------|--------|-------------|
| **Local Development (Docker)** | ✔ Supported | Full stack via Docker Compose with hot-reload |
| **HTTPS Proxy Mode (Caddy)** | ✔ Supported | Same-origin deployment with TLS termination |
| **Cookie-Based Auth Mode** | ✔ Supported | httpOnly secure cookies with refresh rotation |

### Local Development Mode

**Configuration:**
- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- MinIO Console: `http://localhost:9001`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

**Verification Command:**
```powershell
.\infra\dev.ps1 verify
```

**Use Case:** Development, testing, demonstration environments.

### HTTPS Proxy / Same-Origin Mode

**Configuration:**
- Web: `https://localhost`
- API: `https://localhost/api`

**Architecture:**
```
Browser → https://localhost:443 → Caddy (TLS)
                                    ├── / → web-proxy:3000
                                    └── /api/* → api-proxy:8000
```

**Verification Command:**
```powershell
.\infra\dev.ps1 proxy-check
```

**Use Case:** Staging environments, Secure cookie testing, production-like validation.

### What Is NOT Supported

| Capability | Status | Notes |
|------------|--------|-------|
| Kubernetes deployment | ❌ Not implemented | No Helm charts or K8s manifests exist |
| Multi-region deployment | ❌ Not implemented | Single-region only |
| Blue-green deployment | ❌ Not implemented | No deployment automation |
| CDN / Edge caching | ❌ Not implemented | No edge configuration |
| External load balancer integration | ❌ Not implemented | Caddy is the only proxy tested |

---

## 3. Authentication & Session Security

### As-Implemented Authentication

| Mechanism | Implementation | Status |
|-----------|---------------|--------|
| Cookie-based auth | httpOnly cookies (`access_token`, `refresh_token`) | ✔ Implemented |
| Refresh token rotation | New token issued on each refresh, old revoked | ✔ Implemented |
| Token version invalidation | `user.token_version` field incremented on logout-all | ✔ Implemented |
| Logout-all semantics | Invalidates all sessions across devices | ✔ Implemented |
| Refresh reuse detection | All sessions revoked if revoked token reused | ✔ Implemented |
| Session tracking | `refresh_sessions` table with jti, IP, user_agent | ✔ Implemented |

### Cookie Security Configuration

| Cookie | Path | Flags |
|--------|------|-------|
| `access_token` | `/` | `HttpOnly`, `SameSite=Lax` |
| `refresh_token` | `/auth` (or `/api/auth` behind proxy) | `HttpOnly`, `SameSite=Lax` |

**Secure Flag Behavior:**
- Development: `Secure=false` (allows localhost without HTTPS)
- Staging/Production: `Secure=true` (enforced regardless of TLS termination)

### Token Lifetimes

| Token | Default Lifetime | Configurable |
|-------|-----------------|--------------|
| Access Token | 15 minutes | Yes (`ACCESS_TOKEN_EXPIRES_MINUTES`) |
| Refresh Token | 7 days | Yes (`REFRESH_TOKEN_EXPIRES_DAYS`) |

### Authentication Readiness Assessment

| Aspect | Pilot Ready | Production Ready | Notes |
|--------|-------------|------------------|-------|
| Cookie security | ✔ | ✔ | httpOnly, SameSite enforced |
| Session invalidation | ✔ | ✔ | Logout-all, token version |
| Replay protection | ✔ | ✔ | Refresh reuse detection |
| SSO / IdP integration | ❌ | ❌ | **Not implemented** |
| SAML / OIDC | ❌ | ❌ | **Not implemented** |
| MFA / 2FA | ❌ | ❌ | **Not implemented** |
| Password authentication | ❌ | ❌ | Dev-login only (must be disabled in production) |
| Rate limiting on auth | ❌ | ❌ | **Not implemented** |
| Account lockout | ❌ | ❌ | **Not implemented** |

**Critical Note:** The current authentication relies on a development login mechanism (`/auth/dev-login`). This endpoint **must** be disabled in production environments via the `ENABLE_DEV_LOGIN=false` environment variable. No production-grade password or SSO authentication is implemented.

---

## 4. Data Handling & Residency

### Data Storage Architecture

| Data Type | Storage Location | Encryption |
|-----------|-----------------|------------|
| User accounts, workspaces, tenants | PostgreSQL | At-rest via database configuration |
| Document metadata | PostgreSQL | At-rest via database configuration |
| Document files | MinIO / S3-compatible | Configurable per bucket policy |
| Document text (extracted) | PostgreSQL | At-rest via database configuration |
| Document chunks | PostgreSQL | At-rest via database configuration |
| Vector embeddings | PostgreSQL (pgvector) | At-rest via database configuration |
| Audit logs | PostgreSQL | At-rest via database configuration |
| Refresh sessions | PostgreSQL | At-rest via database configuration |

### Tenant / Workspace Isolation

**Enforcement Mechanism:** Query-level filtering on all data access.

All database queries include:
```python
.where(
    and_(
        Model.tenant_id == ctx.tenant.id,
        Model.workspace_id == ctx.workspace.id,
    )
)
```

**Isolation Guarantees:**
- Users can only access workspaces they have explicit membership in
- Documents are scoped to `tenant_id` + `workspace_id`
- Cross-tenant access is not possible through the API
- S3/MinIO storage keys include tenant/workspace path isolation:
  ```
  tenants/{tenant_id}/workspaces/{workspace_id}/documents/{document_id}/...
  ```

### Jurisdiction Tagging

Jurisdiction is tagged at three levels:

| Level | Field | Purpose |
|-------|-------|---------|
| Tenant | `primary_jurisdiction` | Organization default |
| Workspace | `jurisdiction_profile` | Workspace default (e.g., UAE_DEFAULT, DIFC_DEFAULT) |
| Document | `jurisdiction` | Per-document tagging (UAE, DIFC, ADGM, KSA) |

**Policy Enforcement:**
- Document uploads are validated against workspace policy `allowed_jurisdictions`
- Workflow requests are validated against policy constraints
- Violations return HTTP 403 with policy denial status

### Data Residency Policy

| Aspect | Current State |
|--------|---------------|
| Residency field | `data_residency_policy` on Tenant (UAE, KSA, GCC) |
| Physical enforcement | **NOT implemented** |
| Policy-level tagging | ✔ Implemented |

**Critical Distinction:**

- **What exists:** A `data_residency_policy` field that records the intended residency policy for compliance tracking purposes.
- **What does NOT exist:** Physical infrastructure routing that enforces data stays within a specific region. All data currently resides in a single PostgreSQL and MinIO instance.

This is a **policy declaration**, not a **technical enforcement**. Actual data residency guarantees require infrastructure-level controls that are not currently implemented.

---

## 5. AI Output Reliability Guarantees

### Evidence-First Architecture

Aiden.ai is designed as an **evidence-first** system. All AI outputs are constrained by:

1. **Evidence Threshold**: Minimum 3 evidence chunks required before any generation
2. **Strict Citation Enforcement**: Every paragraph must contain valid citations
3. **Post-Generation Filtering**: Uncited statements are removed automatically
4. **Deterministic Temperature**: All LLM calls use `temperature=0.0`

### Workflow Status Codes

| Status | Meaning | Exportable |
|--------|---------|------------|
| `SUCCESS` | Valid output with citations | ✔ Yes |
| `INSUFFICIENT_SOURCES` | < 3 evidence chunks found | ✔ Yes (with disclaimer) |
| `CITATION_VIOLATION` | Output failed citation enforcement | ❌ No |
| `POLICY_DENIED` | Request blocked by policy (HTTP 403) | ❌ No |
| `VALIDATION_FAILED` | JSON parse or schema failure | ❌ No |
| `GENERATION_FAILED` | LLM provider error | ❌ No |

### Citation Enforcement Rules

**Legal Research:**
- Every paragraph must have at least one citation `[1]`, `[2]`, etc.
- Paragraphs without citations are removed
- Invalid citation indices are stripped
- Minimum answer length: 50 characters after processing

**Contract Review:**
- Every finding must have valid citations in `issue` and `recommendation`
- Findings without citations are removed
- Summary is regenerated from findings if citations missing

**Clause Redlines:**
- Contract claims (statements about what contract says) must be cited
- Uncited contract claims trigger downgrade to `insufficient_evidence`
- Recommended/template text does not require citations

### Prompt Hashing & Traceability

| Component | Implementation |
|-----------|---------------|
| Hash algorithm | SHA256 |
| Hash format | 64-character hex string |
| Hash input | `"{system_prompt}\n---\n{prompt}"` |
| Storage | Response metadata (`meta.prompt_hash`) |
| Audit log | Logged with each workflow execution |
| Export | Included in traceability footer (truncated) |

### Why Aiden Refuses to Answer

Aiden will refuse to generate output when:

1. **Insufficient evidence:** Fewer than 3 relevant chunks found
2. **Policy violation:** Workflow, jurisdiction, or language not allowed
3. **Citation failure:** Generated response lacks valid citations after enforcement
4. **Authentication failure:** Invalid or expired session

These refusals are **deterministic** and **logged**.

### Why Repetition May Occur

With the **stub provider** (development mode):
- Responses are deterministic and template-based
- Same input produces identical output
- This is expected behavior for testing

With **production providers** (OpenAI, Anthropic):
- Temperature is set to 0.0 for consistency
- Same evidence + question produces similar (not identical) answers
- Minor variation is expected; significant variation indicates different evidence

### Hallucination Structural Constraints

| Constraint | Mechanism |
|------------|-----------|
| Evidence-only context | Only numbered evidence chunks provided to LLM |
| No external knowledge | System prompt forbids external information |
| Citation requirement | "Do NOT write paragraphs without citations" |
| Post-generation filter | Uncited paragraphs removed |
| Minimum evidence | Generation blocked if < 3 chunks |

**Claim:** Hallucination is structurally constrained but not eliminated. The citation enforcement removes unsourced claims post-generation, but the LLM may still produce incorrect interpretations of sourced evidence. Human review remains required.

---

## 6. Audit, Traceability & Compliance

### Audit Log Coverage

**Logged Actions:**

| Category | Actions |
|----------|---------|
| Authentication | `auth.dev_login`, `auth.logout`, `auth.logout_all`, `auth.refresh_reuse_detected` |
| Documents | `document.upload`, `document.download`, `document.extract.success`, `document.extract.fail` |
| Workflows | `workflow.run.success`, `workflow.run.fail` |
| Exports | `export.contract_review.success/fail`, `export.clause_redlines.success/fail` |
| Search | `search.chunks.success/fail`, `embeddings.reindex.success/fail` |
| Admin | `policy_profile.create/update`, `workspace.policy_profile.attach` |
| Membership | `membership.create`, `workspace.member.add/remove`, `workspace.member.role.update` |

### Audit Log Structure

| Field | Description |
|-------|-------------|
| `id` | UUID primary key |
| `tenant_id` | Tenant scope (required) |
| `workspace_id` | Workspace scope (optional) |
| `user_id` | Acting user (optional) |
| `request_id` | Correlation ID for request tracing |
| `action` | Action identifier (e.g., `workflow.run.success`) |
| `resource_type` | Type of resource affected |
| `resource_id` | UUID of affected resource |
| `status` | `success` or `fail` |
| `meta` | JSONB with action-specific details |
| `ip` | Client IP address |
| `user_agent` | Client user agent (truncated to 512 chars) |
| `created_at` | Timestamp (timezone-aware) |

### Audit Log Properties

| Property | Status |
|----------|--------|
| Append-only | ✔ Records never updated or deleted |
| Tenant-scoped | ✔ Only accessible within tenant |
| Admin-only access | ✔ Requires ADMIN role |
| Fail-safe logging | ✔ Logging errors do not break requests |
| Environment tracking | ✔ `meta.environment` added automatically |

### Export Traceability

Every exported document includes a **traceability footer**:

| Field | Description |
|-------|-------------|
| Workflow | Type (e.g., `CONTRACT_REVIEW_V1`) |
| Status | Result status |
| LLM Provider | Provider name or "N/A" |
| LLM Model | Model identifier |
| Prompt Hash | SHA256 hash (truncated) |
| Generated By | "Aiden.ai" |
| Environment | System environment |
| Disclaimer | Legal disclaimer text |

### Compliance Assessment

| Requirement | Status | Notes |
|-------------|--------|-------|
| Reviewable | ✔ | All actions logged with context |
| Reconstructable | ✔ | Prompt hash + evidence enables reconstruction |
| Explainable | ✔ | Citations trace to source evidence |
| Exportable | ✔ | DOCX exports with full traceability |
| Immutable audit | ✔ | Append-only audit log table |

---

## 7. Operational Safety

### Health Checks

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | API health with environment and LLM provider info |

**Health Response:**
```json
{
  "status": "healthy",
  "environment": "dev",
  "llm_provider": "stub",
  "llm_model": "stub-v1"
}
```

### Verification Commands

| Command | Purpose |
|---------|---------|
| `.\infra\dev.ps1 verify` | Full verification (build, health, tests, lint) |
| `.\infra\dev.ps1 cors-check` | CORS header validation |
| `.\infra\dev.ps1 cookie-check` | Auth cookie validation |
| `.\infra\dev.ps1 proxy-check` | HTTPS proxy validation |
| `.\infra\dev.ps1 llm-status` | LLM provider status |

### Safe Recovery Procedures

| Procedure | Risk | Command / Method |
|-----------|------|------------------|
| Restart API | Temporary outage | `docker compose restart api` |
| Clear user sessions | User must re-login | `POST /auth/logout-all` |
| Reindex document | Updates embeddings | `POST /admin/reindex/{doc}/{ver}` |
| Reindex with replace | Full regeneration | `POST /admin/reindex/{doc}/{ver}?replace=true` |

### Non-Destructive Operations

These operations are safe and reversible:

- Restarting containers
- Clearing browser cookies (user re-login)
- Logout-all for a user
- Reindexing documents
- Attaching different policy profiles

### Escalation-Required Operations

These operations require elevated access and carry risk:

| Operation | Risk Level | Escalation |
|-----------|------------|------------|
| Direct database DELETE | **High** - Permanent data loss | DBA required |
| Docker volume removal | **High** - All data lost | Platform admin |
| Database reset | **Critical** - All data lost | DBA + approval |
| Environment variable changes | **Medium** - Service disruption | Platform admin |

---

## 8. Explicit Non-Goals / Exclusions

This section documents capabilities that are **explicitly not implemented** and should not be assumed available.

### Document Processing

| Capability | Status | Notes |
|------------|--------|-------|
| OCR (Optical Character Recognition) | ❌ Not implemented | Scanned PDFs not searchable |
| Email ingestion | ❌ Not implemented | No email parsing or import |
| PDF export | ❌ Not implemented | DOCX only |
| Image extraction | ❌ Not implemented | Embedded images ignored |
| Table extraction | ❌ Not implemented | Tables converted to text |

### Collaboration

| Capability | Status | Notes |
|------------|--------|-------|
| Real-time collaboration | ❌ Not implemented | No simultaneous editing |
| Comments / annotations | ❌ Not implemented | No annotation layer |
| Document versioning conflicts | ❌ Not implemented | No merge/conflict resolution |
| Notifications | ❌ Not implemented | No email or push notifications |

### Legal AI Boundaries

| Capability | Status | Notes |
|------------|--------|-------|
| Autonomous legal advice | ❌ Not implemented | System provides analysis, not advice |
| Unsourced reasoning | ❌ Structurally prevented | Citation enforcement removes unsourced claims |
| Legal strategy recommendations | ❌ Not implemented | No strategic guidance |
| Outcome prediction | ❌ Not implemented | No case outcome predictions |
| External legal database search | ❌ Not implemented | Only searches uploaded documents |

### Infrastructure

| Capability | Status | Notes |
|------------|--------|-------|
| High availability | ❌ Not implemented | No HA configuration |
| Auto-scaling | ❌ Not implemented | Fixed container deployment |
| Disaster recovery | ❌ Not implemented | No automated DR |
| Geographic failover | ❌ Not implemented | Single-region only |
| Backup automation | ❌ Not implemented | Manual backup required |

### Integration

| Capability | Status | Notes |
|------------|--------|-------|
| SSO / SAML / OIDC | ❌ Not implemented | Placeholder interfaces only |
| Active Directory | ❌ Not implemented | No directory integration |
| Document management systems | ❌ Not implemented | No DMS connectors |
| E-signature integration | ❌ Not implemented | No signature workflows |
| Billing / metering | ❌ Not implemented | No usage tracking |

---

## 9. Pilot Readiness Matrix

| Capability | Pilot Ready | Production Ready | Notes |
|------------|-------------|------------------|-------|
| **Legal Research** | ✔ | ⚠ | Depends on LLM provider configuration |
| **Contract Review** | ✔ | ⚠ | Evidence-dependent; review mode affects depth |
| **Clause Redlines** | ✔ | ⚠ | Jurisdiction template coverage varies |
| **Cookie Authentication** | ✔ | ⚠ | SSO not implemented; dev-login must be disabled |
| **Session Security** | ✔ | ✔ | Token rotation and invalidation implemented |
| **Tenant Isolation** | ✔ | ✔ | Query-level enforcement validated |
| **Audit Logging** | ✔ | ✔ | Comprehensive coverage, append-only |
| **DOCX Export** | ✔ | ✔ | Evidence validation enforced |
| **Citation Enforcement** | ✔ | ✔ | Post-generation filtering active |
| **Evidence Thresholds** | ✔ | ✔ | Minimum 3 chunks enforced |
| **Health Monitoring** | ✔ | ⚠ | Basic endpoint only; no metrics/alerting |
| **Data Residency** | ⚠ | ❌ | Policy tagging only; no physical enforcement |
| **SSO/SAML/OIDC** | ❌ | ❌ | Not implemented |
| **MFA/2FA** | ❌ | ❌ | Not implemented |
| **OCR** | ❌ | ❌ | Not implemented |
| **High Availability** | ❌ | ❌ | Not implemented |
| **Automated Backup** | ❌ | ❌ | Not implemented |

### Legend

| Symbol | Meaning |
|--------|---------|
| ✔ | Ready for the indicated deployment stage |
| ⚠ | Conditional readiness; review notes |
| ❌ | Not ready; capability not implemented |

---

## 10. Final Readiness Statement

### Summary Assessment

Aiden.ai is suitable for **controlled enterprise pilots** and **internal legal team usage** under the following conditions:

1. **Authentication Constraints Acknowledged**
   - Dev-login mechanism must be disabled (`ENABLE_DEV_LOGIN=false`)
   - Users authenticate via the cookie-based flow
   - No SSO, MFA, or enterprise identity integration exists
   - Session security (rotation, invalidation) is implemented

2. **Data Handling Understood**
   - All data resides in a single PostgreSQL/MinIO deployment
   - Tenant/workspace isolation is enforced at query level
   - Data residency is policy-tagged, not physically enforced
   - No automated backup or disaster recovery

3. **AI Output Limitations Accepted**
   - Outputs are citation-constrained but require human review
   - System refuses answers when evidence is insufficient
   - Hallucination is structurally constrained, not eliminated
   - Temperature=0.0 provides consistency, not perfection

4. **Operational Readiness Confirmed**
   - Health check endpoints exist
   - Verification scripts validate deployment
   - Audit logging covers all significant actions
   - Safe recovery procedures are documented

### Deployment Authorization

**Authorized For:**
- Internal legal team pilots with informed users
- Controlled evaluation with limited document sets
- Non-production environments for integration testing
- Development and demonstration purposes

**Not Authorized For:**
- Unattended production deployment in regulated environments
- Deployments requiring SSO or enterprise identity
- Deployments requiring physical data residency guarantees
- Deployments requiring high availability or disaster recovery
- Use as a substitute for legal professional judgment

### Required Actions Before Production

The following must be implemented before production deployment in regulated environments:

1. SSO/OIDC identity integration
2. MFA/2FA for user authentication
3. Physical data residency enforcement (if required)
4. High availability and disaster recovery
5. Automated backup with validated restore
6. Rate limiting on authentication endpoints
7. Production monitoring and alerting
8. Security penetration testing

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | January 2026 | Platform Architecture | Initial release |

---

*This document describes the current implementation state of Aiden.ai. It does not constitute a commitment to future features or capabilities. All assessments are based on code review and documented behavior as of the date indicated.*
