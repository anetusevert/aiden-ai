# Aiden.ai Web

Next.js frontend for Aiden.ai - AI-powered legal research with strict citation enforcement.

## Features

- **Tenant Bootstrap**: Create tenant, workspace, and admin user in one step
- **Workspace Templates**: Pre-configured templates for GCC jurisdictions (UAE + KSA)
- **GCC Jurisdiction Parity**: UAE and KSA as first-class tenants with equal support
- **Arabic-First Mode**: KSA templates default to Arabic output language
- **Dev Login**: Passwordless JWT authentication for development
- **Document Vault**: Upload, list, and manage documents with version control
- **Legal Research**: Ask legal questions and get cited answers from your documents

## Getting Started

### Prerequisites

- Node.js 18+ with pnpm (enable via `corepack enable` then `corepack prepare pnpm@latest --activate`)
- Docker and Docker Compose (for full stack)
- API running at `http://localhost:8000` (or via Docker)

### Running with Docker Compose (Recommended)

From the project root:

```powershell
# Start all services (API + Web + Database + MinIO)
docker compose up -d

# View logs
docker compose logs -f web

# Access the web app
# http://localhost:3000
```

### Running Locally (Development)

```powershell
# Navigate to web directory
cd apps\web

# Install dependencies
pnpm install

# Create .env file (copy from example)
copy .env.example .env

# Start development server
pnpm dev

# Access at http://localhost:3000
```

## Environment Variables

| Variable                   | Description                                | Default                 |
| -------------------------- | ------------------------------------------ | ----------------------- |
| `NEXT_PUBLIC_API_BASE_URL` | API URL for browser requests               | `http://localhost:8000` |
| `API_INTERNAL_BASE_URL`    | API URL for SSR requests (Docker internal) | `http://api:8000`       |

**Important**: In Docker, the web container uses `API_INTERNAL_BASE_URL` for server-side requests because it can resolve Docker service names. The browser uses `NEXT_PUBLIC_API_BASE_URL` which must be a host-accessible URL.

## Pages

| Route              | Description                                           |
| ------------------ | ----------------------------------------------------- |
| `/`                | Home page with quick links and API health status      |
| `/setup`           | Bootstrap new tenant/workspace/admin with templates   |
| `/login`           | Dev login with tenant/workspace/email                 |
| `/documents`       | Document list and upload (with indexing status)       |
| `/documents/[id]`  | Document details, version history, and reindex        |
| `/documents/[id]/versions/[versionId]/viewer` | Document text viewer with chunk navigation |
| `/research`        | Legal research with question input and cited answers  |
| `/contract-review` | Contract review workflow with findings and evidence   |
| `/clause-redlines` | Clause library analysis with suggested redlines       |
| `/members`         | Workspace member management (Admin only)              |
| `/audit`           | Audit log viewer (Admin only)                         |
| `/account`         | User profile and session info                         |

## Demo Flow

### 1. Setup (Bootstrap with Template)

Navigate to `/setup` and fill in:

1. **Select Template** (required) - grouped by region:

   **UAE Templates:**
   - **UAE In-House (General Counsel)**: Full access to legal research and contract review
   - **UAE Procurement (Contract-heavy)**: Contract review only for procurement teams
   - **UAE Compliance**: Legal research only for compliance teams

   **KSA Templates:**
   - **KSA In-House (General Counsel)**: Full access for Saudi in-house legal teams (Arabic-first)
   - **KSA Procurement (Contract-heavy)**: Contract review for Saudi procurement (Arabic-first)

2. **Tenant Information** (auto-populated from template):
   - **Tenant Name**: e.g., "Demo Corp"
   - **Primary Jurisdiction**: Auto-set from template (can be overridden)
   - **Data Residency**: Auto-set from template (override shows warning)

3. **Admin User**:
   - **Email**: admin@example.com
   - **Full Name** (optional)

4. **Workspace**:
   - **Workspace Name**: e.g., "Main Workspace"
   - **Workspace Type**: In-House or Law Firm

Click "Create Tenant + Workspace + Policy" to bootstrap. The setup process will:

1. Create the tenant with workspace and admin user
2. Automatically sign you in
3. Create a policy profile based on the selected template
4. Attach the policy profile to the workspace
5. Store workspace context (including language defaults)
6. Redirect you to the documents page

You'll see a progress stepper showing each step's status. The template ID and workspace context are stored in localStorage for transparency.

