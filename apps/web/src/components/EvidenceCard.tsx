'use client';

import React, { useCallback } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { SourceTypeBadge } from './ui/Badge';
import type { EvidenceItem, SourceType } from '@/lib/evidence';
import {
  getEvidenceTitle,
  getEvidenceSourceLink,
  canViewInDocument,
  getDocumentViewerLink,
  getExternalSourceUrl,
  getSourceTypeDescription,
  isGlobalLawCitation,
  parseCitationNumber,
} from '@/lib/evidence';

// Re-export EvidenceItem for convenience
export type { EvidenceItem } from '@/lib/evidence';

// =============================================================================
// Citation Rendering with Global Law Differentiation
// =============================================================================

/**
 * Render text with citations, differentiating workspace [1] from global law [GL-1].
 *
 * Usage:
 * ```tsx
 * <p>{renderCitationsWithDifferentiation(text)}</p>
 * ```
 */
export function renderCitationsWithDifferentiation(
  text: string,
  options?: { globalCitationTitle?: string }
): React.ReactNode[] {
  const globalTitle = options?.globalCitationTitle ?? 'Global Law Reference';
  // Match both [1] and [GL-1] patterns
  const parts = text.split(/(\[(?:GL-)?\d+\])/g);

  return parts.map((part, index) => {
    // Check for global law citation [GL-X]
    const globalMatch = part.match(/^\[GL-(\d+)\]$/);
    if (globalMatch) {
      return (
        <span key={index} className="citation-ref-global" title={globalTitle}>
          GL-{globalMatch[1]}
        </span>
      );
    }

    // Check for workspace citation [X]
    const workspaceMatch = part.match(/^\[(\d+)\]$/);
    if (workspaceMatch) {
      return (
        <span key={index} className="citation-ref">
          {workspaceMatch[1]}
        </span>
      );
    }

    // Regular text
    return part;
  });
}

/**
 * Render legacy citations (only [1], [2] format) without differentiation.
 * For backward compatibility with existing workflows.
 */
export function renderLegacyCitations(text: string): React.ReactNode[] {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      return (
        <span key={index} className="citation-ref">
          {match[1]}
        </span>
      );
    }
    return part;
  });
}

// =============================================================================
// Evidence Counts & Grouping Utilities
// =============================================================================

export interface EvidenceCounts {
  workspace: number;
  global: number;
  total: number;
}

/**
 * Count evidence by source type
 */
export function countEvidenceBySource(
  evidence: EvidenceItem[]
): EvidenceCounts {
  const workspace = evidence.filter(
    e => e.source_type === 'workspace_document'
  ).length;
  const global = evidence.filter(e => e.source_type === 'global_legal').length;
  return { workspace, global, total: evidence.length };
}

/**
 * Group evidence by source type for visual separation
 */
export function groupEvidenceBySource(evidence: EvidenceItem[]): {
  workspace: EvidenceItem[];
  global: EvidenceItem[];
} {
  return {
    workspace: evidence.filter(e => e.source_type === 'workspace_document'),
    global: evidence.filter(e => e.source_type === 'global_legal'),
  };
}

// =============================================================================
// EvidenceCard Component
// =============================================================================

export interface EvidenceCardProps {
  /** Unified evidence item (works for both workspace and global legal) */
  evidence: EvidenceItem;
  /** Show score badge */
  showScore?: boolean;
  /** Show "View in Document" link */
  showViewLink?: boolean;
  /** Maximum snippet length */
  maxSnippetLength?: number;
  /** Show "Why this was used" policy tooltip for global sources */
  showPolicyTooltip?: boolean;
}

/**
 * Evidence card component that displays evidence with proper source type distinction.
 *
 * Viewer behavior:
 * - Workspace documents: "View in Document" links to internal document viewer
 * - Global legal corpus: "View Source" links to official_source_url (external) if available
 *   - If no official URL exists, no view action is rendered (broken links are prevented)
 *
 * This ensures users can never confuse global legal sources with workspace documents,
 * and no broken or dead links are possible.
 */
