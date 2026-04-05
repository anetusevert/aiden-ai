'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  ClauseRedlinesResponse,
  ClauseRedlineItem,
  ClauseType,
  ClauseJurisdiction,
  ExportDocumentMetadata,
  EvidenceScope,
  EvidenceChunkRef,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { getPlaybookById, getPlaybooksByRegion } from '@/lib/contractPlaybooks';
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge';
import { AdvancedSettingsPanel } from '@/components/EvidenceScopeSelector';
import {
  EvidenceMetaPanel,
  GlobalLawExplanationBanner,
  renderCitationsWithDifferentiation,
  usePolicyTooltipText,
} from '@/components/EvidenceCard';
import { SourceTypeBadge } from '@/components/ui/Badge';
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
};

const SEVERITY_BG: Record<string, string> = {
  critical: 'rgba(220, 38, 38, 0.1)',
  high: 'rgba(234, 88, 12, 0.1)',
  medium: 'rgba(245, 158, 11, 0.1)',
  low: 'rgba(59, 130, 246, 0.1)',
};

const STATUS_COLORS: Record<string, string> = {
  found: '#22c55e',
  missing: '#ef4444',
  insufficient_evidence: '#f59e0b',
};

const STATUS_BG: Record<string, string> = {
  found: 'rgba(34, 197, 94, 0.1)',
  missing: 'rgba(239, 68, 68, 0.1)',
  insufficient_evidence: 'rgba(245, 158, 11, 0.1)',
};