### 2. Login (Manual - if needed)

If you've logged out or need to re-authenticate:

Navigate to `/login`. The tenant and workspace IDs should be pre-filled from setup.

- Enter your **email** (must match the admin email from setup)
- Click "Sign In"

You'll be redirected to the documents page upon successful authentication.

### 3. Upload Documents

Navigate to `/documents`:

- Click "Upload Document"
- Select a file (PDF, DOC, DOCX, or TXT)
- Fill in metadata:
  - Title
  - Document Type (contract, policy, memo, regulatory, other)
  - Jurisdiction
  - Language
  - Confidentiality level
- Click "Upload Document"

The document will be processed, text extracted, and chunks created for search.

### 4. Legal Research

Navigate to `/research`:

- Enter your legal question in the text area
- Optionally select:
  - Answer Language (English or Arabic)
  - Filters (jurisdiction, document type, source language)
- Click "Ask Question"

The response includes:

- **Status Badge**: Trust indicator showing workflow result status (see below)
- **Answer**: Generated text with inline citations [1], [2], etc.
- **Citations**: Mapping of citation numbers to source documents
- **Evidence**: Ranked chunks used to generate the answer
- **Meta**: Model info, chunk count, removed paragraph count (for strict citation enforcement)

### Workflow Status Badges

All workflow pages display a status badge at the top of results indicating the reliability of the output:

| Status | Badge Text | Description |
|--------|------------|-------------|
| `success` | **Verified Output** | All citations validated successfully |
| `insufficient_sources` | **Insufficient Evidence** | Not enough sources for confident output |
| `policy_denied` | **Policy Blocked** | Request blocked by workspace policy |
| `citation_violation` | **Citation Enforcement Reduced Output** | Output reduced due to citation validation failures |
| `validation_failed` / `generation_failed` | **Generation Failed** | LLM error or invalid response |

The badge is driven strictly by `meta.status` from the API response - no heuristics or client-side logic.

### 5. Contract Review

Navigate to `/documents`, click on a document, then click "Review" next to any version. Or access directly via `/contract-review?documentId=...&versionId=...`

**Review Settings**:

- **Playbook** (optional): Select a pre-configured playbook to auto-fill settings
- **Review Mode**: Quick (fast overview), Standard (balanced), or Deep (comprehensive)
- **Focus Areas**: Select areas to analyze (liability, termination, governing law, payment, IP, confidentiality)
- **Output Language**: English or Arabic

Click "Run Review" to analyze the contract.

The response includes:

- **Summary**: Overall assessment with inline citations [1], [2], etc.
- **Findings**: List of identified issues as cards showing:
  - Severity badge (critical, high, medium, low, info)
  - Category (e.g., liability, termination)
  - Title and description of the issue
  - Recommendation with citations
  - Expandable evidence snippets from the contract
- **Meta**: Review mode, model info, removed findings count (for strict citation enforcement)

**Note**: Contract review requires EDITOR or ADMIN role. VIEWER users cannot run reviews.

### 6. Clause Redlines

Navigate to `/documents`, click on a document, then click "Redlines" next to any version. Or access directly via `/clause-redlines?documentId=...&versionId=...`

**Analysis Settings**:

- **Playbook** (optional): Select a pre-configured playbook to auto-fill settings
- **Jurisdiction**: UAE, DIFC, ADGM, or KSA (defaults from workspace context)
- **Clause Types**: Select clause types to analyze (8 types: governing_law, termination, liability, indemnity, confidentiality, payment, ip, force_majeure)
- **Output Language**: English or Arabic

Click "Run Analysis" to analyze the contract for clauses and generate suggested redlines.

The response includes:

- **Summary**: Executive summary with inline citations [1], [2], etc.
- **Clause Cards**: List of analyzed clauses showing:
  - Status badge (found, missing, insufficient_evidence)
  - Severity badge (critical, high, medium, low)
  - Confidence score
  - Issue description with citations
  - Rationale with citations
  - Recommended Text block (suggested redline)
  - Expandable evidence snippets from the contract
- **Meta**: Jurisdiction, model info, evidence chunk count, downgraded/removed counts

**Note**: Clause redlines requires EDITOR or ADMIN role. VIEWER users cannot run the analysis.

### 7. Export Results to DOCX

Both Contract Review and Clause Redlines support exporting results to Microsoft Word (DOCX) format.

**How to Export:**