export function EvidenceCard({
  evidence,
  showScore = true,
  showViewLink = true,
  maxSnippetLength = 300,
  showPolicyTooltip = false,
}: EvidenceCardProps) {
  const t = useTranslations('evidence');
  const isGlobalLegal = evidence.source_type === 'global_legal';
  const isWorkspace = evidence.source_type === 'workspace_document';

  // Policy tooltip text for global sources
  const policyTooltipText = isGlobalLegal
    ? evidence.jurisdiction
      ? t('policyTooltipJurisdiction', { jurisdiction: evidence.jurisdiction })
      : t('policyTooltipDefault')
    : undefined;

  // Truncate snippet if needed
  const snippet =
    evidence.snippet.length > maxSnippetLength
      ? evidence.snippet.slice(0, maxSnippetLength) + '...'
      : evidence.snippet;

  // Use helper functions for unified behavior
  const title = getEvidenceTitle(evidence);
  const titleLink = getEvidenceSourceLink(evidence);

  // Viewer links based on source type
  const canViewDoc = canViewInDocument(evidence);
  const documentViewerLink = getDocumentViewerLink(evidence);
  const externalSourceUrl = getExternalSourceUrl(evidence);

  // Get score (prefer score, fallback to final_score pattern)
  const displayScore = evidence.score ?? 0;

  // Source type description for tooltip
  const sourceDescription = getSourceTypeDescription(evidence);

  /**
   * Render the appropriate view action based on source type:
   * - Workspace: "View in Document" (internal link)
   * - Global with official URL: "View Source" (external link, opens in new tab)
   * - Global without official URL: No action (prevents broken links)
   */
  const renderViewAction = () => {
    if (!showViewLink) return null;

    // Workspace documents: internal document viewer
    if (isWorkspace && canViewDoc && documentViewerLink) {
      return (
        <Link href={documentViewerLink} className="view-in-doc-link">
          View in Document
        </Link>
      );
    }

    // Global legal with official source: external link
    if (isGlobalLegal && externalSourceUrl) {
      return (
        <a
          href={externalSourceUrl}
          className="view-in-doc-link external-source-link"
          target="_blank"
          rel="noopener noreferrer"
          title="Opens official government source in a new tab"
        >
          View Source ↗
        </a>
      );
    }

    // Global legal without official source: show info text (no dead link)
    if (isGlobalLegal && !externalSourceUrl) {
      return (
        <span
          className="text-xs text-muted italic"
          title="No official source URL available for this legal reference"
        >
          External source
        </span>
      );
    }

    return null;
  };

  return (
    <div
      className="workflow-evidence-item"
      data-source-type={evidence.source_type}
    >
      <div className="workflow-evidence-header">
        <div className="workflow-evidence-title-row">
          {/* Source type badge - show for both types for clarity */}
          <SourceTypeBadge
            sourceType={evidence.source_type}
            jurisdiction={evidence.jurisdiction}
          />
          <span className="workflow-evidence-doc">
            <Link href={titleLink} title={sourceDescription}>
              {title}
            </Link>
          </span>
        </div>
        {showScore && (
          <span className="workflow-evidence-score">
            {displayScore.toFixed(3)}
          </span>
        )}
      </div>

      <p className="workflow-evidence-text">{snippet}</p>

      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-muted">
          {t('chunkMeta', { index: evidence.chunk_index })}
          {evidence.page_start &&
            ` · ${t('pageMeta', { page: evidence.page_start })}`}
          {isGlobalLegal && evidence.effective_at && (
            <> · {t('effectiveMeta', { date: evidence.effective_at })}</>
          )}
        </span>

        {renderViewAction()}
      </div>

      {/* Tooltip/info for global legal sources */}
      {isGlobalLegal && (
        <div className="global-law-info-row">
          <span className="text-xs text-muted italic" title={sourceDescription}>
            {t('globalLawReadOnlyInline')}
          </span>
          {showPolicyTooltip && policyTooltipText && (
            <span className="policy-tooltip-trigger" title={policyTooltipText}>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span className="policy-tooltip-text">{t('whyIncluded')}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Global Law Explanation Banner
// =============================================================================

export interface GlobalLawExplanationBannerProps {
  /** Number of global law evidence items */
  globalEvidenceCount: number;
  /** Optional class name */
  className?: string;
}

/**
 * Trust-building banner explaining global law sources.
 * Only shown when global law evidence is present.
 */
export function GlobalLawExplanationBanner({
  globalEvidenceCount,
  className = '',
}: GlobalLawExplanationBannerProps) {
  if (globalEvidenceCount === 0) return null;

  return (
    <div className={`global-law-explanation-banner ${className}`}>
      <div className="global-law-explanation-icon">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </div>
      <div className="global-law-explanation-text">
        <span className="global-law-explanation-title">
          About Global Law References
        </span>
        <span className="global-law-explanation-desc">
          Some references below come from HeyAmin&apos;s Global Legal Library —
          a curated, read-only collection of publicly available laws. These are
          not part of your workspace documents.
        </span>
      </div>
    </div>
  );
}

// =============================================================================
// Evidence Meta Panel
// =============================================================================

export interface EvidenceMetaPanelProps {
  /** Workspace evidence count */
  workspaceCount: number;
  /** Global law evidence count */
  globalCount: number;
  /** Evidence scope used */
  evidenceScope?: 'workspace' | 'global' | 'both';
  /** Optional class name */
  className?: string;
}

/**
 * Meta panel showing evidence counts and scope.
 * Provides transparency about what sources were used.
 */
export function EvidenceMetaPanel({
  workspaceCount,
  globalCount,
  evidenceScope,
  className = '',
}: EvidenceMetaPanelProps) {
  const t = useTranslations('evidence');
  const totalCount = workspaceCount + globalCount;

  if (totalCount === 0) return null;

  const scopeLabel =
    evidenceScope === 'workspace'
      ? t('scopeWorkspace')
      : evidenceScope === 'global'
        ? t('scopeGlobal')
        : t('scopeBoth');

  return (
    <div className={`evidence-meta-panel ${className}`}>
      <div className="evidence-meta-title">{t('evidenceUsed')}</div>
      <div className="evidence-meta-items">
        {workspaceCount > 0 && (
          <div className="evidence-meta-item">
            <span className="evidence-meta-icon">📄</span>
            <span className="evidence-meta-label">
              {t('workspaceDocuments')}
            </span>
            <span className="evidence-meta-count">{workspaceCount}</span>
          </div>
        )}
        {globalCount > 0 && (
          <div className="evidence-meta-item">
            <span className="evidence-meta-icon">⚖️</span>
            <span className="evidence-meta-label">
              {t('globalLawReferencesLabel')}
            </span>
            <span className="evidence-meta-count">{globalCount}</span>
          </div>
        )}
      </div>
      {evidenceScope && (
        <div className="evidence-meta-scope">
          {t('scopeShort')} {scopeLabel}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Evidence Section Header
// =============================================================================

export interface EvidenceSectionHeaderProps {
  /** Section title */
  title: string;
  /** Number of items in section */
  count: number;
  /** Source type for styling */
  sourceType: SourceType;
}

/**
 * Section header for evidence groups.
 */
export function EvidenceSectionHeader({
  title,
  count,
  sourceType,
}: EvidenceSectionHeaderProps) {
  const isGlobal = sourceType === 'global_legal';

  return (
    <div
      className={`evidence-section-header ${isGlobal ? 'evidence-section-header-global' : 'evidence-section-header-workspace'}`}
    >
      <span className="evidence-section-icon">{isGlobal ? '⚖️' : '📄'}</span>
      <span className="evidence-section-title">{title}</span>
      <span className="evidence-section-count">({count})</span>
    </div>
  );
}

// =============================================================================
// Policy Tooltip (Why This Was Used)
// =============================================================================

export interface PolicyTooltipProps {
  /** Jurisdiction that allowed this source */
  jurisdiction?: string;
  /** Show only when this is a global source */
  isGlobalSource: boolean;
}

/**
 * Localised policy tooltip for global law evidence (use inside Client Components).
 */
export function usePolicyTooltipText() {
  const t = useTranslations('evidence');
  return useCallback(
    (jurisdiction?: string) =>
      jurisdiction
        ? t('policyTooltipJurisdiction', { jurisdiction })
        : t('policyTooltipDefault'),
    [t]
  );
}

// =============================================================================
// Grouped Evidence List
// =============================================================================

export interface GroupedEvidenceListProps {
  /** Array of unified evidence items */
  evidence: EvidenceItem[];
  /** Maximum items per section */
  maxItemsPerSection?: number;
  /** Show explanation banner for global law */
  showGlobalLawBanner?: boolean;
  /** Show "show more" button */
  showMore?: boolean;
  /** Empty state message */
  emptyMessage?: string;
}

/**
 * Evidence list that groups items by source type.
 * Workspace documents are shown first, then global law references.
 * Never mixes sources in the same visual list.
 */
export function GroupedEvidenceList({
  evidence,
  maxItemsPerSection = 5,
  showGlobalLawBanner = true,
  showMore = true,
  emptyMessage,
}: GroupedEvidenceListProps) {
  const t = useTranslations('evidence');
  const resolvedEmpty = emptyMessage ?? t('noEvidenceFound');
  const [expandedWorkspace, setExpandedWorkspace] = React.useState(false);
  const [expandedGlobal, setExpandedGlobal] = React.useState(false);

  if (evidence.length === 0) {
    return (
      <div className="text-sm text-muted text-center py-4">{resolvedEmpty}</div>
    );
  }

  const grouped = groupEvidenceBySource(evidence);
  const counts = countEvidenceBySource(evidence);

  const displayedWorkspace = expandedWorkspace
    ? grouped.workspace
    : grouped.workspace.slice(0, maxItemsPerSection);
  const hasMoreWorkspace = grouped.workspace.length > maxItemsPerSection;

  const displayedGlobal = expandedGlobal
    ? grouped.global
    : grouped.global.slice(0, maxItemsPerSection);
  const hasMoreGlobal = grouped.global.length > maxItemsPerSection;

  return (
    <div className="grouped-evidence-list">
      {/* Global Law Explanation Banner - shown when global evidence exists */}
      {showGlobalLawBanner && counts.global > 0 && (
        <GlobalLawExplanationBanner globalEvidenceCount={counts.global} />
      )}

      {/* Workspace Documents Section */}
      {grouped.workspace.length > 0 && (
        <div className="evidence-section evidence-section-workspace">
          <EvidenceSectionHeader
            title={t('evidenceFromDocuments')}
            count={grouped.workspace.length}
            sourceType="workspace_document"
          />
          <div className="evidence-section-items">
            {displayedWorkspace.map(item => (
              <EvidenceCard key={item.chunk_id} evidence={item} />
            ))}
          </div>
          {showMore && hasMoreWorkspace && !expandedWorkspace && (
            <button
              className="text-sm text-primary text-center mt-3 w-full hover:underline"
              onClick={() => setExpandedWorkspace(true)}
            >
              {t('moreWorkspaceEvidence', {
                count: grouped.workspace.length - maxItemsPerSection,
              })}
            </button>
          )}
        </div>
      )}

      {/* Global Law Section */}
      {grouped.global.length > 0 && (
        <div className="evidence-section evidence-section-global">
          <EvidenceSectionHeader
            title={t('evidenceFromGlobalReadOnly')}
            count={grouped.global.length}
            sourceType="global_legal"
          />
          <div className="evidence-section-items">
            {displayedGlobal.map(item => (
              <EvidenceCard
                key={item.chunk_id}
                evidence={item}
                showPolicyTooltip={true}
              />
            ))}
          </div>
          {showMore && hasMoreGlobal && !expandedGlobal && (
            <button
              className="text-sm text-primary text-center mt-3 w-full hover:underline"
              onClick={() => setExpandedGlobal(true)}
            >
              {t('moreGlobalLawEvidence', {
                count: grouped.global.length - maxItemsPerSection,
              })}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// EvidenceList Component (Legacy - for backward compatibility)
// =============================================================================

export interface EvidenceListProps {
  /** Array of unified evidence items */
  evidence: EvidenceItem[];
  /** Maximum number of items to show initially */
  maxInitialItems?: number;
  /** Show "show more" button */
  showMore?: boolean;
  /** Empty state message */
  emptyMessage?: string;
}

/**
 * Evidence list component for displaying multiple evidence items.
 * Uses unified EvidenceItem type.
 */
export function EvidenceList({
  evidence,
  maxInitialItems = 5,
  showMore = true,
  emptyMessage,
}: EvidenceListProps) {
  const t = useTranslations('evidence');
  const resolvedEmpty = emptyMessage ?? t('noEvidenceFound');
  const [expanded, setExpanded] = React.useState(false);

  if (evidence.length === 0) {
    return (
      <div className="text-sm text-muted text-center py-4">{resolvedEmpty}</div>
    );
  }

  const displayedEvidence = expanded
    ? evidence
    : evidence.slice(0, maxInitialItems);
  const hasMore = evidence.length > maxInitialItems;

  return (
    <div className="workflow-evidence">
      {displayedEvidence.map(item => (
        <EvidenceCard key={item.chunk_id} evidence={item} />
      ))}

      {showMore && hasMore && !expanded && (
        <button
          className="text-sm text-primary text-center mt-3 w-full hover:underline"
          onClick={() => setExpanded(true)}
        >
          {t('moreEvidenceChunks', {
            count: evidence.length - maxInitialItems,
          })}
        </button>
      )}
    </div>
  );
}
