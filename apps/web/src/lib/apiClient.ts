/**
 * HeyAmin API Client
 *
 * Single source of truth for all API calls.
 * Handles URL resolution, authentication via httpOnly cookies, and typed responses.
 *
 * Authentication:
 * - Uses httpOnly cookies set by the backend (access_token, refresh_token)
 * - All requests include credentials: "include" for cookie transmission
 * - On 401, attempts silent refresh before redirecting to login
 * - No tokens are stored in localStorage (XSS protection)
 */

import { getApiBaseUrl, isServer } from './api';

/** Browser fetch can hang indefinitely if the API is down or misconfigured — abort so auth can finish. */
const CLIENT_FETCH_TIMEOUT_MS = 25_000;

async function fetchWithClientTimeout(
  url: string,
  init: RequestInit
): Promise<Response> {
  if (isServer()) {
    return fetch(url, init);
  }
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    CLIENT_FETCH_TIMEOUT_MS
  );
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

// ============================================================================
// Types
// ============================================================================

// Bootstrap types
export interface BootstrapAdminUser {
  email: string;
  password: string;
  full_name?: string;
}

export interface BootstrapWorkspace {
  name: string;
  workspace_type?: 'IN_HOUSE' | 'LAW_FIRM';
  jurisdiction_profile?:
    | 'UAE_DEFAULT'
    | 'DIFC_DEFAULT'
    | 'ADGM_DEFAULT'
    | 'KSA_DEFAULT';
  default_language?: 'en' | 'ar' | 'mixed';
}

export interface BootstrapPayload {
  admin_user: BootstrapAdminUser;
  workspace: BootstrapWorkspace;
}

export interface TenantCreateWithBootstrap {
  name: string;
  primary_jurisdiction: 'UAE' | 'KSA' | 'DIFC' | 'ADGM';
  data_residency_policy: 'UAE' | 'KSA' | 'GCC';
  bootstrap?: BootstrapPayload;
}

export interface BootstrapResponse {
  tenant_id: string;
  tenant_name: string;
  workspace_id: string | null;
  workspace_name: string | null;
  admin_user_id: string | null;
  admin_user_email: string | null;
  created_at: string;
}