1. Run a Contract Review or Clause Redlines analysis
2. When results are displayed, look for the **Download DOCX** button in the top-right corner
3. Click the button to download the DOCX file

**Button States:**

| State | Description |
|-------|-------------|
| Enabled (Blue) | Export available - workflow completed successfully |
| Disabled (Gray) | Export not available - workflow failed or has unsupported status |
| Spinning | Export in progress |

**Exportable Statuses:**

Only `success` and `insufficient_sources` results can be exported. Other statuses (e.g., `generation_failed`, `citation_violation`) cannot be exported.

**DOCX Document Contents:**

1. **Cover Page**: Document title, workspace, tenant, jurisdiction, timestamp, confidentiality notice
2. **Executive Summary**: Workflow summary with citations (plus disclaimer if insufficient sources)
3. **Findings/Clause Analysis**: Detailed breakdown with severity, citations, and evidence
4. **Citations Section**: Numbered list mapping to source chunks
5. **Evidence Appendix**: Full text snippets from the contract
6. **Traceability Footer**: Workflow name, LLM provider/model, prompt hash, environment

**Filename Format:**

```
<DocumentTitle>_<workflow>_<YYYYMMDD>.docx
```

Example: `Employment_Agreement_contract-review_20260125.docx`

**Legal Disclaimer:**

Exported documents include a legal disclaimer stating:
- The document does NOT constitute legal advice
- Users should consult qualified legal counsel
- Accuracy depends on source document quality

#### Contract Review Playbooks

Playbooks provide pre-configured settings for common contract review scenarios. Selecting a playbook automatically sets the review mode, focus areas, output language, and displays a guidance hint.

**Available Playbooks:**

| Playbook | Region | Review Mode | Focus Areas | Output Language | Guidance Hint |
|----------|--------|-------------|-------------|-----------------|---------------|
| UAE Procurement MSA | UAE | Standard | Liability, Termination, Payment, Governing Law | English | Prioritize UAE governing law clauses, DIFC/ADGM considerations, and standard procurement terms. |
| UAE NDA | UAE | Quick | Confidentiality, Termination, Governing Law | English | Focus on confidentiality scope, permitted disclosures, term/survival periods, and UAE law compliance. |
| KSA Procurement MSA | KSA | Standard | Liability, Termination, Payment, Governing Law | Arabic | Prioritize Saudi law compliance, Sharia considerations, and government procurement regulations. |
| KSA NDA | KSA | Quick | Confidentiality, Termination, Governing Law | Arabic | Focus on confidentiality under Saudi law, Arabic language requirements, and KSA jurisdiction clauses. |

**Using Playbooks:**

1. Navigate to `/contract-review` with a document
2. Select a playbook from the dropdown at the top of the settings panel
3. Review the auto-filled settings and the displayed guidance hint
4. Optionally adjust settings manually
5. Click "Run Review"
6. Use "Reset to workspace defaults" to clear the playbook and return to manual configuration

**Notes:**

- Playbooks are defined in `src/lib/contractPlaybooks.ts`
- The playbook hint is sent to the backend and prepended to the LLM prompt for enhanced guidance
- KSA playbooks default to Arabic output language (Arabic-first)
- You can manually override any auto-filled setting before running the review

### 6. Document Text Viewer (Evidence Navigation)

The Document Text Viewer allows users to navigate to the source of evidence chunks from workflow results.

**Accessing the Viewer:**

There are two ways to access the viewer:

1. **From Evidence Links**: Click "View in Document" next to any evidence snippet in:
   - Legal Research results (citations and evidence chunks)
   - Contract Review findings (evidence accordions)
   - Clause Redlines analysis (evidence accordions)

2. **Direct URL**: Navigate directly to `/documents/{documentId}/versions/{versionId}/viewer`

**Deep Linking with Query Parameters:**

The viewer supports jump-to-chunk via query parameters:

- `?chunkId={id}` - Jump to a specific chunk by its UUID
- `?chunkIndex={n}` - Jump to a chunk by its index number

Example: `/documents/abc123/versions/def456/viewer?chunkId=chunk789`

**Viewer Features:**

- **Left Sidebar**: List of all document chunks with:
  - Chunk index and character range
  - Text preview (first 150 characters)
  - Page numbers (if available)
  - Search/filter input to find chunks by content

- **Main Content Area**: Selected chunk details with:
  - Full chunk text with line wrapping
  - Character offset and page info
  - Context: Previous and next chunk previews
  - Navigation buttons (Prev/Next)

