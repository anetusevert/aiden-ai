'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  ContractReviewResponse,
  ContractReviewMode,
  ContractFocusArea,
  ContractFinding,
  ExportDocumentMetadata,
  EvidenceScope,
  EvidenceChunkRef,
  type SourceType,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { getPlaybookById, getPlaybooksByRegion } from '@/lib/contractPlaybooks';
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge';
import { AdvancedSettingsPanel } from '@/components/EvidenceScopeSelector';
import {
  EvidenceMetaPanel,
  GlobalLawExplanationBanner,
  renderCitationsWithDifferentiation,
  countEvidenceBySource,
  usePolicyTooltipText,
} from '@/components/EvidenceCard';
import { SourceTypeBadge } from '@/components/ui/Badge';
import type { EvidenceItem } from '@/lib/evidence';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { useTranslations } from 'next-intl';
import { WorkflowLaunchBanner } from '@/components/workflows/WorkflowLaunchBanner';

type OutputLanguage = 'en' | 'ar';

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#f59e0b',
  low: '#3b82f6',
  info: '#6b7280',
};

const SEVERITY_BG: Record<string, string> = {
  critical: 'rgba(220, 38, 38, 0.1)',
  high: 'rgba(234, 88, 12, 0.1)',
  medium: 'rgba(245, 158, 11, 0.1)',
  low: 'rgba(59, 130, 246, 0.1)',
  info: 'rgba(107, 114, 128, 0.1)',
};