// Auth types
export interface DevLoginRequest {
  tenant_id: string;
  workspace_id: string;
  email: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/** Operator API user row (subset of backend UserResponse). */
export interface OperatorUserRow {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_platform_admin?: boolean;
  created_at: string;
}

// Legacy TokenResponse (for backwards compatibility)
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// New cookie-based auth response
export interface CookieAuthResponse {
  user_id: string;
  email: string | null;
  role: string;
  expires_in: number;
  auth_mode: 'cookie';
}

export interface RefreshResponse {
  expires_in: number;
  auth_mode: 'cookie';
}

export interface CurrentUserResponse {
  user_id: string;
  tenant_id: string;
  workspace_id: string;
  role: string;
  email: string | null;
  full_name: string | null;
  is_platform_admin: boolean;
  auth_mode?: 'cookie' | 'bearer';
}

/**
 * Workspace context including language defaults
 * Used for setting default output language in workflows
 */
export interface WorkspaceContext {
  id: string;
  name: string;
  default_language: 'en' | 'ar' | 'mixed';
  jurisdiction_profile: string;
}

// Document types
export interface DocumentVersionSummary {
  id: string;
  version_number: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_user_id: string;
  created_at: string;
}

export interface DocumentWithLatestVersion {
  id: string;
  tenant_id: string;
  workspace_id: string;
  title: string;
  document_type: string;
  jurisdiction: string;
  language: string;
  confidentiality: string;
  created_by_user_id: string;
  created_at: string;
  latest_version: DocumentVersionSummary | null;
}

export interface DocumentWithVersions {
  id: string;
  tenant_id: string;
  workspace_id: string;
  title: string;
  document_type: string;
  jurisdiction: string;
  language: string;
  confidentiality: string;
  created_by_user_id: string;
  created_at: string;
  versions: DocumentVersionSummary[];
}

export interface DocumentListResponse {
  items: DocumentWithLatestVersion[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentResponse {
  id: string;
  tenant_id: string;
  workspace_id: string;
  title: string;
  document_type: string;
  jurisdiction: string;
  language: string;
  confidentiality: string;
  created_by_user_id: string;
  created_at: string;
}

export interface DocumentVersionResponse {
  id: string;
  tenant_id: string;
  workspace_id: string;
  document_id: string;
  version_number: number;
  file_name: string;
  content_type: string;
  size_bytes: number;
  storage_provider: string;
  sha256: string;
  uploaded_by_user_id: string;
  created_at: string;
}

export interface DocumentCreateResponse {
  document: DocumentResponse;
  version: DocumentVersionResponse;
}

export interface DocumentVersionCreateResponse {
  version: DocumentVersionResponse;
  document_id: string;
}

// Research types
export interface ResearchFilters {
  document_type?: string;
  jurisdiction?: string;
  language?: string;
}

// Evidence scope options
export type EvidenceScope = 'workspace' | 'global' | 'both';

export interface LegalResearchRequest {
  question: string;
  limit?: number;
  filters?: ResearchFilters;
  output_language?: 'en' | 'ar';
  /** Evidence retrieval scope: workspace (default), global, or both */
  evidence_scope?: EvidenceScope;
}

export interface CitationReference {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  version_id: string;
  document_title: string;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
}

export interface EvidenceChunk {
  chunk_id: string;
  chunk_index: number;
  snippet: string;
  // Source provenance (required for user trust)
  source_type: SourceType;
  source_label: string;
  // Document metadata (workspace documents)
  document_id?: string;
  version_id?: string;
  document_title?: string;
  document_type?: string;
  // Instrument metadata (global legal)
  instrument_id?: string;
  instrument_title?: string;
  instrument_title_ar?: string | null;
  instrument_type?: string;
  // Common metadata
  jurisdiction?: string;
  language?: string;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
  final_score: number;
  // Legal provenance (global legal)
  published_at?: string | null;
  effective_at?: string | null;
  official_source_url?: string | null;
}

// Workflow result status enum (matches backend WorkflowResultStatus)
export type WorkflowResultStatus =
  | 'success'
  | 'insufficient_sources'
  | 'policy_denied'
  | 'citation_violation'
  | 'validation_failed'
  | 'generation_failed';

export interface ResearchMeta {
  status: WorkflowResultStatus;
  model: string;
  provider: string;
  chunk_count: number;
  request_id: string | null;
  output_language: string;
  validation_warnings: string[] | null;
  strict_citation_enforced: boolean;
  removed_paragraph_count: number;
  strict_citations_failed: boolean;
  citation_count_used: number;
  // Prompt/model fingerprinting
  prompt_hash: string | null;
  llm_provider: string | null;
  llm_model: string | null;
  // Evidence scope and counts
  evidence_scope: EvidenceScope;
  workspace_evidence_count: number;
  global_evidence_count: number;
  // Policy metadata
  policy_jurisdictions_count: number;
  policy_languages_count: number;
  policy_denied_reason: string | null;
}

export interface LegalResearchResponse {
  answer_text: string;
  citations: CitationReference[];
  evidence: EvidenceChunk[];
  meta: ResearchMeta;
  insufficient_sources: boolean;
}

// Contract Review types
export type ContractReviewMode = 'quick' | 'standard' | 'deep';
export type ContractFocusArea =
  | 'liability'
  | 'termination'
  | 'governing_law'
  | 'payment'
  | 'ip'
  | 'confidentiality';

// Clause Redlines types
export type ClauseType =
  | 'governing_law'
  | 'termination'
  | 'liability'
  | 'indemnity'
  | 'confidentiality'
  | 'payment'
  | 'ip'
  | 'force_majeure';

export type ClauseJurisdiction = 'UAE' | 'DIFC' | 'ADGM' | 'KSA';
export type ClauseStatus = 'found' | 'missing' | 'insufficient_evidence';
export type ClauseSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface EvidenceChunkRef {
  chunk_id: string;
  snippet: string;
  char_start: number;
  char_end: number;
  // Source provenance
  source_type: SourceType;
  source_label: string;
  // Global legal metadata (optional)
  instrument_id?: string;
  jurisdiction?: string;
  official_source_url?: string | null;
}

export interface ClauseRedlineItem {
  clause_type: ClauseType;
  status: ClauseStatus;
  confidence: number;
  issue: string | null;
  suggested_redline: string | null;
  rationale: string | null;
  citations: number[];
  evidence: EvidenceChunkRef[];
  severity: ClauseSeverity;
}

export interface ClauseRedlinesMeta {
  status: WorkflowResultStatus;
  model: string;
  provider: string;
  evidence_chunk_count: number;
  request_id: string | null;
  output_language: string;
  jurisdiction: string;
  downgraded_count: number;
  removed_count: number;
  strict_citations_failed: boolean;
  validation_warnings: string[] | null;
  // Prompt/model fingerprinting
  prompt_hash: string | null;
  llm_provider: string | null;
  llm_model: string | null;
  // Evidence scope and counts
  evidence_scope: EvidenceScope;
  workspace_evidence_count: number;
  global_evidence_count: number;
  // Policy metadata
  policy_jurisdictions_count: number;
  policy_languages_count: number;
  policy_denied_reason: string | null;
}

export interface ClauseRedlinesRequest {
  document_id: string;
  version_id: string;
  jurisdiction?: ClauseJurisdiction;
  playbook_hint?: string;
  clause_types?: ClauseType[];
  output_language: 'en' | 'ar';
  /** Evidence retrieval scope: workspace (default), global, or both */
  evidence_scope?: EvidenceScope;
}

export interface ClauseRedlinesResponse {
  summary: string;
  items: ClauseRedlineItem[];
  meta: ClauseRedlinesMeta;
  insufficient_sources: boolean;
}

export interface ContractReviewRequest {
  document_id: string;
  version_id: string;
  review_mode: ContractReviewMode;
  focus_areas: ContractFocusArea[];
  output_language: 'en' | 'ar';
  /** Optional hint from a playbook to guide the review focus */
  playbook_hint?: string;
  /** Evidence retrieval scope: workspace (default), global, or both */
  evidence_scope?: EvidenceScope;
}

export interface FindingCitation {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  version_id: string;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
}

export interface FindingEvidence {
  chunk_id: string;
  snippet: string;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
}

export interface ContractFinding {
  finding_id: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: string;
  title: string;
  issue: string;
  recommendation: string;
  citations: FindingCitation[];
  evidence: FindingEvidence[];
}

export interface ContractReviewMeta {
  status: WorkflowResultStatus;
  model: string;
  provider: string;
  review_mode: ContractReviewMode;
  focus_areas: ContractFocusArea[];
  output_language: string;
  request_id: string | null;
  removed_findings_count: number;
  strict_citations_failed: boolean;
  // Prompt/model fingerprinting
  prompt_hash: string | null;
  llm_provider: string | null;
  llm_model: string | null;
  // Evidence scope and counts
  evidence_scope: EvidenceScope;
  workspace_evidence_count: number;
  global_evidence_count: number;
  // Policy metadata
  policy_jurisdictions_count: number;
  policy_languages_count: number;
  policy_denied_reason: string | null;
}

export interface ContractReviewResponse {
  document_id: string;
  version_id: string;
  summary: string;
  findings: ContractFinding[];
  meta: ContractReviewMeta;
}

// Policy Profile types
export interface PolicyConfig {
  allowed_workflows: string[];
  allowed_input_languages: string[];
  allowed_output_languages: string[];
  allowed_jurisdictions: string[];
  feature_flags: Record<string, boolean>;
}

export interface PolicyProfileCreateRequest {
  name: string;
  description?: string;
  config: PolicyConfig;
  is_default: boolean;
}

export interface PolicyProfileResponse {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  config: Record<string, unknown>;
  is_default: boolean;
  created_at: string;
}

export interface AttachPolicyRequest {
  policy_profile_id: string;
}

export interface WorkspaceResponse {
  id: string;
  tenant_id: string;
  name: string;
  workspace_type: string;
  jurisdiction_profile: string;
  default_language: string;
  policy_profile_id: string | null;
  created_at: string;
}

// API Error type
export interface ApiError {
  detail: string | ApiErrorDetail;
}

// Structured error detail (for token_revoked, etc.)
export interface ApiErrorDetail {
  error_code: string;
  message: string;
}

// Audit types
export interface AuditLogEntry {
  id: string;
  timestamp: string;
  tenant_id: string;
  workspace_id: string | null;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  status: 'success' | 'failure' | 'pending';
  request_id: string | null;
  details: Record<string, unknown> | null;
}

export interface AuditLogResponse {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

// Extended version summary with indexing status
export interface DocumentVersionSummaryWithIndexing extends DocumentVersionSummary {
  is_indexed?: boolean;
  indexed_at?: string | null;
  embedding_model?: string | null;
}

export interface DocumentWithLatestVersionAndIndexing {
  id: string;
  tenant_id: string;
  workspace_id: string;
  title: string;
  document_type: string;
  jurisdiction: string;
  language: string;
  confidentiality: string;
  created_by_user_id: string;
  created_at: string;
  latest_version: DocumentVersionSummaryWithIndexing | null;
}

export interface DocumentWithVersionsAndIndexing {
  id: string;
  tenant_id: string;
  workspace_id: string;
  title: string;
  document_type: string;
  jurisdiction: string;
  language: string;
  confidentiality: string;
  created_by_user_id: string;
  created_at: string;
  versions: DocumentVersionSummaryWithIndexing[];
}

export interface DocumentListResponseWithIndexing {
  items: DocumentWithLatestVersionAndIndexing[];
  total: number;
  limit: number;
  offset: number;
}

// Reindex response
export interface ReindexResponse {
  success: boolean;
  document_id: string;
  version_id: string;
  message: string;
}

// Document Text response
export interface DocumentTextResponse {
  id: string;
  version_id: string;
  extraction_method: string;
  page_count: number | null;
  text_length: number;
  created_at: string;
  extracted_text: string | null;
}

// Document Chunk response
export interface DocumentChunkResponse {
  id: string;
  chunk_index: number;
  text: string;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
}

// Document Chunks response
export interface DocumentChunksResponse {
  version_id: string;
  document_id: string;
  chunk_count: number;
  chunks: DocumentChunkResponse[];
}

// Export Document Metadata (for DOCX export)
export interface ExportDocumentMetadata {
  document_id: string;
  version_id: string;
  document_title: string;
  version_number: number;
  workspace_name: string;
  tenant_name: string;
  jurisdiction: string;
}

// Member Management types
export interface MemberWithUser {
  id: string;
  tenant_id: string;
  workspace_id: string;
  user_id: string;
  role: 'ADMIN' | 'EDITOR' | 'VIEWER';
  created_at: string;
  email: string | null;
  full_name: string | null;
  is_active: boolean;
}

export interface MemberInviteRequest {
  email: string;
  full_name?: string;
  /** Required when the invite creates a new user */
  initial_password?: string;
  role: 'ADMIN' | 'EDITOR' | 'VIEWER';
}

export interface MemberRoleUpdateRequest {
  role: 'ADMIN' | 'EDITOR' | 'VIEWER';
}

// ============================================================================
// Operator — Knowledge base scraping (platform admin)
// ============================================================================

export interface ScrapingSourceResponse {
  id: string;
  connector_name: string;
  display_name: string;
  jurisdiction: string;
  source_url: string | null;
  enabled: boolean;
  schedule_cron: string | null;
  harvest_limit: number;
  last_run_at: string | null;
  last_job_id: string | null;
  created_at: string;
  updated_at: string;
}

export type ScrapingJobStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ScrapingJobResponse {
  id: string;
  source_id: string;
  connector_name: string;
  status: ScrapingJobStatus;
  triggered_by: 'scheduler' | 'manual';
  started_at: string | null;
  finished_at: string | null;
  items_listed: number;
  items_upserted: number;
  items_failed: number;
  error_detail: string | null;
  created_at: string;
}

/** Run log entry shape from GET /operator/scraping/jobs/{id} */
export interface ScrapingJobRunLogEntry {
  source_url?: string;
  url?: string;
  result?: string;
}

export type ScrapingJobDetailResponse = ScrapingJobResponse & {
  run_log?: ScrapingJobRunLogEntry[] | null;
};

export interface ScrapingSourceCreate {
  connector_name: string;
  display_name: string;
  jurisdiction: string;
  source_url?: string;
  enabled: boolean;
  schedule_cron?: string | null;
  harvest_limit: number;
}

export interface ScrapingSourceUpdate {
  display_name?: string;
  enabled?: boolean;
  schedule_cron?: string | null;
  harvest_limit?: number;
}

export interface ScrapingTriggerResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ScrapingStatsResponse {
  total_instruments: number;
  instruments_by_jurisdiction: Record<string, number>;
  active_sources: number;
  total_sources: number;
  running_jobs: number;
  items_harvested_24h: number;
  items_harvested_7d: number;
  last_harvest_at: string | null;
}

// ============================================================================
// Session Storage (workspace context only - NO tokens in localStorage)
// ============================================================================

const TENANT_KEY = 'aiden_tenant_id';
const WORKSPACE_KEY = 'aiden_workspace_id';
const WORKSPACE_CONTEXT_KEY = 'aiden_workspace_context';

// Legacy token storage functions - kept for migration but deprecated
// DO NOT use these for new code

/** @deprecated Tokens are now stored in httpOnly cookies */
export function getStoredToken(): string | null {
  // Always return null - tokens are in cookies now
  return null;
}

/** @deprecated Tokens are now stored in httpOnly cookies */
export function setStoredToken(_token: string): void {
  // No-op - tokens are in cookies now
}

/** @deprecated Tokens are now stored in httpOnly cookies */
export function clearStoredToken(): void {
  // Clean up any legacy tokens
  if (!isServer()) {
    localStorage.removeItem('aiden_jwt_token');
  }
}

export function getStoredTenantId(): string | null {
  if (isServer()) return null;
  return localStorage.getItem(TENANT_KEY);
}

export function setStoredTenantId(tenantId: string): void {
  if (isServer()) return;
  localStorage.setItem(TENANT_KEY, tenantId);
}

export function getStoredWorkspaceId(): string | null {
  if (isServer()) return null;
  return localStorage.getItem(WORKSPACE_KEY);
}

export function setStoredWorkspaceId(workspaceId: string): void {
  if (isServer()) return;
  localStorage.setItem(WORKSPACE_KEY, workspaceId);
}

export function clearSession(): void {
  if (isServer()) return;
  // Clear legacy token if exists
  localStorage.removeItem('aiden_jwt_token');
  localStorage.removeItem(TENANT_KEY);
  localStorage.removeItem(WORKSPACE_KEY);
  localStorage.removeItem(WORKSPACE_CONTEXT_KEY);
}

/**
 * Get stored workspace context (includes language defaults)
 */
export function getStoredWorkspaceContext(): WorkspaceContext | null {
  if (isServer()) return null;
  const stored = localStorage.getItem(WORKSPACE_CONTEXT_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as WorkspaceContext;
  } catch {
    return null;
  }
}

/**
 * Store workspace context (set during setup)
 */
export function setStoredWorkspaceContext(context: WorkspaceContext): void {
  if (isServer()) return;
  localStorage.setItem(WORKSPACE_CONTEXT_KEY, JSON.stringify(context));
}

/**
 * Get the default output language based on workspace context
 * Falls back to 'en' if no context is available
 */
export function getDefaultOutputLanguage(): 'en' | 'ar' {
  const context = getStoredWorkspaceContext();
  if (!context) return 'en';
  // For 'mixed' default, prefer Arabic for Arabic-first regions
  if (context.default_language === 'ar') return 'ar';
  if (context.default_language === 'mixed') {
    // If jurisdiction is KSA, default to Arabic
    if (context.jurisdiction_profile === 'KSA_DEFAULT') return 'ar';
  }
  return 'en';
}

// ============================================================================
// API Client
// ============================================================================

// Track if we're currently refreshing to prevent multiple concurrent refreshes
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

class ApiClient {
  private getHeaders(): HeadersInit {
    // No Authorization header needed - cookies are sent automatically
    return {
      Accept: 'application/json',
    };
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      // Try to parse error detail first
      let errorDetail: string = `HTTP ${response.status}: ${response.statusText}`;
      let errorCode: string | null = null;

      try {
        const error: ApiError = await response.json();
        if (typeof error.detail === 'object' && error.detail !== null) {
          // Structured error (e.g., token_revoked)
          errorCode = error.detail.error_code;
          errorDetail = error.detail.message;
        } else if (typeof error.detail === 'string') {
          errorDetail = error.detail;
        }
      } catch {
        // Could not parse JSON, use default error message
      }

      // Don't handle 401 here - let the caller handle it for retry logic
      throw new ApiClientError(errorDetail, response.status, errorCode);
    }

    return response.json();
  }

  /**
   * Attempt to refresh the access token using the refresh token cookie.
   * Returns true if refresh succeeded, false otherwise.
   */
  async refreshAccessToken(): Promise<boolean> {
    // Prevent multiple concurrent refresh attempts
    if (isRefreshing && refreshPromise) {
      return refreshPromise;
    }

    isRefreshing = true;
    refreshPromise = (async () => {
      try {
        const baseUrl = getApiBaseUrl();
        const response = await fetchWithClientTimeout(
          `${baseUrl}/auth/refresh`,
          {
            method: 'POST',
            headers: this.getHeaders(),
            credentials: 'include',
          }
        );

        if (response.ok) {
          return true;
        }
        return false;
      } catch {
        return false;
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  }

  /**
   * Execute a request with automatic 401 retry via token refresh.
   */
  private async fetchWithRetry<T>(
    url: string,
    options: RequestInit
  ): Promise<T> {
    // Always include credentials for cookie transmission
    const optionsWithCredentials: RequestInit = {
      ...options,
      credentials: 'include',
    };

    const response = await fetchWithClientTimeout(url, optionsWithCredentials);

    if (response.status === 401 && !isServer()) {
      // Try to refresh and retry once
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        // Retry the original request
        const retryResponse = await fetchWithClientTimeout(
          url,
          optionsWithCredentials
        );
        return this.handleResponse<T>(retryResponse);
      }

      // Refresh failed - redirect to login (but not on public marketing/auth pages)
      const currentPath = window.location.pathname;
      const isPublicPage =
        currentPath === '/login' ||
        currentPath === '/setup' ||
        currentPath === '/' ||
        currentPath.startsWith('/#');

      if (!isPublicPage) {
        let errorCode: string | null = null;
        try {
          const error: ApiError = await response.clone().json();
          if (typeof error.detail === 'object' && error.detail !== null) {
            errorCode = error.detail.error_code;
          }
        } catch {
          // Ignore parse errors
        }

        clearSession();
        if (
          errorCode === 'token_revoked' ||
          errorCode === 'refresh_reuse_detected'
        ) {
          window.location.href = '/login?reason=session_expired';
        } else {
          window.location.href = '/login';
        }
      }
      throw new Error('Session expired');
    }

    return this.handleResponse<T>(response);
  }

  // =========================================================================
  // Bootstrap / Tenant
  // =========================================================================

  async bootstrapTenant(
    data: TenantCreateWithBootstrap
  ): Promise<BootstrapResponse> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/tenants`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });

    return this.handleResponse<BootstrapResponse>(response);
  }

  // =========================================================================
  // Auth
  // =========================================================================

  async login(data: LoginRequest): Promise<CookieAuthResponse> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/auth/login`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });

    return this.handleResponse<CookieAuthResponse>(response);
  }

  async devLogin(data: DevLoginRequest): Promise<CookieAuthResponse> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/auth/dev-login`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(data),
    });

    return this.handleResponse<CookieAuthResponse>(response);
  }

  async getMe(): Promise<CurrentUserResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<CurrentUserResponse>(`${baseUrl}/auth/me`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async logout(): Promise<void> {
    const baseUrl = getApiBaseUrl();
    try {
      await fetch(`${baseUrl}/auth/logout`, {
        method: 'POST',
        headers: this.getHeaders(),
        credentials: 'include',
      });
    } catch {
      // Ignore errors - we're logging out anyway
    }
    clearSession();
  }

  async logoutAll(): Promise<void> {
    const baseUrl = getApiBaseUrl();
    await this.fetchWithRetry<{ message: string }>(
      `${baseUrl}/auth/logout-all`,
      {
        method: 'POST',
        headers: this.getHeaders(),
      }
    );
    clearSession();
  }

  // =========================================================================
  // Documents
  // =========================================================================

  async listDocuments(
    limit: number = 100,
    offset: number = 0
  ): Promise<DocumentListResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    return this.fetchWithRetry<DocumentListResponse>(
      `${baseUrl}/documents?${params}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  async getDocument(documentId: string): Promise<DocumentWithVersions> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<DocumentWithVersions>(
      `${baseUrl}/documents/${documentId}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  async uploadDocument(
    file: File,
    metadata: {
      title: string;
      document_type: string;
      jurisdiction: string;
      language: string;
      confidentiality: string;
    }
  ): Promise<DocumentCreateResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', metadata.title);
    formData.append('document_type', metadata.document_type);
    formData.append('jurisdiction', metadata.jurisdiction);
    formData.append('language', metadata.language);
    formData.append('confidentiality', metadata.confidentiality);

    return this.fetchWithRetry<DocumentCreateResponse>(`${baseUrl}/documents`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
      body: formData,
    });
  }

  async uploadVersion(
    documentId: string,
    file: File
  ): Promise<DocumentVersionCreateResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();
    formData.append('file', file);

    return this.fetchWithRetry<DocumentVersionCreateResponse>(
      `${baseUrl}/documents/${documentId}/versions`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/json',
        },
        body: formData,
      }
    );
  }

  getDownloadUrl(documentId: string, versionId: string): string {
    const baseUrl = getApiBaseUrl();
    return `${baseUrl}/documents/${documentId}/versions/${versionId}/download`;
  }

  async downloadVersion(documentId: string, versionId: string): Promise<Blob> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/documents/${documentId}/versions/${versionId}/download`,
      {
        method: 'GET',
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );

    if (!response.ok) {
      throw new Error(`Download failed: ${response.status}`);
    }

    return response.blob();
  }

  // =========================================================================
  // Legal Research
  // =========================================================================

  async legalResearch(
    data: LegalResearchRequest
  ): Promise<LegalResearchResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<LegalResearchResponse>(
      `${baseUrl}/workflows/legal-research`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  // =========================================================================
  // Contract Review
  // =========================================================================

  async contractReview(
    data: ContractReviewRequest
  ): Promise<ContractReviewResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ContractReviewResponse>(
      `${baseUrl}/workflows/contract-review`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  // =========================================================================
  // Clause Redlines
  // =========================================================================

  async clauseRedlines(
    data: ClauseRedlinesRequest
  ): Promise<ClauseRedlinesResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ClauseRedlinesResponse>(
      `${baseUrl}/workflows/clause-redlines`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  // =========================================================================
  // Policy Profiles (Admin only)
  // =========================================================================

  /**
   * Create a policy profile for the tenant.
   * Requires ADMIN role.
   *
   * @param data - Policy profile creation data
   */
  async createPolicyProfile(
    data: PolicyProfileCreateRequest
  ): Promise<PolicyProfileResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<PolicyProfileResponse>(
      `${baseUrl}/policy-profiles`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  /**
   * Attach a policy profile to a workspace.
   * Requires ADMIN role.
   *
   * @param workspaceId - The workspace ID to attach the policy to
   * @param policyProfileId - The policy profile ID to attach
   */
  async attachWorkspacePolicyProfile(
    workspaceId: string,
    policyProfileId: string
  ): Promise<WorkspaceResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<WorkspaceResponse>(
      `${baseUrl}/workspaces/${workspaceId}/policy-profile`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
          'X-Workspace-Id': workspaceId,
        },
        body: JSON.stringify({ policy_profile_id: policyProfileId }),
      }
    );
  }

  // =========================================================================
  // Audit (Admin only)
  // =========================================================================

  /**
   * Fetch audit log entries.
   * Requires ADMIN role.
   *
   * @param limit - Maximum number of entries to return
   * @param offset - Number of entries to skip
   * @param action - Filter by action (contains)
   * @param workspaceId - Filter by workspace ID
   */
  async getAuditLogs(
    limit: number = 50,
    offset: number = 0,
    action?: string,
    workspaceId?: string
  ): Promise<AuditLogResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
    });