- **Auto-scrolling**: When a chunk is selected (via click or deep link), the sidebar automatically scrolls to highlight it.

**Demo: Click Evidence to Jump to Chunk**

1. Run a Legal Research query from `/research`
2. In the results, find an evidence chunk
3. Click "View in Document" link
4. The viewer opens with that chunk selected and highlighted
5. Use Prev/Next buttons to navigate through the document
6. Use the search box to filter chunks by content

**Access Control:**

- Requires VIEWER role or higher
- Uses JWT authentication (same as other pages)
- Returns 404 if document/version not found
- Returns 403 if user lacks permission

### 7. Manage Workspace Members (Admin Only)

Navigate to `/members` (visible in navigation only for ADMIN users):

**Member List:**

- Displays all workspace members with:
  - Name and email
  - Current role (with badge)
  - Active status
  - Join date
- Members can view the list (transparency) but only admins can make changes

**Invite New Member:**

1. Click "Invite Member" button
2. Fill in the invite form:
   - **Email** (required): The user's email address
   - **Full Name** (optional): For new users
   - **Role**: VIEWER, EDITOR, or ADMIN
3. Click "Send Invite"

**Notes:**
- If the user exists in the tenant, they're added to the workspace
- If not, a new user is created (dev "invite" - no email is sent)
- Each email can only be added once per workspace

**Update Member Role:**

- Click the role dropdown next to any member (except yourself)
- Select the new role (VIEWER, EDITOR, or ADMIN)
- The role is updated immediately

**Remove Member:**

- Click "Remove" next to any member (except yourself)
- The member is immediately removed from the workspace

**Restrictions:**
- Cannot remove yourself
- Cannot remove/demote the last admin (at least one admin must remain)
- Non-admin users see the list but cannot make changes

### 8. View Audit Log (Admin Only)

Navigate to `/audit` (visible in navigation only for ADMIN users):

Member management actions are logged:
- `workspace.member.add`: Member invited/added
- `workspace.member.role.update`: Role changed
- `workspace.member.remove`: Member removed

- **Filters**:
  - **Action (contains)**: Filter by action type (e.g., `document.upload`, `auth.login`)
  - **Workspace ID**: Pre-filled with your current workspace, can be changed
- Click "Search" to fetch audit entries

The audit log displays:

- **Timestamp**: When the action occurred
- **Action**: The action type (e.g., `document.create`, `workflow.research`)
- **Status**: Success, failure, or pending
- **Resource**: Resource type and ID (truncated)
- **Request ID**: For correlation with backend logs

**Note**: Non-admin users will see an "Admin Only" message.

### 9. Reindex a Document Version (Admin Only)

Navigate to `/documents`, then click on any document to view its details.

**Viewing Indexing Status**:

- Each version shows its indexing status:
  - **Indexed**: Green badge with indexed timestamp and embedding model
  - **Not indexed**: Gray badge indicating the version needs indexing

**Reindexing a Version** (Admin only):

1. Click the "Reindex" button next to any version
2. Wait for the reindexing to complete (button shows "Reindexing...")
3. A success/failure message will appear
4. The page refreshes to show updated indexing status

**Why Reindex?**:

- After changing embedding models
- If indexing failed during initial upload
- To refresh embeddings after system updates

## Authentication

The web app uses **httpOnly cookie-based authentication** for enterprise security:

### How It Works

1. **Login**: User submits credentials to `/auth/dev-login`
2. **Cookies Set**: Backend sets `access_token` and `refresh_token` cookies (httpOnly)
3. **Requests**: All API requests include `credentials: "include"` for cookie transmission
4. **Refresh**: On 401, the client silently calls `/auth/refresh` and retries
5. **Logout**: Client calls `/auth/logout` which clears cookies and revokes session

### Security Features

- **No localStorage tokens**: Tokens are stored in httpOnly cookies, not accessible to JavaScript
- **XSS Protection**: Even if an attacker injects script, they cannot steal the tokens
- **Refresh Token Rotation**: Each refresh generates a new token, old one is revoked
- **Reuse Detection**: If a stolen refresh token is replayed, all sessions are revoked
- **SameSite=Lax**: CSRF protection while allowing normal navigation

### Same-Origin Target Architecture

The application is designed for same-origin deployment in production:

