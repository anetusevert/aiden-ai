/**
 * Standard Evidence DTO
 *
 * This module provides a unified evidence representation for both
 * workspace documents and global legal corpus results.
 *
 * Design goals:
 * - Single type for all evidence rendering
 * - No "if global then..." branching in components
 * - Clear source provenance for user trust
 */

import type {
  EvidenceChunk,
  GlobalLegalChunkResult,
  SourceType,
} from './apiClient';

// Re-export SourceType for convenience
export type { SourceType } from './apiClient';

// =============================================================================
// Core Evidence Types
// =============================================================================

/**
 * Unified evidence item that works for both workspace and global legal sources.
 *
 * All fields from both source types are included with appropriate optionality.
 * The `source_type` field determines which fields are relevant.
 */
export interface EvidenceItem {
  // =========================================================================
  // Core identification (required for all evidence)
  // =========================================================================
  /** Unique chunk identifier */
  chunk_id: string;
  /** Index of chunk within document/instrument */
  chunk_index: number;
  /** Truncated text snippet */
  snippet: string;

  // =========================================================================
  // Source provenance (required - user trust)
  // =========================================================================
  /** Source type: workspace_document or global_legal */
  source_type: SourceType;
  /** Human-readable source label (e.g., "Saudi Companies Law (2022)") */
  source_label: string;

  // =========================================================================
  // Scores (optional - may not be present in all contexts)
  // =========================================================================
  /** Combined relevance score */
  score?: number;
  /** Vector similarity score */
  vector_score?: number;
  /** Keyword match score */
  keyword_score?: number;

  // =========================================================================
  // Location/citation (optional)
  // =========================================================================
  char_start?: number;
  char_end?: number;
  page_start?: number | null;
  page_end?: number | null;

  // =========================================================================
  // Document metadata (workspace documents)
  // =========================================================================
  /** Document ID (workspace only) */
  document_id?: string;
  /** Document title (workspace only) */
  document_title?: string;
  /** Document type (workspace only) */
  document_type?: string;

  // =========================================================================
  // Instrument metadata (global legal)
  // =========================================================================
  /** Legal instrument ID (global only) */
  instrument_id?: string;
  /** Instrument title (global only) */
  instrument_title?: string;
  /** Instrument title in Arabic (global only) */
  instrument_title_ar?: string | null;
  /** Instrument type (global only) */
  instrument_type?: string;

  // =========================================================================
  // Common metadata (both sources)
  // =========================================================================
  /** Version ID */
  version_id?: string;
  /** Jurisdiction (e.g., UAE, KSA, DIFC) */
  jurisdiction?: string;
  /** Language (en, ar, mixed) */
  language?: string;

  // =========================================================================
  // Legal provenance (global legal)
  // =========================================================================
  /** Publication date (global only) */
  published_at?: string | null;
  /** Effective date (global only) */
  effective_at?: string | null;
  /** Official government source URL (global only) */
  official_source_url?: string | null;
}

// =============================================================================
// Mapping Helpers
// =============================================================================

/**
 * Workspace search result from API.
 * This extends EvidenceChunk with additional search-specific fields.
 */
export interface WorkspaceChunkResult extends EvidenceChunk {
  vector_score?: number;
  keyword_score?: number;
  source_type: 'workspace_document';
  source_label: string;
}

/**
 * Convert unified EvidenceChunk from API (which now includes source_type) to EvidenceItem.
 *
 * Works with both workspace and global legal chunks automatically based on source_type.
 */
export function toEvidenceItemFromChunk(chunk: EvidenceChunk): EvidenceItem {
  return {
    // Core
    chunk_id: chunk.chunk_id,
    chunk_index: chunk.chunk_index,
    snippet: chunk.snippet,

    // Provenance - use the chunk's source_type
    source_type: chunk.source_type || 'workspace_document',
    source_label:
      chunk.source_label ||
      chunk.document_title ||
      chunk.instrument_title ||
      '',

    // Scores
    score: chunk.final_score,

    // Location
    char_start: chunk.char_start,
    char_end: chunk.char_end,
    page_start: chunk.page_start,
    page_end: chunk.page_end,

    // Document metadata (workspace)
    document_id: chunk.document_id,
    document_title: chunk.document_title,
    document_type: chunk.document_type,
    version_id: chunk.version_id,
    jurisdiction: chunk.jurisdiction,
    language: chunk.language,

    // Instrument metadata (global legal)
    instrument_id: chunk.instrument_id,
    instrument_title: chunk.instrument_title,
    instrument_title_ar: chunk.instrument_title_ar,
    instrument_type: chunk.instrument_type,

    // Legal provenance (global legal)
    published_at: chunk.published_at,
    effective_at: chunk.effective_at,
    official_source_url: chunk.official_source_url,
  };
}