export default function ContractReviewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const {
    isAuthenticated,
    isLoading: authLoading,
    canEdit,
    defaultOutputLanguage,
    workspaceContext,
  } = useAuth();

  const t = useTranslations('common');
  const tEvidence = useTranslations('evidence');
  const policyTooltip = usePolicyTooltipText();

  const FOCUS_AREAS = useMemo(
    () =>
      [
        { value: 'liability' as const, label: t('focusLiability') },
        { value: 'termination' as const, label: t('focusTermination') },
        { value: 'governing_law' as const, label: t('focusGoverningLaw') },
        { value: 'payment' as const, label: t('focusPayment') },
        { value: 'ip' as const, label: t('focusIp') },
        { value: 'confidentiality' as const, label: t('focusConfidentiality') },
      ] as const satisfies ReadonlyArray<{
        value: ContractFocusArea;
        label: string;
      }>,
    [t]
  );

  const REVIEW_MODES = useMemo(
    () =>
      [
        {
          value: 'quick' as const,
          label: t('quick'),
          description: t('quickDesc'),
        },
        {
          value: 'standard' as const,
          label: t('standard'),
          description: t('standardDesc'),
        },
        {
          value: 'deep' as const,
          label: t('deep'),
          description: t('deepDesc'),
        },
      ] as const satisfies ReadonlyArray<{
        value: ContractReviewMode;
        label: string;
        description: string;
      }>,
    [t]
  );

  // URL params
  const documentId = searchParams.get('documentId') || '';
  const versionId = searchParams.get('versionId') || '';
  const title = searchParams.get('title') || 'Contract';

  // Default workspace values (for reset)
  const workspaceDefaultFocusAreas: ContractFocusArea[] = [
    'liability',
    'termination',
    'governing_law',
  ];
  const workspaceDefaultReviewMode: ContractReviewMode = 'standard';

  // Playbook state
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string | null>(
    null
  );
  const [promptHint, setPromptHint] = useState<string | null>(null);

  // Form state - default output language from workspace context
  const [reviewMode, setReviewMode] = useState<ContractReviewMode>(
    workspaceDefaultReviewMode
  );
  const [focusAreas, setFocusAreas] = useState<ContractFocusArea[]>(
    workspaceDefaultFocusAreas
  );
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>(
    defaultOutputLanguage
  );
  const [evidenceScope, setEvidenceScope] =
    useState<EvidenceScope>('workspace');

  // Memoize the evidence scope change handler
  const handleEvidenceScopeChange = useCallback((scope: EvidenceScope) => {
    setEvidenceScope(scope);
  }, []);

  // Result state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ContractReviewResponse | null>(null);

  // Expanded evidence state
  const [expandedFindings, setExpandedFindings] = useState<Set<string>>(
    new Set()
  );

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Update output language when workspace context changes (e.g., after login)
  useEffect(() => {
    setOutputLanguage(defaultOutputLanguage);
  }, [defaultOutputLanguage]);

  const toggleFocusArea = (area: ContractFocusArea) => {
    setFocusAreas(prev =>
      prev.includes(area) ? prev.filter(a => a !== area) : [...prev, area]
    );
  };

  // Playbook selection handler
  const handlePlaybookChange = (playbookId: string) => {
    if (!playbookId) {
      // "None" selected - reset to workspace defaults
      handleResetToDefaults();
      return;
    }

    const playbook = getPlaybookById(playbookId);
    if (!playbook) return;

    setSelectedPlaybookId(playbookId);
    setReviewMode(playbook.default_review_mode);
    setFocusAreas([...playbook.default_focus_areas]);
    setOutputLanguage(playbook.recommended_output_language);
    setPromptHint(playbook.prompt_hint || null);
  };

  // Reset to workspace defaults
  const handleResetToDefaults = () => {
    setSelectedPlaybookId(null);
    setReviewMode(workspaceDefaultReviewMode);
    setFocusAreas([...workspaceDefaultFocusAreas]);
    setOutputLanguage(defaultOutputLanguage);
    setPromptHint(null);
  };

  const toggleEvidence = (findingId: string) => {
    setExpandedFindings(prev => {
      const next = new Set(prev);
      if (next.has(findingId)) {
        next.delete(findingId);
      } else {
        next.add(findingId);
      }
      return next;
    });
  };

  const handleRunReview = async () => {
    if (!documentId || !versionId) {
      setError('Missing document or version ID');
      return;
    }

    if (!canEdit) {
      setError('Insufficient permissions. EDITOR or ADMIN role required.');
      return;
    }

    if (focusAreas.length === 0) {
      setError('Please select at least one focus area');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.contractReview({
        document_id: documentId,
        version_id: versionId,
        review_mode: reviewMode,
        focus_areas: focusAreas,
        output_language: outputLanguage,
        evidence_scope: evidenceScope,
        // Include playbook_hint if a playbook is selected
        ...(promptHint && { playbook_hint: promptHint }),
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Contract review failed');
    } finally {
      setLoading(false);
    }
  };

  // Handle DOCX export
  const handleExportDocx = async () => {
    if (!result) return;

    setExporting(true);
    setExportError(null);

    try {
      const metadata: ExportDocumentMetadata = {
        document_id: documentId,
        version_id: versionId,
        document_title: title,
        version_number: 1, // Default to 1
        workspace_name: workspaceContext?.name || 'Workspace',
        tenant_name: 'Organization', // Could be enhanced to get from context
        jurisdiction:
          workspaceContext?.jurisdiction_profile?.replace('_DEFAULT', '') ||
          'UAE',
      };

      const blob = await apiClient.exportContractReviewDocx(metadata, result);

      // Generate filename: <title>_contract-review_<date>.docx
      const safeTitle = title.replace(/[^a-zA-Z0-9 \-_]/g, '_').slice(0, 50);
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `${safeTitle}_contract-review_${dateStr}.docx`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  // Check if export is allowed (success or insufficient_sources)
  const canExport =
    result &&
    (result.meta.status === 'success' ||
      result.meta.status === 'insufficient_sources');

  // Render text with styled citations, differentiating [1] from [GL-1]
  const renderWithCitations = (text: string) => {
    return renderCitationsWithDifferentiation(text, {
      globalCitationTitle: tEvidence('globalLawRefTitle'),
    });
  };

  // Convert EvidenceChunkRef to minimal EvidenceItem for counting
  const convertEvidenceForCounting = (
    evidenceRefs: EvidenceChunkRef[]
  ): Partial<EvidenceItem>[] => {
    return evidenceRefs.map(ev => ({
      chunk_id: ev.chunk_id,
      source_type: ev.source_type || 'workspace_document',
    })) as Partial<EvidenceItem>[];
  };

  // Count all evidence in all findings
  const getAllFindingsEvidence = (): EvidenceItem[] => {
    if (!result) return [];
    const allEvidence: EvidenceItem[] = [];
    for (const finding of result.findings) {
      for (const ev of finding.evidence) {
        const evAny = ev as unknown as Record<string, unknown>;
        allEvidence.push({
          chunk_id: ev.chunk_id,
          chunk_index: 0,
          snippet: ev.snippet,
          source_type: (evAny.source_type as string) || 'workspace_document',
          source_label: (evAny.source_label as string) || '',
          char_start: ev.char_start,
          char_end: ev.char_end,
        } as EvidenceItem);
      }
    }
    return allEvidence;
  };

  const renderFindingCard = (finding: ContractFinding) => {
    const isExpanded = expandedFindings.has(finding.finding_id);

    return (
      <div
        key={finding.finding_id}
        style={{
          border: '1px solid var(--border)',
          borderRadius: '8px',
          overflow: 'hidden',
          marginBottom: '1rem',
        }}
      >
        {/* Header with severity */}
        <div
          style={{
            padding: '1rem',
            background: SEVERITY_BG[finding.severity] || SEVERITY_BG.info,
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: 'white',
                  background:
                    SEVERITY_COLORS[finding.severity] || SEVERITY_COLORS.info,
                }}
              >
                {finding.severity}
              </span>
              <span className="badge badge-muted">{finding.category}</span>
            </div>
            {finding.citations.length > 0 && (
              <span className="text-sm text-muted">
                {finding.citations.length} citation
                {finding.citations.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <h4 style={{ margin: '0.5rem 0 0', fontWeight: 600 }}>
            {finding.title}
          </h4>
        </div>

        {/* Body */}
        <div style={{ padding: '1rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <p
              className="text-sm text-muted"
              style={{ marginBottom: '0.25rem' }}
            >
              Issue
            </p>
            <p style={{ lineHeight: 1.6 }}>
              {renderWithCitations(finding.issue)}
            </p>
          </div>

          <div>
            <p
              className="text-sm text-muted"
              style={{ marginBottom: '0.25rem' }}
            >
              Recommendation
            </p>
            <p style={{ lineHeight: 1.6 }}>
              {renderWithCitations(finding.recommendation)}
            </p>
          </div>
        </div>

        {/* Evidence section */}
        {finding.evidence.length > 0 && (
          <div
            style={{
              borderTop: '1px solid var(--border)',
              background: 'rgba(0,0,0,0.02)',
            }}
          >
            <button
              onClick={() => toggleEvidence(finding.finding_id)}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '0.875rem',
                color: 'var(--muted)',
              }}
            >
              <span>
                Evidence ({finding.evidence.length} snippet
                {finding.evidence.length !== 1 ? 's' : ''})
              </span>
              <span
                style={{
                  transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s',
                }}
              >
                ▼
              </span>
            </button>

            {isExpanded && (
              <div style={{ padding: '0 1rem 1rem' }}>
                {finding.evidence.map((ev, idx) => {
                  const evExt = ev as unknown as Record<string, unknown>;
                  const isGlobalLegal = evExt.source_type === 'global_legal';
                  const borderColor = isGlobalLegal
                    ? 'rgba(30, 64, 175, 0.6)'
                    : 'var(--primary)';
                  const bgColor = isGlobalLegal
                    ? 'linear-gradient(135deg, rgba(30, 64, 175, 0.03) 0%, rgba(59, 130, 246, 0.05) 100%)'
                    : 'white';

                  return (
                    <blockquote
                      key={ev.chunk_id || idx}
                      style={{
                        margin: idx > 0 ? '0.75rem 0 0' : 0,
                        padding: '0.75rem',
                        background: bgColor,
                        borderLeft: `3px solid ${borderColor}`,
                        fontSize: '0.9rem',
                        lineHeight: 1.6,
                        borderRadius: '0 4px 4px 0',
                      }}
                    >
                      {/* Source type badge for clarity */}
                      <div style={{ marginBottom: '0.5rem' }}>
                        <SourceTypeBadge
                          sourceType={
                            ((evExt.source_type as string) ||
                              'workspace_document') as SourceType
                          }
                          jurisdiction={evExt.jurisdiction as string}
                          size="sm"
                        />
                      </div>

                      {ev.snippet}

                      <div
                        className="flex items-center justify-between"
                        style={{ marginTop: '0.5rem' }}
                      >
                        <div className="text-sm text-muted">
                          {tEvidence('charsRange', {
                            start: ev.char_start,
                            end: ev.char_end,
                          })}
                        </div>

                        {/* View action based on source type */}
                        {isGlobalLegal ? (
                          evExt.official_source_url ? (
                            <a
                              href={evExt.official_source_url as string}
                              className="view-in-doc-link external-source-link"
                              target="_blank"
                              rel="noopener noreferrer"
                              title={tEvidence('opensOfficial')}
                            >
                              {tEvidence('viewSource')}
                            </a>
                          ) : (
                            <span
                              className="text-xs text-muted italic"
                              title={policyTooltip(
                                evExt.jurisdiction as string | undefined
                              )}
                            >
                              {tEvidence('globalLawRefTitle')}
                            </span>
                          )
                        ) : (
                          ev.chunk_id && (
                            <Link
                              href={`/documents/${documentId}/versions/${versionId}/viewer?chunkId=${ev.chunk_id}`}
                              className="view-in-doc-link"
                            >
                              {tEvidence('viewInDocument')}
                            </Link>
                          )
                        )}
                      </div>
                    </blockquote>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (authLoading) {
    return <div className="loading">{t('loading')}</div>;
  }

  // Check for missing params
  if (!documentId || !versionId) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">{t('contractReviewTitle')}</h1>
          <p className="page-subtitle">{t('contractReviewSubtitle')}</p>
        </div>
        <div className="alert alert-error">
          {t('missingParamsSelect')}{' '}
          <Link href="/documents" style={{ fontWeight: 500 }}>
            {t('documentsPage')}
          </Link>{' '}
          {t('pageLink')}
        </div>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      <WorkflowLaunchBanner currentRoute="/contract-review" />

      <div className="mb-4">
        <Link
          href={`/documents/${documentId}`}
          style={{ color: 'var(--muted)', fontSize: '0.875rem' }}
        >
          {t('backToDocument')}
        </Link>
      </div>

      <div className="page-header">
        <h1 className="page-title">{t('contractReviewTitle')}</h1>
        <p className="page-subtitle">
          {t('reviewing')} {title}
        </p>
      </div>

      <div
        className="grid"
        style={{ gridTemplateColumns: '300px 1fr', gap: '1.5rem' }}
      >
        {/* Controls Panel */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div className="card-header">
            <h3 className="card-title">{t('reviewSettings')}</h3>
          </div>

          {/* Playbook Selector */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="playbook" className="form-label">
              {t('playbook')}
            </label>
            <select
              id="playbook"
              className="form-select"
              value={selectedPlaybookId || ''}
              onChange={e => handlePlaybookChange(e.target.value)}
            >
              <option value="">{t('noneManual')}</option>
              {(() => {
                const grouped = getPlaybooksByRegion();
                return (
                  <>
                    <optgroup label={t('optgroupUae')}>
                      {grouped.UAE.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </optgroup>
                    <optgroup label={t('optgroupKsa')}>
                      {grouped.KSA.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </optgroup>
                  </>
                );
              })()}
            </select>
            {selectedPlaybookId && (
              <button
                type="button"
                onClick={handleResetToDefaults}
                style={{
                  marginTop: '0.5rem',
                  padding: '0.25rem 0.5rem',
                  fontSize: '0.75rem',
                  background: 'transparent',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  color: 'var(--muted)',
                }}
              >
                {t('resetWorkspaceDefaults')}
              </button>
            )}
          </div>

          {/* Prompt Hint (read-only) */}
          {promptHint && (
            <div
              style={{
                marginBottom: '1rem',
                padding: '0.75rem',
                background: 'rgba(59, 130, 246, 0.05)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                borderRadius: '6px',
                fontSize: '0.875rem',
              }}
            >
              <div
                style={{
                  fontWeight: 500,
                  color: '#1e40af',
                  marginBottom: '0.25rem',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                {t('playbookHint')}
              </div>
              <div style={{ color: '#334155', lineHeight: 1.5 }}>
                {promptHint}
              </div>
            </div>
          )}

          {/* Document Info */}
          <div
            style={{
              marginBottom: '1rem',
              padding: '0.75rem',
              background: 'rgba(0,0,0,0.02)',
              borderRadius: '6px',
              fontSize: '0.875rem',
            }}
          >
            <div className="text-muted">{t('documentId')}</div>
            <code style={{ fontSize: '0.75rem' }}>
              {documentId.slice(0, 8)}...
            </code>
            <div className="text-muted" style={{ marginTop: '0.5rem' }}>
              {t('versionId')}
            </div>
            <code style={{ fontSize: '0.75rem' }}>
              {versionId.slice(0, 8)}...
            </code>
          </div>

          {/* Review Mode */}
          <div className="form-group">
            <label className="form-label">{t('reviewMode')}</label>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              {REVIEW_MODES.map(mode => (
                <label
                  key={mode.value}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.5rem',
                    padding: '0.5rem',
                    border: '1px solid var(--border)',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    background:
                      reviewMode === mode.value
                        ? 'rgba(59, 130, 246, 0.05)'
                        : 'transparent',
                    borderColor:
                      reviewMode === mode.value
                        ? 'var(--primary)'
                        : 'var(--border)',
                  }}
                >
                  <input
                    type="radio"
                    name="reviewMode"
                    value={mode.value}
                    checked={reviewMode === mode.value}
                    onChange={() => setReviewMode(mode.value)}
                    style={{ marginTop: '0.2rem' }}
                  />
                  <div>
                    <div style={{ fontWeight: 500 }}>{mode.label}</div>
                    <div className="text-sm text-muted">{mode.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Focus Areas */}
          <div className="form-group">
            <label className="form-label">{t('focusAreas')}</label>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              {FOCUS_AREAS.map(area => (
                <label
                  key={area.value}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={focusAreas.includes(area.value)}
                    onChange={() => toggleFocusArea(area.value)}
                  />
                  <span>{area.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Output Language */}
          <div className="form-group">
            <label htmlFor="outputLang" className="form-label">
              {t('outputLanguage')}
            </label>
            <select
              id="outputLang"
              className="form-select"
              value={outputLanguage}
              onChange={e =>
                setOutputLanguage(e.target.value as OutputLanguage)
              }
            >
              <option value="en">{t('english')}</option>
              <option value="ar">{t('arabicOption')}</option>
            </select>
            {workspaceContext && (
              <small
                className="text-muted text-sm"
                style={{ marginTop: '0.25rem', display: 'block' }}
              >
                {t('workspaceDefault')}{' '}
                {defaultOutputLanguage === 'ar' ? t('arabic') : t('english')}
              </small>
            )}
          </div>

          {/* Role Warning */}
          {!canEdit && (
            <div
              className="alert alert-warning"
              style={{ marginBottom: '1rem' }}
            >
              {t('viewerCannotReview')}
            </div>
          )}

          {/* Advanced Settings (Evidence Scope) */}
          {workspaceContext?.id && (
            <AdvancedSettingsPanel
              workspaceId={workspaceContext.id}
              evidenceScope={evidenceScope}
              onEvidenceScopeChange={handleEvidenceScopeChange}
            />
          )}

          {/* Run Button */}
          <button
            onClick={handleRunReview}
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={loading || !canEdit || focusAreas.length === 0}
          >
            {loading ? 'Running Review...' : 'Run Review'}
          </button>
        </div>

        {/* Results Panel */}
        <div>
          {error && <div className="alert alert-error">{error}</div>}

          {loading && (
            <div className="card">
              <div className="loading">
                Analyzing contract... This may take a moment.
              </div>
            </div>
          )}

          {result && (
            <>
              {/* Status Badge and Export Button */}
              <div
                className="flex items-center justify-between"
                style={{ marginBottom: '1rem' }}
              >
                <WorkflowStatusBadge
                  status={result.meta.status}
                  showDescription
                />

                <button
                  onClick={handleExportDocx}
                  className="btn"
                  disabled={!canExport || exporting}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 1rem',
                    background: canExport ? 'var(--primary)' : 'var(--muted)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: canExport && !exporting ? 'pointer' : 'not-allowed',
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    opacity: canExport ? 1 : 0.6,
                  }}
                  title={
                    !canExport
                      ? t('exportUnavailableTitle')
                      : t('downloadAsDocxTitle')
                  }
                >
                  {exporting ? (
                    <>
                      <span
                        className="spinner"
                        style={{
                          width: '14px',
                          height: '14px',
                          border: '2px solid rgba(255,255,255,0.3)',
                          borderTopColor: 'white',
                          borderRadius: '50%',
                          animation: 'spin 1s linear infinite',
                        }}
                      />
                      {t('exporting')}
                    </>
                  ) : (
                    <>
                      <span style={{ fontSize: '1rem' }}>&#x2193;</span>
                      {t('downloadDocx')}
                    </>
                  )}
                </button>
              </div>

              {exportError && (
                <div
                  className="alert alert-error"
                  style={{ marginBottom: '1rem' }}
                >
                  {t('exportFailedPrefix')} {exportError}
                </div>
              )}

              {/* Summary */}
              <div className="card mb-4">
                <div className="card-header">
                  <h3 className="card-title">{t('summary')}</h3>
                </div>

                {/* Insufficient Sources Info Banner */}
                {result.meta.strict_citations_failed && (
                  <div
                    style={{
                      padding: '1rem',
                      marginBottom: '1rem',
                      background: 'rgba(59, 130, 246, 0.05)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      borderRadius: '6px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '0.75rem',
                      }}
                    >
                      <span
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          width: '24px',
                          height: '24px',
                          borderRadius: '50%',
                          background: 'rgba(59, 130, 246, 0.1)',
                          color: '#3b82f6',
                          fontSize: '0.875rem',
                          flexShrink: 0,
                        }}
                      >
                        i
                      </span>
                      <div>
                        <div
                          style={{
                            fontWeight: 500,
                            marginBottom: '0.25rem',
                            color: '#1e40af',
                          }}
                        >
                          Not enough indexed sources for a fully cited review
                        </div>
                        <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                          {result.meta.removed_findings_count} finding
                          {result.meta.removed_findings_count !== 1
                            ? 's'
                            : ''}{' '}
                          removed due to insufficient citations.
                        </div>
                        <div
                          style={{
                            fontSize: '0.875rem',
                            color: '#64748b',
                            marginTop: '0.5rem',
                          }}
                        >
                          To improve results, try uploading more relevant
                          documents or reindexing the document.
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                  {renderWithCitations(result.summary)}
                </div>

                {/* Meta info */}
                <div
                  className="flex flex-wrap gap-2 mt-4"
                  style={{
                    paddingTop: '1rem',
                    borderTop: '1px solid var(--border)',
                  }}
                >
                  <span className="badge badge-muted">
                    Mode: {result.meta.review_mode}
                  </span>
                  <span className="badge badge-muted">
                    Model: {result.meta.model}
                  </span>
                  <span className="badge badge-muted">
                    Provider: {result.meta.provider}
                  </span>
                  <span className="badge badge-muted">
                    Findings: {result.findings.length}
                  </span>
                  {result.meta.removed_findings_count > 0 && (
                    <span className="badge badge-warning">
                      Removed: {result.meta.removed_findings_count}
                    </span>
                  )}
                </div>
              </div>

              {/* Evidence Meta Panel - shows evidence counts by source */}
              <EvidenceMetaPanel
                workspaceCount={result.meta.workspace_evidence_count}
                globalCount={result.meta.global_evidence_count}
                evidenceScope={result.meta.evidence_scope}
                className="mb-4"
              />

              {/* Global Law Explanation Banner - shown when global evidence is used */}
              {result.meta.global_evidence_count > 0 && (
                <GlobalLawExplanationBanner
                  globalEvidenceCount={result.meta.global_evidence_count}
                  className="mb-4"
                />
              )}

              {/* Findings */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    Findings ({result.findings.length})
                  </h3>
                </div>

                {result.findings.length === 0 ? (
                  <p
                    className="text-muted"
                    style={{ textAlign: 'center', padding: '2rem 0' }}
                  >
                    No findings identified in this review.
                  </p>
                ) : (
                  <div>
                    {/* Severity summary */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {['critical', 'high', 'medium', 'low', 'info'].map(
                        severity => {
                          const count = result.findings.filter(
                            f => f.severity === severity
                          ).length;
                          if (count === 0) return null;
                          return (
                            <span
                              key={severity}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.25rem 0.75rem',
                                borderRadius: '4px',
                                fontSize: '0.875rem',
                                background: SEVERITY_BG[severity],
                                color: SEVERITY_COLORS[severity],
                                fontWeight: 500,
                              }}
                            >
                              {count} {severity}
                            </span>
                          );
                        }
                      )}
                    </div>

                    {/* Finding cards */}
                    {result.findings.map(finding => renderFindingCard(finding))}
                  </div>
                )}
              </div>
            </>
          )}

          {!result && !loading && !error && (
            <div className="card">
              <p
                className="text-muted"
                style={{ textAlign: 'center', padding: '3rem 0' }}
              >
                Configure your review settings and click &ldquo;Run
                Review&rdquo; to analyze the contract for potential issues and
                risks.
              </p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