    if (action) {
      params.append('action', action);
    }
    if (workspaceId) {
      params.append('workspace_id', workspaceId);
    }

    return this.fetchWithRetry<AuditLogResponse>(`${baseUrl}/audit?${params}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  // =========================================================================
  // Reindex (Admin only)
  // =========================================================================

  /**
   * Trigger reindexing of a document version.
   * Requires ADMIN role.
   *
   * @param documentId - The document ID
   * @param versionId - The version ID to reindex
   * @param replace - Whether to replace existing embeddings
   */
  async reindexVersion(
    documentId: string,
    versionId: string,
    replace: boolean = true
  ): Promise<ReindexResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams({ replace: replace.toString() });

    return this.fetchWithRetry<ReindexResponse>(
      `${baseUrl}/admin/reindex/${documentId}/${versionId}?${params}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
      }
    );
  }

  // =========================================================================
  // Member Management
  // =========================================================================

  /**
   * List all members of a workspace with user details.
   * Requires VIEWER+ role.
   *
   * @param workspaceId - The workspace ID
   */
  async listMembers(workspaceId: string): Promise<MemberWithUser[]> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<MemberWithUser[]>(
      `${baseUrl}/workspaces/${workspaceId}/members`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Add a member to a workspace by email.
   * Creates user if not exists in tenant.
   * Requires ADMIN role.
   *
   * @param workspaceId - The workspace ID
   * @param data - Member invite data (email, optional full_name, role)
   */
  async addMember(
    workspaceId: string,
    data: MemberInviteRequest
  ): Promise<MemberWithUser> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<MemberWithUser>(
      `${baseUrl}/workspaces/${workspaceId}/members`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  /**
   * Update a member's role in a workspace.
   * Requires ADMIN role.
   * Cannot demote the last admin.
   *
   * @param workspaceId - The workspace ID
   * @param membershipId - The membership ID to update
   * @param role - The new role
   */
  async updateMemberRole(
    workspaceId: string,
    membershipId: string,
    role: 'ADMIN' | 'EDITOR' | 'VIEWER'
  ): Promise<MemberWithUser> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<MemberWithUser>(
      `${baseUrl}/workspaces/${workspaceId}/members/${membershipId}`,
      {
        method: 'PATCH',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ role }),
      }
    );
  }

  /**
   * Remove a member from a workspace.
   * Requires ADMIN role.
   * Cannot remove the last admin.
   *
   * @param workspaceId - The workspace ID
   * @param membershipId - The membership ID to remove
   */
  async removeMember(workspaceId: string, membershipId: string): Promise<void> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/workspaces/${workspaceId}/members/${membershipId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
        credentials: 'include',
      }
    );

    if (response.status === 401 && !isServer()) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        const retryResponse = await fetch(
          `${baseUrl}/workspaces/${workspaceId}/members/${membershipId}`,
          {
            method: 'DELETE',
            headers: this.getHeaders(),
            credentials: 'include',
          }
        );
        if (!retryResponse.ok && retryResponse.status !== 204) {
          await this.handleDeleteError(retryResponse);
        }
        return;
      }
      clearSession();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    if (!response.ok && response.status !== 204) {
      await this.handleDeleteError(response);
    }
  }

  private async handleDeleteError(response: Response): Promise<never> {
    let errorDetail: string = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const error: ApiError = await response.json();
      if (typeof error.detail === 'object' && error.detail !== null) {
        errorDetail = error.detail.message;
      } else if (typeof error.detail === 'string') {
        errorDetail = error.detail;
      }
    } catch {
      // Could not parse JSON, use default error message
    }
    throw new Error(errorDetail);
  }

  // =========================================================================
  // Document Text & Chunks (for Evidence Viewer)
  // =========================================================================

  /**
   * Get extracted text for a document version.
   * Requires VIEWER role or higher.
   *
   * @param documentId - The document ID
   * @param versionId - The version ID
   * @param includeText - Whether to include the full extracted text (default: true)
   */
  async getDocumentVersionText(
    documentId: string,
    versionId: string,
    includeText: boolean = true
  ): Promise<DocumentTextResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams({
      include_text: includeText.toString(),
    });

    return this.fetchWithRetry<DocumentTextResponse>(
      `${baseUrl}/documents/${documentId}/versions/${versionId}/text?${params}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Get all chunks for a document version.
   * Requires VIEWER role or higher.
   *
   * @param documentId - The document ID
   * @param versionId - The version ID
   */
  async getDocumentVersionChunks(
    documentId: string,
    versionId: string
  ): Promise<DocumentChunksResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<DocumentChunksResponse>(
      `${baseUrl}/documents/${documentId}/versions/${versionId}/chunks`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  // =========================================================================
  // DOCX Export
  // =========================================================================

  /**
   * Export contract review results to DOCX.
   * Downloads the file as a blob.
   *
   * @param metadata - Document metadata for the export
   * @param workflowResult - The contract review result to export
   */
  async exportContractReviewDocx(
    metadata: ExportDocumentMetadata,
    workflowResult: ContractReviewResponse
  ): Promise<Blob> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/exports/contract-review`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        document_metadata: metadata,
        workflow_result: workflowResult,
      }),
    });

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const error: ApiError = await response.json();
        if (typeof error.detail === 'string') {
          errorDetail = error.detail;
        }
      } catch {
        // Could not parse JSON
      }
      throw new Error(errorDetail);
    }

    return response.blob();
  }

  /**
   * Export clause redlines results to DOCX.
   * Downloads the file as a blob.
   *
   * @param metadata - Document metadata for the export
   * @param workflowResult - The clause redlines result to export
   */
  async exportClauseRedlinesDocx(
    metadata: ExportDocumentMetadata,
    workflowResult: ClauseRedlinesResponse
  ): Promise<Blob> {
    const baseUrl = getApiBaseUrl();
    const response = await fetch(`${baseUrl}/exports/clause-redlines`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        document_metadata: metadata,
        workflow_result: workflowResult,
      }),
    });

    if (!response.ok) {
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const error: ApiError = await response.json();
        if (typeof error.detail === 'string') {
          errorDetail = error.detail;
        }
      } catch {
        // Could not parse JSON
      }
      throw new Error(errorDetail);
    }

    return response.blob();
  }

  // =========================================================================
  // Global Legal Corpus (Platform Admin Only)
  // =========================================================================

  /**
   * List legal instruments in the global corpus.
   * Requires platform admin privileges.
   */
  async listLegalInstruments(
    options: {
      limit?: number;
      offset?: number;
      jurisdiction?: string;
      instrument_type?: string;
      status?: string;
    } = {}
  ): Promise<LegalInstrumentListResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams();
    if (options.limit) params.set('limit', options.limit.toString());
    if (options.offset) params.set('offset', options.offset.toString());
    if (options.jurisdiction) params.set('jurisdiction', options.jurisdiction);
    if (options.instrument_type)
      params.set('instrument_type', options.instrument_type);
    if (options.status) params.set('status', options.status);

    return this.fetchWithRetry<LegalInstrumentListResponse>(
      `${baseUrl}/global/legal-instruments?${params}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Get a legal instrument with all versions.
   * Requires platform admin privileges.
   */
  async getLegalInstrument(
    instrumentId: string
  ): Promise<LegalInstrumentWithVersions> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<LegalInstrumentWithVersions>(
      `${baseUrl}/global/legal-instruments/${instrumentId}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Create a new legal instrument with optional initial version.
   * Requires platform admin privileges.
   */
  async createLegalInstrument(
    data: LegalInstrumentCreateData,
    file?: File
  ): Promise<LegalInstrumentCreateResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();

    formData.append('jurisdiction', data.jurisdiction);
    formData.append('instrument_type', data.instrument_type);
    formData.append('title', data.title);
    if (data.title_ar) formData.append('title_ar', data.title_ar);
    if (data.official_source_url)
      formData.append('official_source_url', data.official_source_url);
    if (data.published_at) formData.append('published_at', data.published_at);
    if (data.effective_at) formData.append('effective_at', data.effective_at);
    if (data.status) formData.append('status', data.status);

    if (file && data.version_label && data.language) {
      formData.append('version_label', data.version_label);
      formData.append('language', data.language);
      formData.append('file', file);
    }

    const response = await fetch(`${baseUrl}/global/legal-instruments`, {
      method: 'POST',
      headers: this.getFormDataHeaders(),
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    return response.json();
  }

  /**
   * Upload a new version for a legal instrument.
   * Requires platform admin privileges.
   */
  async uploadLegalVersion(
    instrumentId: string,
    versionLabel: string,
    language: string,
    file: File
  ): Promise<LegalVersionCreateResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();
    formData.append('version_label', versionLabel);
    formData.append('language', language);
    formData.append('file', file);

    const response = await fetch(
      `${baseUrl}/global/legal-instruments/${instrumentId}/versions`,
      {
        method: 'POST',
        headers: this.getFormDataHeaders(),
        credentials: 'include',
        body: formData,
      }
    );

    if (!response.ok) {
      await this.handleError(response);
    }

    return response.json();
  }

  /**
   * Reindex a legal instrument version.
   * Requires platform admin privileges.
   */
  async reindexLegalVersion(
    instrumentId: string,
    versionId: string,
    replace: boolean = true
  ): Promise<ReindexLegalVersionResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ReindexLegalVersionResponse>(
      `${baseUrl}/global/legal-instruments/${instrumentId}/versions/${versionId}/reindex?replace=${replace}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Import a gcc-harvester snapshot ZIP into the global legal corpus.
   * Requires platform admin privileges.
   *
   * The request is multipart/form-data with field name 'snapshot_zip' to match backend.
   * Content-Type header is NOT set manually to allow browser to set boundary correctly.
   *
   * @param file - The snapshot ZIP file to import
   * @returns Import result with counts and any failures
   */
  async importSnapshot(file: File): Promise<SnapshotImportResponse> {
    const baseUrl = getApiBaseUrl();
    const formData = new FormData();
    // Field name MUST be 'snapshot_zip' to match backend endpoint
    formData.append('snapshot_zip', file);

    // Do not set Content-Type header - browser will set it with correct boundary
    const response = await fetch(`${baseUrl}/global/legal-import/snapshot`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      await this.handleError(response);
    }

    return response.json();
  }

  /**
   * Get the indexing status of an import batch.
   * Requires platform admin privileges.
   *
   * @param importBatchId - UUID of the import batch
   * @returns Status with indexed/pending counts
   */
  async getImportBatchStatus(
    importBatchId: string
  ): Promise<BatchStatusResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<BatchStatusResponse>(
      `${baseUrl}/global/legal-import/batches/${importBatchId}/status`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Reindex versions from an import batch.
   * Requires platform admin privileges.
   *
   * @param importBatchId - UUID of the import batch
   * @param maxVersions - Maximum versions to reindex (default 25, max 5000)
   * @param indexAll - If true, index ALL pending versions regardless of maxVersions
   * @returns Reindex result with counts and failures
   */
  async reindexImportBatch(
    importBatchId: string,
    maxVersions: number = 25,
    indexAll: boolean = false
  ): Promise<BatchReindexResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<BatchReindexResponse>(
      `${baseUrl}/global/legal-import/reindex`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          import_batch_id: importBatchId,
          max_versions: maxVersions,
          index_all: indexAll,
        }),
      }
    );
  }

  /**
   * Purge all legal corpus data.
   * Requires platform admin privileges.
   * WARNING: This is a destructive operation and cannot be undone.
   *
   * @returns Purge result with counts of deleted items
   */
  async purgeAllLegalCorpus(): Promise<PurgeResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<PurgeResponse>(
      `${baseUrl}/global/legal-import/purge-all`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Search the global legal corpus.
   * Available to all authenticated users.
   */
  async searchGlobalLegal(
    query: string,
    options: {
      limit?: number;
      jurisdiction?: string;
      instrument_type?: string;
      language?: string;
    } = {}
  ): Promise<GlobalLegalSearchResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<GlobalLegalSearchResponse>(
      `${baseUrl}/global/search/chunks`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query,
          limit: options.limit || 10,
          jurisdiction: options.jurisdiction || null,
          instrument_type: options.instrument_type || null,
          language: options.language || null,
        }),
      }
    );
  }

  // =========================================================================
  // Global Legal Viewer (Read-Only, All Authenticated Users)
  // =========================================================================

  /**
   * List global legal instruments (read-only viewer).
   * Respects workspace policy for jurisdiction filtering.
   */
  async listGlobalLegalInstruments(
    options: {
      limit?: number;
      offset?: number;
      jurisdiction?: string;
      instrument_type?: string;
    } = {}
  ): Promise<ViewerInstrumentListResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams();
    if (options.limit) params.set('limit', options.limit.toString());
    if (options.offset) params.set('offset', options.offset.toString());
    if (options.jurisdiction) params.set('jurisdiction', options.jurisdiction);
    if (options.instrument_type)
      params.set('instrument_type', options.instrument_type);

    return this.fetchWithRetry<ViewerInstrumentListResponse>(
      `${baseUrl}/global/legal/instruments?${params}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Get a global legal instrument detail (read-only viewer).
   * Respects workspace policy for jurisdiction filtering.
   */
  async getGlobalLegalInstrumentDetail(
    instrumentId: string
  ): Promise<ViewerInstrumentDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ViewerInstrumentDetail>(
      `${baseUrl}/global/legal/instruments/${instrumentId}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Get a global legal version detail (read-only viewer).
   * Respects workspace policy for jurisdiction filtering.
   */
  async getGlobalLegalVersionDetail(
    instrumentId: string,
    versionId: string
  ): Promise<ViewerVersionDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ViewerVersionDetail>(
      `${baseUrl}/global/legal/instruments/${instrumentId}/versions/${versionId}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Get chunks for a global legal version (read-only viewer).
   * Respects workspace policy for jurisdiction filtering.
   */
  async getGlobalLegalVersionChunks(
    instrumentId: string,
    versionId: string
  ): Promise<ViewerChunksResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ViewerChunksResponse>(
      `${baseUrl}/global/legal/instruments/${instrumentId}/versions/${versionId}/chunks`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  /**
   * Get a single chunk with context (read-only viewer).
   * Respects workspace policy for jurisdiction filtering.
   */
  async getGlobalLegalChunk(
    instrumentId: string,
    versionId: string,
    chunkId: string
  ): Promise<LegalChunkWithContext> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<LegalChunkWithContext>(
      `${baseUrl}/global/legal/instruments/${instrumentId}/versions/${versionId}/chunks/${chunkId}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  // =========================================================================
  // Platform operator (is_platform_admin)
  // =========================================================================

  async operatorListTenants(): Promise<
    Array<{
      id: string;
      name: string;
      primary_jurisdiction: string;
      data_residency_policy: string;
      created_at: string;
    }>
  > {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry(`${baseUrl}/operator/tenants`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async operatorCreateTenant(
    data: TenantCreateWithBootstrap
  ): Promise<BootstrapResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<BootstrapResponse>(
      `${baseUrl}/operator/tenants`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  async operatorListUsers(
    params: {
      tenant_id?: string;
      search?: string;
    } = {}
  ): Promise<OperatorUserRow[]> {
    const baseUrl = getApiBaseUrl();
    const q = new URLSearchParams();
    if (params.tenant_id) q.set('tenant_id', params.tenant_id);
    if (params.search) q.set('search', params.search);
    const suffix = q.toString() ? `?${q}` : '';
    return this.fetchWithRetry<OperatorUserRow[]>(
      `${baseUrl}/operator/users${suffix}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  async operatorCreateUser(
    tenantId: string,
    body: { email: string; full_name?: string; password: string }
  ): Promise<OperatorUserRow> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<OperatorUserRow>(
      `${baseUrl}/operator/tenants/${tenantId}/users`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );
  }

  async operatorPatchUser(
    userId: string,
    body: {
      is_active?: boolean;
      is_platform_admin?: boolean;
      password?: string;
    }
  ): Promise<OperatorUserRow> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<OperatorUserRow>(
      `${baseUrl}/operator/users/${userId}`,
      {
        method: 'PATCH',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      }
    );
  }

  /**
   * Aggregated dashboard statistics for scraping and the legal corpus.
   */
  async getScrapingStats(): Promise<ScrapingStatsResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ScrapingStatsResponse>(
      `${baseUrl}/operator/scraping/stats`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  /**
   * List configured scraping sources (platform admin).
   */
  async getScrapingSources(): Promise<ScrapingSourceResponse[]> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ScrapingSourceResponse[]>(
      `${baseUrl}/operator/scraping/sources`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async createScrapingSource(
    data: ScrapingSourceCreate
  ): Promise<ScrapingSourceResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ScrapingSourceResponse>(
      `${baseUrl}/operator/scraping/sources`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  async updateScrapingSource(
    id: string,
    data: ScrapingSourceUpdate
  ): Promise<ScrapingSourceResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ScrapingSourceResponse>(
      `${baseUrl}/operator/scraping/sources/${id}`,
      {
        method: 'PATCH',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );
  }

  async deleteScrapingSource(id: string): Promise<void> {
    const baseUrl = getApiBaseUrl();
    const url = `${baseUrl}/operator/scraping/sources/${id}`;

    const runDelete = async (): Promise<Response> => {
      return fetch(url, {
        method: 'DELETE',
        headers: this.getHeaders(),
        credentials: 'include',
      });
    };

    let response = await runDelete();

    if (response.status === 401 && !isServer()) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        response = await runDelete();
      } else {
        clearSession();
        window.location.href = '/login';
        throw new Error('Session expired');
      }
    }

    if (!response.ok && response.status !== 204) {
      let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const error: ApiError = await response.json();
        if (typeof error.detail === 'object' && error.detail !== null) {
          errorDetail =
            (error.detail as { message?: string }).message || errorDetail;
        } else if (typeof error.detail === 'string') {
          errorDetail = error.detail;
        }
      } catch {
        // ignore
      }
      throw new ApiClientError(errorDetail, response.status, null);
    }
  }

  async triggerScrapingSource(id: string): Promise<ScrapingTriggerResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ScrapingTriggerResponse>(
      `${baseUrl}/operator/scraping/sources/${id}/trigger`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
        body: '{}',
      }
    );
  }

  async getScrapingJobs(
    params: { source_id?: string; limit?: number } = {}
  ): Promise<ScrapingJobResponse[]> {
    const baseUrl = getApiBaseUrl();
    const q = new URLSearchParams();
    if (params.source_id) q.set('source_id', params.source_id);
    if (params.limit != null) q.set('limit', String(params.limit));
    const suffix = q.toString() ? `?${q}` : '';
    return this.fetchWithRetry<ScrapingJobResponse[]>(
      `${baseUrl}/operator/scraping/jobs${suffix}`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async getScrapingJob(id: string): Promise<ScrapingJobDetailResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<ScrapingJobDetailResponse>(
      `${baseUrl}/operator/scraping/jobs/${id}`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  // =========================================================================
  // Legal News
  // =========================================================================

  async getLegalNews(query?: LegalNewsQuery): Promise<LegalNewsResponse> {
    const baseUrl = getApiBaseUrl();
    const params = new URLSearchParams();
    if (query?.category) params.set('category', query.category);
    if (query?.jurisdiction) params.set('jurisdiction', query.jurisdiction);
    if (query?.importance) params.set('importance', query.importance);
    if (query?.limit) params.set('limit', String(query.limit));
    if (query?.offset) params.set('offset', String(query.offset));
    const qs = params.toString();
    return this.fetchWithRetry<LegalNewsResponse>(
      `${baseUrl}/news/legal${qs ? `?${qs}` : ''}`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async getBreakingNews(): Promise<BreakingNewsResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<BreakingNewsResponse>(
      `${baseUrl}/news/breaking`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async fileNewsToWiki(itemId: string): Promise<WikiFilingResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<WikiFilingResponse>(
      `${baseUrl}/news/${itemId}/file-to-wiki`,
      {
        method: 'POST',
        headers: {
          ...this.getHeaders(),
          'Content-Type': 'application/json',
        },
      }
    );
  }

  async refreshNews(): Promise<NewsRefreshResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<NewsRefreshResponse>(`${baseUrl}/news/refresh`, {
      method: 'POST',
      headers: {
        ...this.getHeaders(),
        'Content-Type': 'application/json',
      },
    });
  }

  async getNewsSources(): Promise<NewsSourcesResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<NewsSourcesResponse>(`${baseUrl}/news/sources`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async updateNewsSources(
    enabledSourceIds: string[]
  ): Promise<NewsSourcesResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<NewsSourcesResponse>(`${baseUrl}/news/sources`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify({ enabled_source_ids: enabledSourceIds }),
    });
  }

  private getFormDataHeaders(): Record<string, string> {
    // Don't set Content-Type for FormData - browser will set it with boundary
    return {};
  }

  private async handleError(response: Response): Promise<never> {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    let errorCode: string | null = null;
    try {
      const error: ApiError = await response.json();
      if (typeof error.detail === 'string') {
        errorDetail = error.detail;
      } else if (error.detail && typeof error.detail === 'object') {
        errorDetail =
          (error.detail as { message?: string }).message || errorDetail;
        errorCode =
          (error.detail as { error_code?: string }).error_code || null;
      }
    } catch {
      // Could not parse JSON
    }
    throw new ApiClientError(errorDetail, response.status, errorCode);
  }

  // ===========================================================================
  // Soul & Digital Twin
  // ===========================================================================

  async getMySoul(): Promise<SoulDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<SoulDetail>(`${baseUrl}/soul`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async getAdminSoulList(): Promise<{ users: SoulSummary[] }> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<{ users: SoulSummary[] }>(
      `${baseUrl}/soul/admin/list`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  async getAdminSoulDetail(userId: string): Promise<SoulDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<SoulDetail>(`${baseUrl}/soul/admin/${userId}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async updateSoulProfile(
    userId: string,
    document: Record<string, unknown>
  ): Promise<SoulDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<SoulDetail>(
      `${baseUrl}/soul/admin/${userId}/profile`,
      {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify({ document }),
      }
    );
  }

  async updateSoulTwin(
    userId: string,
    document: Record<string, unknown>
  ): Promise<SoulDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<SoulDetail>(
      `${baseUrl}/soul/admin/${userId}/twin`,
      {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify({ document }),
      }
    );
  }

  async updateSoulDimensions(
    userId: string,
    dimensions: SoulDimension[]
  ): Promise<SoulDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<SoulDetail>(
      `${baseUrl}/soul/admin/${userId}/dimensions`,
      {
        method: 'PUT',
        headers: this.getHeaders(),
        body: JSON.stringify({ dimensions }),
      }
    );
  }

  // ===========================================================================
  // Organizations
  // ===========================================================================

  async listOrganizations(workspaceId: string): Promise<Organization[]> {
    const baseUrl = getApiBaseUrl();
    const data = await this.fetchWithRetry<{ organizations: Organization[] }>(
      `${baseUrl}/workspaces/${workspaceId}/organizations`,
      { method: 'GET', headers: this.getHeaders() }
    );
    return data.organizations;
  }

  async createOrganization(
    workspaceId: string,
    body: CreateOrgRequest
  ): Promise<Organization> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<Organization>(
      `${baseUrl}/workspaces/${workspaceId}/organizations`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(body),
      }
    );
  }

  async getOrganization(
    workspaceId: string,
    orgId: string
  ): Promise<OrganizationDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<OrganizationDetail>(
      `${baseUrl}/workspaces/${workspaceId}/organizations/${orgId}`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async updateOrganization(
    workspaceId: string,
    orgId: string,
    body: Partial<CreateOrgRequest>
  ): Promise<Organization> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<Organization>(
      `${baseUrl}/workspaces/${workspaceId}/organizations/${orgId}`,
      {
        method: 'PATCH',
        headers: this.getHeaders(),
        body: JSON.stringify(body),
      }
    );
  }

  async deleteOrganization(workspaceId: string, orgId: string): Promise<void> {
    const baseUrl = getApiBaseUrl();
    await this.fetchWithRetry<void>(
      `${baseUrl}/workspaces/${workspaceId}/organizations/${orgId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
      }
    );
  }

  async addOrgMember(
    workspaceId: string,
    orgId: string,
    userId: string,
    role: string = 'MEMBER'
  ): Promise<void> {
    const baseUrl = getApiBaseUrl();
    await this.fetchWithRetry<void>(
      `${baseUrl}/workspaces/${workspaceId}/organizations/${orgId}/members`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ user_id: userId, role }),
      }
    );
  }

  async removeOrgMember(
    workspaceId: string,
    orgId: string,
    userId: string
  ): Promise<void> {
    const baseUrl = getApiBaseUrl();
    await this.fetchWithRetry<void>(
      `${baseUrl}/workspaces/${workspaceId}/organizations/${orgId}/members/${userId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
      }
    );
  }

  // ===========================================================================
  // Wiki
  // ===========================================================================

  async getWikiPages(params?: {
    search?: string;
    category?: string;
    jurisdiction?: string;
    limit?: number;
    offset?: number;
  }): Promise<WikiPageListResponse> {
    const baseUrl = getApiBaseUrl();
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.category) qs.set('category', params.category);
    if (params?.jurisdiction) qs.set('jurisdiction', params.jurisdiction);
    if (params?.limit) qs.set('limit', params.limit.toString());
    if (params?.offset) qs.set('offset', params.offset.toString());
    const q = qs.toString();
    return this.fetchWithRetry<WikiPageListResponse>(
      `${baseUrl}/wiki/pages${q ? '?' + q : ''}`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async getWikiPage(slug: string): Promise<WikiPageDetail> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<WikiPageDetail>(
      `${baseUrl}/wiki/pages/${slug}`,
      {
        method: 'GET',
        headers: this.getHeaders(),
      }
    );
  }

  async updateWikiPage(
    slug: string,
    instruction: string
  ): Promise<{ status: string; page_slug: string; version: number }> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry(`${baseUrl}/wiki/pages/${slug}/update`, {
      method: 'POST',
      headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ instruction }),
    });
  }

  async getWikiGraph(): Promise<WikiGraphResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<WikiGraphResponse>(`${baseUrl}/wiki/graph`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async getWikiLogs(params?: {
    operation?: string;
    limit?: number;
    offset?: number;
  }): Promise<WikiLogListResponse> {
    const baseUrl = getApiBaseUrl();
    const qs = new URLSearchParams();
    if (params?.operation) qs.set('operation', params.operation);
    if (params?.limit) qs.set('limit', params.limit.toString());
    if (params?.offset) qs.set('offset', params.offset.toString());
    const q = qs.toString();
    return this.fetchWithRetry<WikiLogListResponse>(
      `${baseUrl}/wiki/log${q ? '?' + q : ''}`,
      { method: 'GET', headers: this.getHeaders() }
    );
  }

  async getWikiHealth(): Promise<WikiHealthResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<WikiHealthResponse>(`${baseUrl}/wiki/health`, {
      method: 'GET',
      headers: this.getHeaders(),
    });
  }

  async runWikiLint(): Promise<{ status: string; message: string }> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry(`${baseUrl}/wiki/lint`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
  }

  async ingestToWiki(data: {
    source_text: string;
    source_title: string;
    source_type?: string;
    metadata?: Record<string, unknown>;
  }): Promise<WikiIngestResponse> {
    const baseUrl = getApiBaseUrl();
    return this.fetchWithRetry<WikiIngestResponse>(`${baseUrl}/wiki/ingest`, {
      method: 'POST',
      headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }
}

// ============================================================================
// Soul & Digital Twin Types
// ============================================================================

export interface SoulDimension {
  id: string;
  label: string;
  value: number;
  confidence: number;
  category: 'identity' | 'style' | 'expertise';
}

export interface SoulSummary {
  user_id: string;
  email: string;
  full_name: string | null;
  has_twin: boolean;
  interaction_count: number;
  maturity: string;
  consolidated_at: string | null;
}

export interface SoulDetail {
  id: string;
  user_id: string;
  profile: Record<string, unknown>;
  preferences: Record<string, unknown>;
  work_patterns: Record<string, unknown>;
  drafting_style: Record<string, unknown>;
  review_priorities: Record<string, unknown>;
  learned_corrections: unknown[];
  personality_model: Record<string, unknown>;
  soul_dimensions: SoulDimension[];
  interaction_count: number;
  maturity: string;
  consolidated_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  user_email?: string;
  user_full_name?: string;
}

// ============================================================================
// Organization Types
// ============================================================================

export interface Organization {
  id: string;
  name: string;
  description: string | null;
  master_user_id: string | null;
  member_count: number;
  created_at: string;
}

export interface OrganizationDetail extends Organization {
  members: OrgMember[];
}

export interface OrgMember {
  user_id: string;
  email: string;
  full_name: string | null;
  role: 'MASTER' | 'MEMBER';
}

export interface CreateOrgRequest {
  name: string;
  description?: string;
  master_user_id?: string;
}

// ============================================================================
// Global Legal Corpus Types
// ============================================================================

export interface LegalVersionSummary {
  id: string;
  version_label: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  language: string;
  is_indexed: boolean;
  indexed_at: string | null;
  embedding_model: string | null;
  created_at: string;
  uploaded_by_user_id: string | null;
}

export interface LegalInstrumentResponse {
  id: string;
  jurisdiction: string;
  instrument_type: string;
  title: string;
  title_ar: string | null;
  official_source_url: string | null;
  published_at: string | null;
  effective_at: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  created_by_user_id: string | null;
}

export interface LegalInstrumentWithLatestVersion extends LegalInstrumentResponse {
  latest_version: LegalVersionSummary | null;
}

export interface LegalInstrumentWithVersions extends LegalInstrumentResponse {
  versions: LegalVersionSummary[];
}

export interface LegalInstrumentListResponse {
  items: LegalInstrumentWithLatestVersion[];
  total: number;
  limit: number;
  offset: number;
}

export interface LegalInstrumentCreateData {
  jurisdiction: string;
  instrument_type: string;
  title: string;
  title_ar?: string;
  official_source_url?: string;
  published_at?: string;
  effective_at?: string;
  status?: string;
  // Optional initial version
  version_label?: string;
  language?: string;
}

export interface LegalInstrumentCreateResponse {
  instrument: LegalInstrumentResponse;
  version: LegalVersionSummary | null;
}

export interface LegalVersionCreateResponse {
  version: LegalVersionSummary;
  instrument_id: string;
}

export interface ReindexLegalVersionResponse {
  instrument_id: string;
  version_id: string;
  chunks_indexed: number;
  chunks_skipped: number;
  embedding_model: string;
}

/**
 * Source types for evidence/search results
 * Used to distinguish between workspace documents and global legal corpus
 */
export type SourceType = 'workspace_document' | 'global_legal';

export interface GlobalLegalChunkResult {
  chunk_id: string;
  chunk_index: number;
  snippet: string;
  instrument_id: string;
  version_id: string;
  instrument_title: string;
  instrument_title_ar: string | null;
  instrument_type: string;
  jurisdiction: string;
  language: string;
  published_at: string | null;
  effective_at: string | null;
  official_source_url: string | null;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
  vector_score: number;
  keyword_score: number;
  final_score: number;
  // Source provenance (user trust)
  source_type: SourceType;
  source_label: string; // Human-readable label, e.g., "Saudi Companies Law (2022)"
}

export interface GlobalLegalSearchResponse {
  query: string;
  total: number;
  results: GlobalLegalChunkResult[];
}

// =============================================================================
// Global Legal Viewer Types (Read-Only)
// =============================================================================

export interface LegalChunkPreview {
  id: string;
  chunk_index: number;
  preview: string;
  page_start: number | null;
}

export interface LegalChunkDetail {
  id: string;
  chunk_index: number;
  text: string;
  char_start: number;
  char_end: number;
  page_start: number | null;
  page_end: number | null;
}

export interface LegalChunkWithContext {
  chunk: LegalChunkDetail;
  prev_chunk: LegalChunkPreview | null;
  next_chunk: LegalChunkPreview | null;
}

export interface ViewerVersionSummary {
  id: string;
  version_label: string;
  language: string;
  is_indexed: boolean;
  created_at: string;
}

export interface ViewerInstrumentListItem {
  id: string;
  title: string;
  title_ar: string | null;
  jurisdiction: string;
  instrument_type: string;
  status: string;
  published_at: string | null;
  effective_at: string | null;
  official_source_url: string | null;
  latest_version_date: string | null;
}

export interface ViewerInstrumentListResponse {
  items: ViewerInstrumentListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ViewerInstrumentDetail {
  id: string;
  title: string;
  title_ar: string | null;
  jurisdiction: string;
  instrument_type: string;
  status: string;
  published_at: string | null;
  effective_at: string | null;
  official_source_url: string | null;
  created_at: string;
  versions: ViewerVersionSummary[];
}

export interface ViewerVersionDetail {
  id: string;
  version_label: string;
  language: string;
  is_indexed: boolean;
  indexed_at: string | null;
  file_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  instrument_id: string;
  instrument_title: string;
  instrument_title_ar: string | null;
  jurisdiction: string;
  instrument_type: string;
  official_source_url: string | null;
  published_at: string | null;
  effective_at: string | null;
}

export interface ViewerChunksResponse {
  version_id: string;
  instrument_id: string;
  chunk_count: number;
  chunks: LegalChunkPreview[];
}

// =============================================================================
// Snapshot Import Types (Platform Admin Only)
// =============================================================================

export interface SnapshotImportFailure {
  record_index: number;
  source_url: string | null;
  error: string;
}

export interface SnapshotImportResponse {
  import_batch_id: string;
  instruments_created: number;
  instruments_existing: number;
  versions_created: number;
  versions_existing: number;
  failures: SnapshotImportFailure[];
  failure_count: number;
  processing_time_ms: number;
}

export interface BatchReindexFailure {
  version_id: string;
  instrument_id: string;
  error: string;
}

export interface BatchReindexResponse {
  import_batch_id: string;
  attempted: number;
  indexed: number;
  failed: number;
  failures: BatchReindexFailure[];
}

export interface BatchStatusResponse {
  import_batch_id: string;
  total_versions: number;
  indexed_versions: number;
  pending_versions: number;
  last_imported_at: string | null;
}

export interface PurgeResponse {
  instruments_deleted: number;
  versions_deleted: number;
  chunks_deleted: number;
  embeddings_deleted: number;
  texts_deleted: number;
  message: string;
}

// =============================================================================
// Legal News Types
// =============================================================================

export interface LegalNewsItem {
  id: string;
  title: string;
  title_ar?: string | null;
  summary: string | null;
  url: string;
  image_url: string | null;
  source_name: string;
  source_category: string;
  jurisdiction: string;
  published_at: string;
  importance: string;
  amin_summary?: string | null;
  wiki_filed: boolean;
  wiki_page_slug?: string | null;
  tags?: string[] | null;
  /** @deprecated kept for backward compat — use source_name */
  source?: string;
  /** @deprecated kept for backward compat — use source_category */
  category?: string;
}

export interface LegalNewsResponse {
  items: LegalNewsItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface BreakingNewsResponse {
  items: LegalNewsItem[];
}

export interface WikiFilingResponse {
  wiki_page_slug: string;
  wiki_url: string;
}

export interface NewsRefreshResponse {
  status: string;
}

export interface LegalNewsQuery {
  category?: string;
  jurisdiction?: string;
  importance?: string;
  limit?: number;
  offset?: number;
}

export interface NewsSourceEntry {
  id: string;
  name: string;
  description: string;
  category: string;
  region: string;
  enabled: boolean;
}

export interface NewsSourcesResponse {
  sources: NewsSourceEntry[];
}

// =============================================================================
// Wiki Types
// =============================================================================

export interface WikiPageSummary {
  id: string;
  slug: string;
  title: string;
  category: string;
  summary: string;
  jurisdiction: string | null;
  inbound_link_count: number;
  version: number;
  is_stale: boolean;
  has_contradictions: boolean;
  updated_at: string;
}

export interface WikiBacklink {
  slug: string;
  title: string;
  context: string;
}

export interface WikiPageDetail extends WikiPageSummary {
  content_md: string;
  source_doc_ids: string[];
  created_by_tool: string;
  created_at: string;
  backlinks: WikiBacklink[];
  outlinks: WikiBacklink[];
}

export interface WikiPageListResponse {
  items: WikiPageSummary[];
  total: number;
}

export interface WikiGraphNode {
  id: string;
  slug: string;
  title: string;
  category: string;
  jurisdiction: string | null;
  inbound_link_count: number;
}

export interface WikiGraphEdge {
  from: string;
  to: string;
  context: string;
}

export interface WikiGraphResponse {
  nodes: WikiGraphNode[];
  edges: WikiGraphEdge[];
}

export interface WikiLogEntry {
  id: string;
  operation: string;
  page_slug: string | null;
  source_description: string;
  amin_summary: string;
  pages_affected: string[];
  created_at: string;
}

export interface WikiLogListResponse {
  items: WikiLogEntry[];
  total: number;
}

export interface WikiHealthResponse {
  page_count: number;
  orphan_count: number;
  stale_count: number;
  contradiction_count: number;
}

export interface WikiIngestResponse {
  status: string;
  page_slug: string;
  page_title: string;
  action: string;
  links_created: number;
  contradictions: string[];
}

/**
 * Custom error class for API errors with status and error code
 */
export class ApiClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public errorCode: string | null
  ) {
    super(message);
    this.name = 'ApiClientError';
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