/**
 * Convert workspace search result (EvidenceChunk) to unified EvidenceItem.
 *
 * Works with both raw EvidenceChunk from API and extended WorkspaceChunkResult.
 * @deprecated Use toEvidenceItemFromChunk instead, which handles both source types.
 */
export function toEvidenceItemFromWorkspaceChunk(
  chunk: EvidenceChunk & { vector_score?: number; keyword_score?: number }
): EvidenceItem {
  return {
    // Core
    chunk_id: chunk.chunk_id,
    chunk_index: chunk.chunk_index,
    snippet: chunk.snippet,

    // Provenance - always workspace_document for this mapper
    source_type: 'workspace_document',
    source_label: chunk.source_label || chunk.document_title || '',

    // Scores
    score: chunk.final_score,
    vector_score: chunk.vector_score,
    keyword_score: chunk.keyword_score,

    // Location
    char_start: chunk.char_start,
    char_end: chunk.char_end,
    page_start: chunk.page_start,
    page_end: chunk.page_end,

    // Document metadata
    document_id: chunk.document_id,
    document_title: chunk.document_title,
    document_type: chunk.document_type,
    version_id: chunk.version_id,
    jurisdiction: chunk.jurisdiction,
    language: chunk.language,
  };
}

/**
 * Convert global legal search result to unified EvidenceItem
 */