export default function ClauseRedlinesPage() {
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

  const CLAUSE_TYPES = useMemo(
    () =>
      [
        { value: 'governing_law' as const, label: t('clauseGoverningLaw') },
        { value: 'termination' as const, label: t('clauseTermination') },
        { value: 'liability' as const, label: t('clauseLiability') },
        { value: 'indemnity' as const, label: t('clauseIndemnity') },
        {
          value: 'confidentiality' as const,
          label: t('clauseConfidentiality'),
        },
        { value: 'payment' as const, label: t('clausePayment') },
        { value: 'ip' as const, label: t('clauseIp') },
        { value: 'force_majeure' as const, label: t('clauseForceMajeure') },
      ] as const satisfies ReadonlyArray<{ value: ClauseType; label: string }>,
    [t]
  );

  const JURISDICTIONS = useMemo(
    () =>
      [
        { value: 'UAE' as const, label: t('uae') },
        { value: 'DIFC' as const, label: t('difc') },
        { value: 'ADGM' as const, label: t('adgm') },
        { value: 'KSA' as const, label: t('ksa') },
      ] as const satisfies ReadonlyArray<{
        value: ClauseJurisdiction;
        label: string;
      }>,
    [t]
  );

  // URL params
  const documentId = searchParams.get('documentId') || '';
  const versionId = searchParams.get('versionId') || '';
  const title = searchParams.get('title') || 'Contract';

  // Determine default jurisdiction from workspace context
  const getDefaultJurisdiction = (): ClauseJurisdiction => {
    if (workspaceContext?.jurisdiction_profile) {
      const profile = workspaceContext.jurisdiction_profile;
      if (profile === 'KSA_DEFAULT') return 'KSA';
      if (profile === 'DIFC_DEFAULT') return 'DIFC';
      if (profile === 'ADGM_DEFAULT') return 'ADGM';
    }
    return 'UAE';
  };

  // Default clause types
  const defaultClauseTypes: ClauseType[] = [
    'governing_law',
    'termination',
    'liability',
    'indemnity',
    'confidentiality',
  ];

  // Playbook state
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string | null>(
    null
  );
  const [promptHint, setPromptHint] = useState<string | null>(null);

  // Form state
  const [jurisdiction, setJurisdiction] = useState<ClauseJurisdiction>(
    getDefaultJurisdiction()
  );
  const [clauseTypes, setClauseTypes] =
    useState<ClauseType[]>(defaultClauseTypes);
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
  const [result, setResult] = useState<ClauseRedlinesResponse | null>(null);

  // Expanded evidence state
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // Export state
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Update output language and jurisdiction when workspace context changes
  useEffect(() => {
    setOutputLanguage(defaultOutputLanguage);
    setJurisdiction(getDefaultJurisdiction());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultOutputLanguage, workspaceContext]);

  const toggleClauseType = (clauseType: ClauseType) => {
    setClauseTypes(prev =>
      prev.includes(clauseType)
        ? prev.filter(c => c !== clauseType)
        : [...prev, clauseType]
    );
  };

  // Playbook selection handler
  const handlePlaybookChange = (playbookId: string) => {
    if (!playbookId) {
      handleResetToDefaults();
      return;
    }

    const playbook = getPlaybookById(playbookId);
    if (!playbook) return;

    setSelectedPlaybookId(playbookId);
    setOutputLanguage(playbook.recommended_output_language);
    setPromptHint(playbook.prompt_hint || null);

    // Map playbook focus areas to clause types where applicable
    const clauseTypeMap: Record<string, ClauseType> = {
      liability: 'liability',
      termination: 'termination',
      governing_law: 'governing_law',
      payment: 'payment',
      ip: 'ip',
      confidentiality: 'confidentiality',
    };

    const mappedClauseTypes: ClauseType[] = playbook.default_focus_areas
      .map(fa => clauseTypeMap[fa])
      .filter((ct): ct is ClauseType => ct !== undefined);

    // Add indemnity and force_majeure if liability is included
    if (mappedClauseTypes.includes('liability')) {
      if (!mappedClauseTypes.includes('indemnity')) {
        mappedClauseTypes.push('indemnity');
      }
    }

    if (mappedClauseTypes.length > 0) {
      setClauseTypes(mappedClauseTypes);
    }

    // Set jurisdiction based on playbook region
    if (playbook.region === 'KSA') {
      setJurisdiction('KSA');
    } else {
      setJurisdiction(getDefaultJurisdiction());
    }
  };

  // Reset to workspace defaults
  const handleResetToDefaults = () => {
    setSelectedPlaybookId(null);
    setClauseTypes([...defaultClauseTypes]);
    setOutputLanguage(defaultOutputLanguage);
    setJurisdiction(getDefaultJurisdiction());
    setPromptHint(null);
  };

  const toggleEvidence = (itemKey: string) => {
    setExpandedItems(prev => {
      const next = new Set(prev);
      if (next.has(itemKey)) {
        next.delete(itemKey);
      } else {
        next.add(itemKey);
      }
      return next;
    });
  };

  const handleRunAnalysis = async () => {
    if (!documentId || !versionId) {
      setError('Missing document or version ID');
      return;
    }

    if (!canEdit) {
      setError('Insufficient permissions. EDITOR or ADMIN role required.');
      return;
    }

    if (clauseTypes.length === 0) {
      setError('Please select at least one clause type');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.clauseRedlines({
        document_id: documentId,
        version_id: versionId,
        jurisdiction,
        clause_types: clauseTypes,
        output_language: outputLanguage,
        evidence_scope: evidenceScope,
        ...(promptHint && { playbook_hint: promptHint }),
      });
      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Clause redlines analysis failed'
      );
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
        jurisdiction: jurisdiction,
      };

      const blob = await apiClient.exportClauseRedlinesDocx(metadata, result);

      // Generate filename: <title>_clause-redlines_<date>.docx
      const safeTitle = title.replace(/[^a-zA-Z0-9 \-_]/g, '_').slice(0, 50);
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `${safeTitle}_clause-redlines_${dateStr}.docx`;

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
    return renderCitationsWithDifferentiation(text);
  };

  // Count citations in text
  const countCitations = (text: string | null): number => {
    if (!text) return 0;
    const matches = text.match(/\[\d+\]/g);
    return matches ? matches.length : 0;
  };

  const renderClauseCard = (item: ClauseRedlineItem, index: number) => {
    const itemKey = `${item.clause_type}-${index}`;
    const isExpanded = expandedItems.has(itemKey);
    const clauseLabel =
      CLAUSE_TYPES.find(ct => ct.value === item.clause_type)?.label ||
      item.clause_type;

    return (
      <div
        key={itemKey}
        style={{
          border: '1px solid var(--border)',
          borderRadius: '8px',
          overflow: 'hidden',
          marginBottom: '1rem',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '1rem',
            background: STATUS_BG[item.status] || STATUS_BG.found,
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
                  background: STATUS_COLORS[item.status] || STATUS_COLORS.found,
                }}
              >
                {item.status.replace('_', ' ')}
              </span>
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
                    SEVERITY_COLORS[item.severity] || SEVERITY_COLORS.medium,
                }}
              >
                {item.severity}
              </span>
              <span className="badge badge-muted">
                {Math.round(item.confidence * 100)}% confidence
              </span>
            </div>
            {item.citations.length > 0 && (
              <span className="text-sm text-muted">
                {item.citations.length} citation
                {item.citations.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <h4 style={{ margin: '0.5rem 0 0', fontWeight: 600 }}>
            {clauseLabel}
          </h4>
        </div>

        {/* Body */}
        <div style={{ padding: '1rem' }}>
          {item.issue && (
            <div style={{ marginBottom: '1rem' }}>
              <p
                className="text-sm text-muted"
                style={{ marginBottom: '0.25rem' }}
              >
                Issue
              </p>
              <p style={{ lineHeight: 1.6 }}>
                {renderWithCitations(item.issue)}
              </p>
            </div>
          )}

          {item.rationale && (
            <div style={{ marginBottom: '1rem' }}>
              <p
                className="text-sm text-muted"
                style={{ marginBottom: '0.25rem' }}
              >
                Rationale
              </p>
              <p style={{ lineHeight: 1.6 }}>
                {renderWithCitations(item.rationale)}
              </p>
            </div>
          )}

          {item.suggested_redline && (
            <div
              style={{
                padding: '0.75rem',
                background: 'rgba(59, 130, 246, 0.05)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                borderRadius: '6px',
              }}
            >
              <div
                style={{
                  fontWeight: 500,
                  color: '#1e40af',
                  marginBottom: '0.5rem',
                  fontSize: '0.75rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Recommended Text
              </div>
              <div
                style={{
                  color: '#334155',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {item.suggested_redline}
              </div>
            </div>
          )}
        </div>

        {/* Evidence section */}
        {item.evidence.length > 0 && (
          <div
            style={{
              borderTop: '1px solid var(--border)',
              background: 'rgba(0,0,0,0.02)',
            }}
          >
            <button
              onClick={() => toggleEvidence(itemKey)}
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
                Evidence ({item.evidence.length} snippet
                {item.evidence.length !== 1 ? 's' : ''})
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
                {item.evidence.map((ev, idx) => {
                  const isGlobalLegal = ev.source_type === 'global_legal';
                  const borderColor = isGlobalLegal
                    ? 'rgba(30, 64, 175, 0.6)'
                    : 'var(--primary)';
                  const bgColor = isGlobalLegal
                    ? 'linear-gradient(135deg, rgba(30, 64, 175, 0.03) 0%, rgba(59, 130, 246, 0.05) 100%)'
                    : 'white';

                  // Citation marker - use GL prefix for global law
                  const citationMarker = isGlobalLegal
                    ? `GL-${idx + 1}`
                    : `${idx + 1}`;
                  const citationClass = isGlobalLegal
                    ? 'citation-ref-global'
                    : 'citation-ref';

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
                          sourceType={ev.source_type || 'workspace_document'}
                          jurisdiction={ev.jurisdiction}
                          size="sm"
                        />
                      </div>

                      {ev.snippet}

                      <div
                        className="flex items-center justify-between"
                        style={{ marginTop: '0.5rem' }}
                      >
                        <div className="text-sm text-muted">
                          <span className={citationClass}>
                            {citationMarker}
                          </span>{' '}
                          Chars {ev.char_start}-{ev.char_end}
                        </div>

                        {/* View action based on source type */}
                        {isGlobalLegal ? (
                          ev.official_source_url ? (
                            <a
                              href={ev.official_source_url}
                              className="view-in-doc-link external-source-link"
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Opens official government source in a new tab"
                            >
                              View Source ↗
                            </a>
                          ) : (
                            <span
                              className="text-xs text-muted italic"
                              title={policyTooltip(ev.jurisdiction)}
                            >
                              Global law reference
                            </span>
                          )
                        ) : (
                          ev.chunk_id && (
                            <Link
                              href={`/documents/${documentId}/versions/${versionId}/viewer?chunkId=${ev.chunk_id}`}
                              className="view-in-doc-link"
                            >
                              View in Document
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
    return <div className="loading">Loading...</div>;
  }

  // Check for missing params
  if (!documentId || !versionId) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Clause Redlines</h1>
          <p className="page-subtitle">
            Analyze contract clauses and get suggested redlines
          </p>
        </div>
        <div className="alert alert-error">
          Missing required parameters. Please select a document version from the{' '}
          <Link href="/documents" style={{ fontWeight: 500 }}>
            Documents
          </Link>{' '}
          page.
        </div>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      <WorkflowLaunchBanner currentRoute="/clause-redlines" />

      <div className="mb-4">
        <Link
          href={`/documents/${documentId}`}
          style={{ color: 'var(--muted)', fontSize: '0.875rem' }}
        >
          &larr; Back to Document
        </Link>
      </div>

      <div className="page-header">
        <h1 className="page-title">Clause Redlines</h1>
        <p className="page-subtitle">Analyzing: {title}</p>
      </div>

      <div
        className="grid"
        style={{ gridTemplateColumns: '320px 1fr', gap: '1.5rem' }}
      >
        {/* Controls Panel */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div className="card-header">
            <h3 className="card-title">Analysis Settings</h3>
          </div>

          {/* Playbook Selector */}
          <div className="form-group" style={{ marginBottom: '1rem' }}>
            <label htmlFor="playbook" className="form-label">
              Playbook (Optional)
            </label>
            <select
              id="playbook"
              className="form-select"
              value={selectedPlaybookId || ''}
              onChange={e => handlePlaybookChange(e.target.value)}
            >
              <option value="">None (manual configuration)</option>
              {(() => {
                const grouped = getPlaybooksByRegion();
                return (
                  <>
                    <optgroup label="UAE">
                      {grouped.UAE.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </optgroup>
                    <optgroup label="KSA">
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
                Reset to workspace defaults
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
                Playbook Hint
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
            <div className="text-muted">Document ID</div>
            <code style={{ fontSize: '0.75rem' }}>
              {documentId.slice(0, 8)}...
            </code>
            <div className="text-muted" style={{ marginTop: '0.5rem' }}>
              Version ID
            </div>
            <code style={{ fontSize: '0.75rem' }}>
              {versionId.slice(0, 8)}...
            </code>
          </div>

          {/* Jurisdiction */}
          <div className="form-group">
            <label htmlFor="jurisdiction" className="form-label">
              Jurisdiction
            </label>
            <select
              id="jurisdiction"
              className="form-select"
              value={jurisdiction}
              onChange={e =>
                setJurisdiction(e.target.value as ClauseJurisdiction)
              }
            >
              {JURISDICTIONS.map(j => (
                <option key={j.value} value={j.value}>
                  {j.label}
                </option>
              ))}
            </select>
          </div>

          {/* Clause Types */}
          <div className="form-group">
            <label className="form-label">Clause Types</label>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              {CLAUSE_TYPES.map(ct => (
                <label
                  key={ct.value}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={clauseTypes.includes(ct.value)}
                    onChange={() => toggleClauseType(ct.value)}
                  />
                  <span>{ct.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Output Language */}
          <div className="form-group">
            <label htmlFor="outputLang" className="form-label">
              Output Language
            </label>
            <select
              id="outputLang"
              className="form-select"
              value={outputLanguage}
              onChange={e =>
                setOutputLanguage(e.target.value as OutputLanguage)
              }
            >
              <option value="en">English</option>
              <option value="ar">Arabic (عربي)</option>
            </select>
            {workspaceContext && (
              <small
                className="text-muted text-sm"
                style={{ marginTop: '0.25rem', display: 'block' }}
              >
                Workspace default:{' '}
                {defaultOutputLanguage === 'ar' ? 'Arabic' : 'English'}
              </small>
            )}
          </div>

          {/* Role Warning */}
          {!canEdit && (
            <div
              className="alert alert-warning"
              style={{ marginBottom: '1rem' }}
            >
              VIEWER role cannot run clause analysis. Contact your admin for
              EDITOR access.
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
            onClick={handleRunAnalysis}
            className="btn btn-primary"
            style={{ width: '100%' }}
            disabled={loading || !canEdit || clauseTypes.length === 0}
          >
            {loading ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>

        {/* Results Panel */}
        <div>
          {error && <div className="alert alert-error">{error}</div>}

          {loading && (
            <div className="card">
              <div className="loading">
                Analyzing clauses and generating redlines... This may take a
                moment.
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
                      ? 'Export is only available for success or insufficient_sources results'
                      : 'Download as DOCX'
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
                      Exporting...
                    </>
                  ) : (
                    <>
                      <span style={{ fontSize: '1rem' }}>&#x2193;</span>
                      Download DOCX
                    </>
                  )}
                </button>
              </div>

              {exportError && (
                <div
                  className="alert alert-error"
                  style={{ marginBottom: '1rem' }}
                >
                  Export failed: {exportError}
                </div>
              )}

              {/* Summary */}
              <div className="card mb-4">
                <div className="card-header">
                  <h3 className="card-title">
                    Summary
                    {countCitations(result.summary) > 0 && (
                      <span
                        className="text-muted text-sm"
                        style={{ fontWeight: 400, marginLeft: '0.5rem' }}
                      >
                        ({countCitations(result.summary)} citations)
                      </span>
                    )}
                  </h3>
                </div>

                {/* Insufficient Sources Info Banner */}
                {(result.insufficient_sources ||
                  result.meta.strict_citations_failed) && (
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
                          {result.insufficient_sources
                            ? 'Insufficient sources for confident analysis'
                            : 'Citation validation had issues'}
                        </div>
                        <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                          {result.meta.downgraded_count > 0 && (
                            <span>
                              {result.meta.downgraded_count} item
                              {result.meta.downgraded_count !== 1
                                ? 's'
                                : ''}{' '}
                              downgraded.{' '}
                            </span>
                          )}
                          {result.meta.removed_count > 0 && (
                            <span>
                              {result.meta.removed_count} item
                              {result.meta.removed_count !== 1 ? 's' : ''}{' '}
                              removed due to insufficient citations.
                            </span>
                          )}
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
                    Jurisdiction: {result.meta.jurisdiction}
                  </span>
                  <span className="badge badge-muted">
                    Model: {result.meta.model}
                  </span>
                  <span className="badge badge-muted">
                    Provider: {result.meta.provider}
                  </span>
                  <span className="badge badge-muted">
                    Evidence: {result.meta.evidence_chunk_count} chunks
                  </span>
                  {result.meta.downgraded_count > 0 && (
                    <span className="badge badge-warning">
                      Downgraded: {result.meta.downgraded_count}
                    </span>
                  )}
                  {result.meta.removed_count > 0 && (
                    <span className="badge badge-warning">
                      Removed: {result.meta.removed_count}
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

              {/* Clause Items */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">
                    Clause Analysis ({result.items.length})
                  </h3>
                </div>

                {result.items.length === 0 ? (
                  <p
                    className="text-muted"
                    style={{ textAlign: 'center', padding: '2rem 0' }}
                  >
                    No clause items identified in this analysis.
                  </p>
                ) : (
                  <div>
                    {/* Status summary */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {['found', 'missing', 'insufficient_evidence'].map(
                        status => {
                          const count = result.items.filter(
                            item => item.status === status
                          ).length;
                          if (count === 0) return null;
                          return (
                            <span
                              key={status}
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                padding: '0.25rem 0.75rem',
                                borderRadius: '4px',
                                fontSize: '0.875rem',
                                background: STATUS_BG[status],
                                color: STATUS_COLORS[status],
                                fontWeight: 500,
                              }}
                            >
                              {count} {status.replace('_', ' ')}
                            </span>
                          );
                        }
                      )}
                    </div>

                    {/* Severity summary */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {['critical', 'high', 'medium', 'low'].map(severity => {
                        const count = result.items.filter(
                          item => item.severity === severity
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
                      })}
                    </div>

                    {/* Clause cards */}
                    {result.items.map((item, idx) =>
                      renderClauseCard(item, idx)
                    )}
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
                Configure your analysis settings and click &ldquo;Run
                Analysis&rdquo; to detect clause types and get suggested
                redlines based on the clause library.
              </p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