| Mode | Description | API URL |
|------|-------------|---------|
| **Cross-origin (dev)** | Web at :3000, API at :8000 | `http://localhost:8000` |
| **Same-origin (prod)** | Both at same origin via proxy | `/api` |

**Why Same-Origin?**
- No CORS complexity
- SameSite=Lax cookies work seamlessly
- No need for SameSite=None (which requires Secure and has browser restrictions)

**Environment Variables:**

```bash
# Cross-origin mode (current dev)
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Same-origin mode (production)
# NEXT_PUBLIC_API_BASE_URL=  (unset)
NEXT_PUBLIC_API_PREFIX=/api
```

**Verify:**

```powershell
.\infra\dev.ps1 same-origin-check
```

### What IS Stored in localStorage

Only non-sensitive context is stored:

| Key | Description |
|-----|-------------|
| `aiden_tenant_id` | Current tenant ID (for login pre-fill) |
| `aiden_workspace_id` | Current workspace ID (for login pre-fill) |
| `aiden_workspace_context` | Workspace language/jurisdiction defaults |

**Tokens are NEVER stored in localStorage.**

### Silent Refresh

The API client automatically handles token expiry:

1. Request returns 401
2. Client calls `/auth/refresh` (sends refresh_token cookie)
3. If successful, original request is retried
4. If refresh fails, user is redirected to `/login?reason=session_expired`

### Logout Flows

| Action | Effect |
|--------|--------|
| Sign Out | Clears cookies, revokes current session |
| Sign Out Everywhere | Clears cookies, revokes ALL sessions, increments token_version |

### Troubleshooting

**Cookies not being sent?**
- Ensure requests include `credentials: "include"`
- Check browser's cookie settings (third-party cookies, SameSite)
- In development, cookies work over HTTP localhost

**Getting 401 after refresh?**
- Check if token_version was incremented (admin action)
- Check if refresh token was revoked (security measure)
- Clear cookies and log in again

**CORS errors with credentials?**
- Backend must have `allow_credentials=True` in CORS config
- `Access-Control-Allow-Origin` cannot be `*` with credentials
- Frontend origin must be in allowed origins list

## Workspace Templates

Templates are pre-configured policy profiles for GCC in-house use cases. They are defined in `src/lib/workspaceTemplates.ts`.

### GCC Jurisdiction Parity

**UAE and KSA are first-class jurisdictions with equal template support.** Neither region is treated as a "default" - all defaults flow from the selected template.

Key principles:

1. **Template-Driven Defaults**: Primary jurisdiction, data residency, and default language are all derived from the selected template
2. **No Hardcoded Assumptions**: The setup flow does not assume any particular region
3. **Arabic-First for KSA**: KSA templates default to Arabic output language, reflecting local practice
4. **Policy Parity**: KSA policies are created, attached, and resolved identically to UAE - no branching logic by country

### Available Templates

| Template | Region | Workflows | Jurisdictions | Default Language |
| -------- | ------ | --------- | ------------- | ---------------- |
| UAE In-House (General Counsel) | UAE | LEGAL_RESEARCH_V1, CONTRACT_REVIEW_V1 | UAE, DIFC, ADGM | mixed |
| UAE Procurement (Contract-heavy) | UAE | CONTRACT_REVIEW_V1 | UAE, DIFC, ADGM | en |
| UAE Compliance | UAE | LEGAL_RESEARCH_V1 | UAE, DIFC, ADGM | en |
| KSA In-House (General Counsel) | KSA | LEGAL_RESEARCH_V1, CONTRACT_REVIEW_V1 | KSA | ar |
| KSA Procurement (Contract-heavy) | KSA | CONTRACT_REVIEW_V1 | KSA | ar |

### Template Configuration

Each template defines:

- **Region**: UAE or KSA (for grouping and display)
- **Recommended Jurisdiction**: Auto-set when template is selected
- **Recommended Data Residency**: Auto-set when template is selected

- **Policy Config**:
  - `allowed_workflows`: Which workflows can be executed
  - `allowed_jurisdictions`: Which jurisdictions are allowed
  - `allowed_input_languages`: Languages for input documents
  - `allowed_output_languages`: Languages for output/responses
  - `feature_flags`: Feature toggles (e.g., `law_firm_mode`)

- **Workspace Defaults**:
  - `default_language`: Default language for the workspace (ar for KSA, en/mixed for UAE)
  - `jurisdiction_profile`: Default jurisdiction profile (KSA_DEFAULT or UAE_DEFAULT)

