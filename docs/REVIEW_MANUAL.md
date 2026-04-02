# Aiden.ai End-User Review Manual

**Version:** 1.0  
**Audience:** Legal users, reviewers, compliance teams  
**Last Updated:** January 2026

---

## Table of Contents

1. [What Aiden Is (and Is Not)](#what-aiden-is-and-is-not)
2. [Getting Started](#getting-started)
3. [Document Lifecycle](#document-lifecycle)
4. [Legal Research Workflow](#legal-research-workflow)
5. [Contract Review Workflow](#contract-review-workflow)
6. [Clause Redlines Workflow](#clause-redlines-workflow)
7. [Evidence & Document Viewer](#evidence--document-viewer)
8. [Exports](#exports)
9. [Known Limitations](#known-limitations)

---

## What Aiden Is (and Is Not)

### Evidence-First System

Aiden is an **evidence-first legal AI assistant** designed to help legal professionals review contracts, conduct research, and analyze clauses. Every answer, finding, or recommendation produced by Aiden is tied directly to evidence from your uploaded documents.

**Key Principles:**

- **Grounded in Your Documents**: Aiden only analyzes documents you upload. It does not access external databases, the internet, or any data outside your workspace.
- **Traceable Citations**: Every claim in a response includes numbered citations (e.g., `[1]`, `[2]`) that reference specific locations in your documents.
- **Evidence Thresholds**: The system requires a minimum number of evidence chunks before generating answers. If insufficient evidence exists, Aiden will tell you rather than guess.

### No Hallucinated Legal Advice

Aiden does **not** provide legal advice. It is a document analysis tool that:

- ✅ Summarizes what your documents contain
- ✅ Identifies clauses and provisions
- ✅ Highlights potential risks based on document content
- ✅ Compares clauses against jurisdiction-specific templates
- ❌ Does **not** provide opinions on legal strategy
- ❌ Does **not** guarantee legal accuracy
- ❌ Does **not** replace professional legal judgment

### Deterministic Safety Rails

Aiden includes multiple safety mechanisms:

| Safety Feature | Description |
|----------------|-------------|
| **Minimum Evidence Threshold** | Requires at least 3 evidence chunks before generating any response |
| **Strict Citation Enforcement** | Paragraphs without valid citations are automatically removed |
| **Answer Length Validation** | Responses shorter than 50 characters after citation processing are rejected |
| **Policy-Based Restrictions** | Workflows, jurisdictions, and languages are controlled by administrator policies |
| **Audit Logging** | All actions are logged for compliance and security |

---

## Getting Started

### Login (Cookie-Based Authentication)

Aiden uses secure, cookie-based authentication:

1. Navigate to the login page
2. Enter your credentials (tenant ID, workspace ID, email)
3. Upon successful login, secure cookies are set automatically
4. Your session persists across page refreshes and browser restarts

**Session Behavior:**

- Access tokens expire after 15 minutes and are automatically refreshed
- Refresh tokens expire after 7 days
- Logging out clears all session data
- The "Logout All" feature invalidates sessions across all devices

### Workspace Context

All work in Aiden occurs within a **workspace**. A workspace is:

- A shared container for documents, research, and reviews
- Isolated from other workspaces (your documents are private)
- Associated with specific permissions and policies

Your current workspace is displayed in the navigation bar. You can switch workspaces if you have access to multiple workspaces.

### Roles: Viewer / Editor / Admin

Your role determines what you can do in a workspace:

| Role | Permissions |
|------|-------------|
| **VIEWER** | View documents, research results, and exports. Read-only access to audit logs. |
| **EDITOR** | All Viewer permissions, plus: upload documents, run workflows (research, contract review, clause redlines), create document versions. |
| **ADMIN** | All Editor permissions, plus: manage workspace members, attach policy profiles, access full audit logs, trigger re-indexing. |

Your role is displayed as a badge in the workspace selector.

---

## Document Lifecycle

### Upload

To upload a document:

1. Navigate to **Documents**
2. Click **Upload Document**
3. Complete the form:
   - **File**: Select a PDF, DOC, DOCX, or TXT file
   - **Title**: Enter a descriptive title
   - **Document Type**: Select from `contract`, `policy`, `memo`, `regulatory`, or `other`
   - **Jurisdiction**: Select the applicable jurisdiction (UAE, DIFC, ADGM, or KSA)
   - **Language**: Select `English`, `Arabic`, or `Mixed`
   - **Confidentiality**: Set the confidentiality level
4. Click **Upload**

**Upload Validation:**

Documents are validated against your workspace policy. If your policy restricts certain jurisdictions or languages, uploads with unsupported values will be rejected.

### Indexing

After upload, Aiden automatically:

1. **Extracts text** from the document
2. **Splits the text into chunks** (approximately 800-1200 characters each)
3. **Generates embeddings** for semantic search

This process typically completes within seconds for most documents.

### Re-indexing (When and Why)

Re-indexing regenerates the search embeddings for a document. This may be needed when:

- The embedding model has been upgraded
- Initial indexing failed or was incomplete
- Search results appear inconsistent

Only **ADMIN** users can trigger re-indexing via the document detail page.

### Indexing Status Meanings

The indexing status indicates whether a document is searchable:

| Status | Meaning |
|--------|---------|
| **Indexed** ✓ | Document is fully indexed and searchable |
| **Not Indexed** | Document has not been indexed or indexing failed |
| **Indexing...** | Indexing is in progress |

If a document remains "Not Indexed" after upload, contact your administrator.

---

## Legal Research Workflow

The Legal Research workflow answers questions based on your uploaded documents.

### How to Use

1. Navigate to **Research**
2. Enter your question in natural language
3. (Optional) Set filters:
   - **Jurisdiction**: Limit search to specific jurisdiction
   - **Document Type**: Limit to specific document types
   - **Language**: Limit to documents in a specific language
4. Set the **Evidence Limit** (how many chunks to retrieve, default: 10)
5. Select **Output Language** (English or Arabic)
6. Click **Submit**

### Evidence Threshold Logic

Aiden requires a **minimum of 3 evidence chunks** to generate a response. This ensures:

- Answers are based on sufficient source material
- Low-confidence guesses are avoided
- Users understand when their document collection lacks relevant content

If fewer than 3 relevant chunks are found, the response will indicate "Insufficient sources in your workspace to answer confidently."

### Citation Requirements

Every paragraph in a research answer must contain at least one citation:

- Citations appear as numbered references: `[1]`, `[2]`, `[3]`
- Multiple citations may appear in one bracket: `[1,2]`
- Citations link directly to evidence chunks in your documents

**Important:** Paragraphs without citations are automatically removed. This ensures every statement can be traced to source evidence.

### Result Statuses

| Status | Meaning |
|--------|---------|
| **success** | Research completed successfully with valid citations |
| **insufficient_sources** | Fewer than 3 relevant evidence chunks found |
| **citation_violation** | Response failed citation requirements (rare) |
| **generation_failed** | LLM generation encountered an error |
| **policy_denied** | Request blocked by workspace policy |

---

## Contract Review Workflow

The Contract Review workflow analyzes contracts for risks and issues.

### Review Modes

Select a review mode based on your needs:

| Mode | Evidence Chunks | Best For |
|------|-----------------|----------|
| **Quick** | Up to 20 | Fast preliminary review, simple contracts |
| **Standard** | Up to 40 | Balanced review for most contracts (default) |
| **Deep** | Up to 80 | Comprehensive review, complex contracts |

Higher chunk limits provide more thorough analysis but take slightly longer.

### How to Use

1. Navigate to the document you want to review
2. Click **Review** or go to **Contract Review**
3. Select the document and version
4. (Optional) Select a playbook for jurisdiction-specific guidance
5. Choose your review mode (Quick/Standard/Deep)
6. (Optional) Select focus areas (Liability, Termination, etc.)
7. Select output language
8. Click **Submit**

### Findings Structure

Each finding includes:

| Field | Description |
|-------|-------------|
| **Title** | Brief description of the finding |
| **Severity** | Risk level: `low`, `medium`, `high`, or `critical` |
| **Category** | Type: `liability`, `termination`, `governing_law`, `payment`, `ip`, `confidentiality`, or `other` |
| **Issue** | Description of the problem with citations |
| **Recommendation** | Suggested action with citations |
| **Evidence** | Source chunks with "View in Document" links |

### Severity vs Confidence

Contract Review uses **severity** to indicate risk level:

| Severity | Meaning |
|----------|---------|
| **Critical** | Immediate attention required; significant legal/business risk |
| **High** | Important issue that should be addressed |
| **Medium** | Moderate concern; review recommended |
| **Low** | Minor issue or standard clause variation |

**Note:** Contract Review does not display confidence levels. Severity reflects the risk impact, not certainty.

### Why Summaries May Be Regenerated

If the executive summary lacks proper citations but the findings contain valid citations, Aiden automatically regenerates the summary to include citations. You may see a note indicating "Summary regenerated from findings due to missing citations."

This ensures the summary is traceable to source evidence.

---

## Clause Redlines Workflow

The Clause Redlines workflow compares contract clauses against jurisdiction-specific templates and suggests improvements.

### Clause Detection (v2)

Aiden uses deterministic clause detection (version 2) to identify clause types:

- **Governing Law** - Jurisdiction and choice of law provisions
- **Termination** - Contract termination rights and procedures
- **Liability** - Liability caps, exclusions, and limitations
- **Indemnity** - Indemnification obligations
- **Confidentiality** - Non-disclosure and confidentiality terms
- **Payment** - Payment terms and conditions
- **IP** - Intellectual property rights
- **Force Majeure** - Force majeure provisions

Detection uses keyword matching and heading recognition—no LLM is involved in clause identification.

### Confidence Levels

Each detected clause has a confidence level:

| Level | Threshold | Meaning |
|-------|-----------|---------|
| **High** | ≥70% | Strong match; clause clearly identified |
| **Medium** | ≥40% | Moderate match; likely correct |
| **Low** | <40% | Weak match; may be incomplete or ambiguous |

The confidence reason explains why the level was assigned (e.g., "Matched heading", "3 trigger(s)").

### Missing vs Insufficient Evidence

Clause status indicates what was found:

| Status | Meaning |
|--------|---------|
| **Found** | Clause detected with high/medium confidence |
| **Insufficient Evidence** | Clause may exist but evidence is weak or citations are missing |
| **Missing** | No evidence of this clause type in the document |

### Recommended Text vs Claims

In redline suggestions:

- **Contract Claims**: Statements about what the contract says. These **must** include citations (e.g., "The contract states... `[1]`")
- **Recommended Text**: Template language from the clause library. This does **not** require citations because it's suggested replacement text, not a claim about the document.

If a contract claim lacks citations, the clause status may be downgraded to "Insufficient Evidence."

---

## Evidence & Document Viewer

### "View in Document"

Throughout research results, contract reviews, and clause redlines, you'll see **"View in Document"** links next to evidence snippets. Clicking this link:

1. Opens the document viewer
2. Navigates directly to the relevant chunk
3. Highlights the evidence location

### Chunk Navigation

The document viewer displays documents as chunks (text segments):

**Sidebar (left):**
- Searchable list of all chunks
- Chunk previews with index numbers
- Click any chunk to navigate

**Main Panel (right):**
- Full text of selected chunk
- Previous/Next navigation buttons
- Context from surrounding chunks
- Metadata: character range, page numbers

**URL Parameters:**
- `?chunkId=xxx` - Navigate to specific chunk by ID
- `?chunkIndex=N` - Navigate to chunk by index number

### Context Windows

When viewing a chunk, you may see:

- **Previous Chunk Context**: Text from the preceding chunk (gray background)
- **Current Chunk**: The selected chunk (white background)
- **Next Chunk Context**: Text from the following chunk (gray background)

This helps you understand the evidence in its original context.

---

## Exports

### DOCX Guarantees

Aiden can export Contract Review and Clause Redlines results to Microsoft Word (DOCX) format.

**What's Included:**

- Cover page with document metadata
- Executive summary with disclaimer
- All findings/clauses with severity and citations
- Evidence appendix with full text snippets
- Traceability footer with audit information

**What's Guaranteed:**

- Export only succeeds if evidence validation passes
- All citations in the export map to real evidence chunks
- Export filename is sanitized (special characters replaced)
- Export includes the LLM model and prompt hash for traceability

### Traceability Footer

Every exported document includes a traceability footer containing:

| Field | Description |
|-------|-------------|
| **Workflow** | Type of analysis (e.g., CONTRACT_REVIEW_V1) |
| **Status** | Result status (success, insufficient_sources) |
| **LLM Provider** | AI provider used (or "N/A" for stub) |
| **LLM Model** | Specific model name |
| **Prompt Hash** | Unique identifier for the prompt (truncated) |
| **Generated By** | Aiden.ai |
| **Environment** | System environment identifier |

**Legal Disclaimer:**

```
This document was generated by an AI system. It does not constitute 
legal advice and should be reviewed by qualified legal professionals. 
The accuracy of the analysis depends on the quality and completeness 
of the source documents. No warranties are provided.
```

### Evidence Validation Before Export

Before generating an export, Aiden validates:

1. All referenced chunk IDs exist in the database
2. Chunks belong to the specified document and version
3. Chunks are owned by your workspace and tenant

If any validation fails, the export is rejected with a clear error message.

---

## Known Limitations

### OCR Not Supported

Aiden does not perform Optical Character Recognition (OCR):

- **Scanned PDFs** with only images will not be searchable
- **Image-based documents** (JPG, PNG) cannot be processed
- Only documents with extractable text are supported

**Recommendation:** Before uploading, verify your PDF contains selectable text (try Ctrl+F in a PDF reader).

### Language Constraints

| Language | Support Level |
|----------|---------------|
| **English** | Full support |
| **Arabic** | Full support |
| **Mixed** | Supported (documents containing both) |
| **Other Languages** | Not currently supported |

Documents in unsupported languages may produce poor results or be rejected by policy.

### Stub LLM vs Production LLM Behavior

In development and testing environments, Aiden may use a **stub LLM provider** instead of production AI:

| Aspect | Stub Provider | Production Provider |
|--------|--------------|---------------------|
| **Responses** | Deterministic, template-based | AI-generated |
| **Quality** | Limited, for testing only | Full analysis quality |
| **Indicator** | Banner or status indicator | No special indicator |
| **Prompt Hash** | 8-character test ID | Full SHA256 hash |

**How to Identify Stub Mode:**

- Look for a "Development Mode" or "Stub Provider" banner
- Check the meta information in responses—stub responses show model name `stub-v1`
- Responses may contain test markers like `[Analysis ID: xxxxxxxx]`

**Important:** Do not rely on stub mode responses for actual legal work. Stub mode is for system testing only.

### Additional Limitations

| Limitation | Details |
|------------|---------|
| **File Size** | Large documents may take longer to process |
| **Chunk Size** | Evidence is split into ~1000-character chunks; very long paragraphs may be split |
| **Evidence Limit** | Maximum 50 evidence chunks per query |
| **Export Format** | Only DOCX format supported |
| **Concurrent Users** | Rate limits may apply during high usage |

---

## Getting Help

If you encounter issues not covered in this manual:

1. **Check the status indicators** - Many issues are explained by the result status
2. **Review evidence counts** - Insufficient sources messages indicate document gaps
3. **Contact your administrator** - For policy, access, or configuration issues
4. **Check audit logs** - Administrators can review detailed action logs

---

*This manual documents the Aiden.ai system as implemented. For technical operations and troubleshooting, see the [Operations Runbook](OPS_RUNBOOK.md).*