export function toEvidenceItemFromGlobalChunk(
  chunk: GlobalLegalChunkResult
): EvidenceItem {
  return {
    // Core
    chunk_id: chunk.chunk_id,
    chunk_index: chunk.chunk_index,
    snippet: chunk.snippet,

    // Provenance
    source_type: 'global_legal',
    source_label: chunk.source_label,

    // Scores
    score: chunk.final_score,
    vector_score: chunk.vector_score,
    keyword_score: chunk.keyword_score,

    // Location
    char_start: chunk.char_start,
    char_end: chunk.char_end,
    page_start: chunk.page_start,
    page_end: chunk.page_end,

    // Instrument metadata
    instrument_id: chunk.instrument_id,
    instrument_title: chunk.instrument_title,
    instrument_title_ar: chunk.instrument_title_ar,
    instrument_type: chunk.instrument_type,
    version_id: chunk.version_id,
    jurisdiction: chunk.jurisdiction,
    language: chunk.language,

    // Legal provenance
    published_at: chunk.published_at,
    effective_at: chunk.effective_at,
    official_source_url: chunk.official_source_url,
  };
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get the display title for an evidence item
 */
export function getEvidenceTitle(item: EvidenceItem): string {
  return (
    item.source_label ||
    item.document_title ||
    item.instrument_title ||
    'Unknown Source'
  );
}

/**
 * Check if the evidence can be viewed in the internal document viewer.
 * Only workspace documents support "View in Document".
 * Global legal sources are external and do NOT have an internal viewer.
 */
export function canViewInDocument(item: EvidenceItem): boolean {
  return (
    item.source_type === 'workspace_document' &&
    !!item.document_id &&
    !!item.version_id
  );
}

/**
 * Get the internal document viewer link for workspace documents.
 * Returns null for global legal sources (they don't have internal viewers).
 */
export function getDocumentViewerLink(item: EvidenceItem): string | null {
  if (
    item.source_type !== 'workspace_document' ||
    !item.document_id ||
    !item.version_id
  ) {
    return null;
  }
  return `/documents/${item.document_id}/versions/${item.version_id}/viewer?chunkId=${item.chunk_id}`;
}

/**
 * Get the external official source URL for global legal evidence.
 * Returns null if not available or not a global legal source.
 */
export function getExternalSourceUrl(item: EvidenceItem): string | null {
  if (item.source_type === 'global_legal' && item.official_source_url) {
    return item.official_source_url;
  }
  return null;
}

/**
 * Check if evidence has an external official source that can be opened.
 * Only global legal sources may have external official URLs.
 */
export function hasOfficialSource(item: EvidenceItem): boolean {
  return item.source_type === 'global_legal' && !!item.official_source_url;
}

/**
 * Get the link to view the evidence in context.
 * For workspace: internal document viewer.
 * For global legal: official source URL if available, otherwise null.
 *
 * @deprecated Use canViewInDocument() + getDocumentViewerLink() or getExternalSourceUrl() instead.
 */
export function getEvidenceViewLink(item: EvidenceItem): string {
  if (item.source_type === 'global_legal') {
    // For global legal, prefer official source if available
    if (item.official_source_url) {
      return item.official_source_url;
    }
    // No internal viewer for global legal - return empty string
    return '';
  } else {
    // Workspace document viewer
    return `/documents/${item.document_id}/versions/${item.version_id}/viewer?chunkId=${item.chunk_id}`;
  }
}

/**
 * Get the link to the source detail page.
 * For workspace: document detail page.
 * For global legal: legal corpus instrument page (operator view).
 */
export function getEvidenceSourceLink(item: EvidenceItem): string {
  if (item.source_type === 'global_legal') {
    return `/operator/legal-corpus/${item.instrument_id}`;
  } else {
    return `/documents/${item.document_id}`;
  }
}

/**
 * Get a user-friendly description of the evidence source type.
 */
export function getSourceTypeDescription(item: EvidenceItem): string {
  if (item.source_type === 'global_legal') {
    return 'Global law sources are external references from official legal databases. They are read-only and cannot be edited.';
  }
  return 'This evidence comes from a document in your workspace.';
}

// =============================================================================
// Citation Formatting (Global Law Differentiation)
// =============================================================================

/**
 * Citation format types:
 * - Workspace citations: [1], [2], [3]...
 * - Global law citations: [GL-1], [GL-2], [GL-3]...
 */
export type CitationFormat = 'workspace' | 'global_legal';

/**
 * Format a citation index based on source type.
 *
 * @param index - The citation index (1-based)
 * @param sourceType - The source type for formatting
 * @returns Formatted citation string (e.g., "[1]" or "[GL-1]")
 */
export function formatCitationIndex(
  index: number,
  sourceType: SourceType
): string {
  if (sourceType === 'global_legal') {
    return `[GL-${index}]`;
  }
  return `[${index}]`;
}

/**
 * Check if a citation string is a global law citation.
 */
export function isGlobalLawCitation(citation: string): boolean {
  return /^\[GL-\d+\]$/.test(citation);
}

/**
 * Parse citation number from a citation string.
 * Handles both [1] and [GL-1] formats.
 */
export function parseCitationNumber(
  citation: string
): { number: number; isGlobal: boolean } | null {
  const globalMatch = citation.match(/^\[GL-(\d+)\]$/);
  if (globalMatch) {
    return { number: parseInt(globalMatch[1], 10), isGlobal: true };
  }

  const workspaceMatch = citation.match(/^\[(\d+)\]$/);
  if (workspaceMatch) {
    return { number: parseInt(workspaceMatch[1], 10), isGlobal: false };
  }

  return null;
}

/**
 * Build a citation map from evidence items.
 * Assigns unique citation indices to each evidence item, prefixed by source type.
 *
 * @param evidence - Array of evidence items
 * @returns Map of chunk_id to formatted citation string
 */
export function buildCitationMap(
  evidence: EvidenceItem[]
): Map<string, string> {
  const citationMap = new Map<string, string>();

  // Separate by source type for independent numbering
  let workspaceIndex = 1;
  let globalIndex = 1;

  for (const item of evidence) {
    if (item.source_type === 'global_legal') {
      citationMap.set(item.chunk_id, `[GL-${globalIndex}]`);
      globalIndex++;
    } else {
      citationMap.set(item.chunk_id, `[${workspaceIndex}]`);
      workspaceIndex++;
    }
  }

  return citationMap;
}