### Data Residency Enforcement

Residency is locked to the template's recommended value by default. This follows a "soft-hard" enforcement model:

1. **Default Behavior**: Residency automatically matches the template recommendation
2. **Advanced Override**: Users can override, but:
   - The override requires explicit user action (changing the dropdown)
   - A persistent warning is shown when residency differs from recommendation
3. **Visibility**: The residency setting and any override is clearly visible during setup

### Arabic-First Mode

KSA templates are configured for Arabic-first operation:

1. **Default Output Language**: Set to Arabic (`ar`)
2. **Placeholder Text**: Research/review forms show bilingual placeholders
3. **Workspace Context**: The default language is stored and used across all workflows

Note: No RTL layout overhaul is required - this is purely a language default setting.

### Adding New Templates

To add a new template:

1. Open `src/lib/workspaceTemplates.ts`
2. Create a new `WorkspaceTemplate` constant
3. Add it to the `WORKSPACE_TEMPLATES` array

Example:

```typescript
export const MY_NEW_TEMPLATE: WorkspaceTemplate = {
  id: 'my_new_template',
  name: 'My New Template',
  description: 'Description of the template',
  region: 'UAE', // or 'KSA'
  recommendedJurisdiction: 'UAE',
  recommendedDataResidency: 'UAE',
  policyConfig: {
    allowed_workflows: ['LEGAL_RESEARCH_V1'],
    allowed_jurisdictions: ['UAE'],
    allowed_input_languages: ['en'],
    allowed_output_languages: ['en'],
    feature_flags: {},
  },
  workspaceDefaults: {
    default_language: 'en',
    jurisdiction_profile: 'UAE_DEFAULT',
  },
};

export const WORKSPACE_TEMPLATES: WorkspaceTemplate[] = [
  // ... existing templates
  MY_NEW_TEMPLATE,
];
```

## Workspace Context Switcher

The navigation bar includes a workspace context switcher that displays:

- **Current Workspace**: Name or truncated ID
- **Role**: Your role in the workspace (ADMIN, EDITOR, VIEWER)

Clicking the workspace button reveals a dropdown with:

- **Current Context Details**: Tenant ID, Workspace ID, Role, Language, Jurisdiction Profile
- **Switch Workspace**: Clears session and redirects to login
- **Create New Workspace**: Clears session and redirects to setup

This allows quick context verification and easy workspace switching for multi-tenant testing.

## Session Management

### Logout from All Devices

Users can revoke all sessions by calling the `/auth/logout-all` endpoint. This invalidates all existing JWT tokens and requires re-authentication.

The API client provides:

```typescript
// Logout from all devices (requires authentication)
await apiClient.logoutAll();
```

**Note**: This feature is available via direct API call. A UI button can be added to `/account` page if needed.

### Forced Logout (Session Expiry)

Sessions may be forcibly terminated in several scenarios:

| Scenario | Cause | User Experience |
|----------|-------|-----------------|
| Admin action | Administrator calls `/auth/logout-all` for your account | Redirected to login |
| Deployment | Token version changed after server update/migration | Redirected to login |
| Security response | Suspected credential compromise | Redirected to login |

When forced logout occurs:
1. The API returns a structured error with `error_code: "token_revoked"`
2. The web client clears all session data automatically
3. User is redirected to `/login?reason=session_expired`
4. A friendly info message is displayed: "Your session has expired. Please sign in again."

This is intentional behavior for security - not an error condition.

## API Client

The API client is located at `src/lib/apiClient.ts` and provides:

### Authentication Methods
- `devLogin()` - Login with credentials (sets cookies)
- `refreshAccessToken()` - Refresh tokens (called automatically on 401)
- `logout()` - Logout current session (clears cookies)
- `logoutAll()` - Logout from all devices (revokes all sessions)
- `getMe()` - Get current user info

### Bootstrap/Setup
- `bootstrapTenant()` - Create tenant with bootstrap

### Documents
- `listDocuments()` - List workspace documents
- `getDocument()` - Get document with versions
- `uploadDocument()` - Upload new document
- `uploadVersion()` - Upload new version
- `downloadVersion()` - Download document version
- `getDocumentVersionText()` - Get extracted text for a document version (Viewer+)
- `getDocumentVersionChunks()` - Get all chunks for a document version (Viewer+)

### Workflows
- `legalResearch()` - Execute legal research workflow
- `contractReview()` - Execute contract review workflow
- `clauseRedlines()` - Execute clause redlines workflow

### Exports
- `exportContractReviewDocx()` - Export contract review results to DOCX (Viewer+)
- `exportClauseRedlinesDocx()` - Export clause redlines results to DOCX (Viewer+)

### Admin
- `createPolicyProfile()` - Create a policy profile (Admin only)
- `attachWorkspacePolicyProfile()` - Attach policy profile to workspace (Admin only)
- `getAuditLogs()` - Fetch audit log entries (Admin only)
- `reindexVersion()` - Trigger reindexing of a document version (Admin only)
- `listMembers()` - List workspace members with user details (Viewer+)
- `addMember()` - Invite/add member by email (Admin only)
- `updateMemberRole()` - Update member role (Admin only)
- `removeMember()` - Remove member from workspace (Admin only)

All authenticated requests include `credentials: "include"` for automatic cookie transmission.

## Role-Based Access

| Role   | View Documents | Upload/Edit | View Members | Manage Members | Audit Logs |
| ------ | -------------- | ----------- | ------------ | -------------- | ---------- |
| VIEWER | Yes            | No          | Yes          | No             | No         |
| EDITOR | Yes            | Yes         | Yes          | No             | No         |
| ADMIN  | Yes            | Yes         | Yes          | Yes            | Yes        |

The UI automatically:
- Disables upload buttons for VIEWER role users
- Shows Members and Audit links only for ADMIN users
- Disables member management actions for non-ADMIN users

## Scripts

```powershell
pnpm dev          # Start development server
pnpm build        # Production build
pnpm start        # Start production server
pnpm lint         # Run ESLint
pnpm lint:fix     # Fix ESLint issues
pnpm format       # Format with Prettier
pnpm typecheck    # TypeScript type check
```

## Windows Build

### Symlink Issue

Next.js standalone builds on Windows fail with:

```
Error: EPERM: operation not permitted, symlink
```

This occurs because Windows restricts symlink creation unless Developer Mode is enabled or the user has elevated permissions. pnpm uses symlinks by default for its node_modules structure.

### Solution (Applied)

This project includes an `.npmrc` file that sets:

```
node-linker=hoisted
```

This tells pnpm to use a flat (hoisted) node_modules structure instead of symlinks, similar to npm/yarn. This works reliably on Windows without requiring system changes.

### If You Still Have Issues

1. **Delete node_modules and reinstall:**

   ```powershell
   Remove-Item -Recurse -Force node_modules
   Remove-Item -Force pnpm-lock.yaml
   pnpm install
   ```

2. **Alternative: Enable Windows Developer Mode** (optional, not required):
   - Settings > Privacy & Security > For Developers > Developer Mode: ON
   - This allows symlinks without elevation

3. **Clear Next.js cache:**

   ```powershell
   Remove-Item -Recurse -Force .next
   pnpm build
   ```

### Docker Builds

Docker builds are unaffected by this issue as they run on Linux. The `.npmrc` setting is harmless in Docker.

## Known Limitations

- Token stored in localStorage (dev-only approach) - visible DEV MODE banner warns users
- No token refresh mechanism
- No offline support
- Basic error handling (could be improved with error boundaries)
- No pagination UI (uses limit/offset in API)

## API Endpoint Gaps

The following features are not available in the current API and would enhance the UI:

- User profile update endpoint
- Password/credential management (for production SSO)
- Document search endpoint (currently internal to research workflow)
- Bulk document operations
- Update workspace defaults after creation (e.g., change default_language)
- Delete policy profile endpoint

## Troubleshooting

### API Connection Failed

1. Ensure the API is running: `docker compose ps`
2. Check API logs: `docker compose logs api`
3. Verify environment variables in `.env`

### 401 Unauthorized

1. **Session expired**: Token may have expired - log in again
2. **Forced logout**: An admin may have revoked all sessions - log in again
3. **No membership**: User may not have membership in the workspace
4. **Wrong credentials**: Check that tenant/workspace IDs are correct

**Note**: If you see "Your session has expired" message on login, this indicates a forced logout (admin action or deployment), not an error.

### Document Upload Failed

1. Check file size (may have limits)
2. Verify EDITOR or ADMIN role
3. Check API logs for policy violations

### Research Returns "Insufficient Sources"

1. Upload more documents to the workspace
2. Ensure documents are relevant to the question
3. Adjust jurisdiction/language filters
