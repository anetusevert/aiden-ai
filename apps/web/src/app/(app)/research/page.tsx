'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  LegalResearchResponse,
  ResearchFilters,
  EvidenceScope,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge';
import { AdvancedSettingsPanel } from '@/components/EvidenceScopeSelector';
import {
  GroupedEvidenceList,
  EvidenceMetaPanel,
  renderCitationsWithDifferentiation,
} from '@/components/EvidenceCard';
import { toEvidenceItemFromChunk } from '@/lib/evidence';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { useTranslations } from 'next-intl';
import { WorkflowLaunchBanner } from '@/components/workflows/WorkflowLaunchBanner';

type OutputLanguage = 'en' | 'ar';

export default function ResearchPage() {
  const router = useRouter();
  const t = useTranslations('common');
  const tEvidence = useTranslations('evidence');
  const {
    isAuthenticated,
    isLoading: authLoading,
    defaultOutputLanguage,
    workspaceContext,
  } = useAuth();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LegalResearchResponse | null>(null);

  // Form state
  const [question, setQuestion] = useState('');
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>(
    defaultOutputLanguage
  );
  const [jurisdiction, setJurisdiction] = useState<string>('');
  const [documentType, setDocumentType] = useState<string>('');
  const [language, setLanguage] = useState<string>('');
  const [limit, setLimit] = useState(10);
  const [evidenceScope, setEvidenceScope] =
    useState<EvidenceScope>('workspace');

  // Memoize the evidence scope change handler
  const handleEvidenceScopeChange = useCallback((scope: EvidenceScope) => {
    setEvidenceScope(scope);
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    setOutputLanguage(defaultOutputLanguage);
  }, [defaultOutputLanguage]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const filters: ResearchFilters = {};
      if (jurisdiction) filters.jurisdiction = jurisdiction;
      if (documentType) filters.document_type = documentType;
      if (language) filters.language = language;

      const response = await apiClient.legalResearch({
        question,
        limit,
        output_language: outputLanguage,
        filters: Object.keys(filters).length > 0 ? filters : undefined,
        evidence_scope: evidenceScope,
      });

      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research failed');
    } finally {
      setLoading(false);
    }
  };

  // Use the enhanced citation rendering that differentiates global law [GL-X] from workspace [X]
  const renderAnswerWithCitations = (text: string) => {
    return renderCitationsWithDifferentiation(text, {
      globalCitationTitle: tEvidence('globalLawRefTitle'),
    });
  };

  if (authLoading) {
    return (
      <div className="loading">
        <span className="spinner" />
        <span style={{ marginLeft: 'var(--space-3)' }}>{t('loading')}</span>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      <WorkflowLaunchBanner currentRoute="/research" />

      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Legal Research</h1>
        <p className="page-subtitle">
          Ask legal questions and receive cited answers from your document vault
        </p>
      </div>

      {/* Workflow Layout */}
      <div className="workflow-layout">
        {/* Controls Panel */}
        <div className="workflow-controls">
          <div className="workflow-controls-header">
            <h3 className="workflow-controls-title">{t('researchQuery')}</h3>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="question" className="form-label">
                {t('question')}
              </label>
              <textarea
                id="question"
                className="form-textarea"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                placeholder={
                  defaultOutputLanguage === 'ar'
                    ? t('placeholderQuestionAr')
                    : t('placeholderQuestionEn')
                }
                required
                style={{ minHeight: '100px' }}
              />
            </div>

            <div className="form-group">
              <label htmlFor="outputLang" className="form-label">
                Answer Language
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
                <span className="form-hint">
                  {t('workspaceDefault')}{' '}
                  {defaultOutputLanguage === 'ar' ? t('arabic') : t('english')}
                </span>
              )}
            </div>

            <div className="divider" />

            <p className="text-sm text-muted mb-3">{t('optionalFilters')}</p>

            <div className="form-group">
              <label htmlFor="filterJurisdiction" className="form-label">
                {t('jurisdiction')}
              </label>
              <select
                id="filterJurisdiction"
                className="form-select"
                value={jurisdiction}
                onChange={e => setJurisdiction(e.target.value)}
              >
                <option value="">{t('any')}</option>
                <option value="UAE">{t('uae')}</option>
                <option value="DIFC">{t('difc')}</option>
                <option value="ADGM">{t('adgm')}</option>
                <option value="KSA">{t('ksa')}</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="filterDocType" className="form-label">
                {t('documentType')}
              </label>
              <select
                id="filterDocType"
                className="form-select"
                value={documentType}
                onChange={e => setDocumentType(e.target.value)}
              >
                <option value="">{t('any')}</option>
                <option value="contract">{t('docTypeContract')}</option>
                <option value="policy">{t('docTypePolicy')}</option>
                <option value="memo">{t('docTypeMemo')}</option>
                <option value="regulatory">{t('docTypeRegulatory')}</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="limit" className="form-label">
                {t('evidenceLimit')}
              </label>
              <input
                id="limit"
                type="number"
                className="form-input"
                value={limit}
                onChange={e => setLimit(parseInt(e.target.value) || 10)}
                min={1}
                max={50}
              />
            </div>

            {/* Advanced Settings (Evidence Scope) */}
            {workspaceContext?.id && (
              <AdvancedSettingsPanel
                workspaceId={workspaceContext.id}
                evidenceScope={evidenceScope}
                onEvidenceScopeChange={handleEvidenceScopeChange}
              />
            )}

            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={loading || !question.trim()}
            >
              {loading ? (
                <>
                  <span className="spinner spinner-sm" />
                  {t('researching')}
                </>
              ) : (
                t('submitQuery')
              )}
            </button>
          </form>
        </div>

        {/* Results Panel */}
        <div className="workflow-results">
          {error && (
            <div style={{ padding: 'var(--space-5)' }}>
              <div className="alert alert-error">{error}</div>
            </div>
          )}

          {loading && (
            <div className="workflow-empty">
              <span
                className="spinner spinner-lg"
                style={{ marginBottom: 'var(--space-4)' }}
              />
              <p className="workflow-empty-title">Searching Documents</p>
              <p className="workflow-empty-desc">
                Analyzing your document vault and generating a cited answer...
              </p>
            </div>
          )}

          {result && (
            <div>
              {/* Status Header */}
              <div className="workflow-results-header">
                <h3 className="workflow-results-title">
                  {t('researchResults')}
                </h3>
                <WorkflowStatusBadge status={result.meta.status} />
              </div>

              <div className="workflow-results-body">
                {/* Insufficient Sources Banner */}
                {(result.insufficient_sources ||
                  result.meta.strict_citations_failed) && (
                  <div
                    className="alert alert-neutral"
                    style={{ marginBottom: 'var(--space-5)' }}
                  >
                    <div>
                      <strong>{t('limitedSourceCoverage')}</strong>
                      <p
                        style={{
                          margin: 'var(--space-1) 0 0',
                          fontSize: 'var(--text-sm)',
                        }}
                      >
                        {t('limitedSourceCoverageBody', {
                          count: result.evidence.length,
                        })}
                      </p>
                    </div>
                  </div>
                )}

                {/* Answer */}
                <div className="workflow-answer">
                  <div className="workflow-answer-text">
                    {renderAnswerWithCitations(result.answer_text)}
                  </div>

                  <div
                    className="flex flex-wrap gap-2 mt-4"
                    style={{
                      paddingTop: 'var(--space-4)',
                      borderTop: '1px solid var(--border)',
                    }}
                  >
                    <span className="badge badge-muted">
                      {t('model')}: {result.meta.model}
                    </span>
                    <span className="badge badge-muted">
                      {t('chunks')}: {result.meta.chunk_count}
                    </span>
                    <span className="badge badge-muted">
                      {t('citations')}: {result.meta.citation_count_used}
                    </span>
                  </div>
                </div>

                {/* Citations */}
                {result.citations.length > 0 && (
                  <div className="workflow-citations">
                    <h4 className="workflow-citations-title">
                      Citations ({result.citations.length})
                    </h4>
                    {result.citations.map(citation => (
                      <div
                        key={citation.citation_index}
                        className="workflow-citation-item"
                      >
                        <span className="workflow-citation-number">
                          {citation.citation_index}
                        </span>
                        <div className="workflow-citation-content">
                          <p className="workflow-citation-doc">
                            <Link href={`/documents/${citation.document_id}`}>
                              {citation.document_title}
                            </Link>
                          </p>
                          <div className="flex items-center justify-between gap-2">
                            <span className="workflow-citation-chunk">
                              {tEvidence('charsRange', {
                                start: citation.char_start,
                                end: citation.char_end,
                              })}
                              {citation.page_start &&
                                ` · ${tEvidence('pageMeta', {
                                  page: citation.page_start,
                                })}`}
                            </span>
                            <Link
                              href={`/documents/${citation.document_id}/versions/${citation.version_id}/viewer?chunkId=${citation.chunk_id}`}
                              className="view-in-doc-link"
                            >
                              {t('view')}
                            </Link>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Evidence Meta Panel - shows evidence counts by source */}
                <EvidenceMetaPanel
                  workspaceCount={result.meta.workspace_evidence_count}
                  globalCount={result.meta.global_evidence_count}
                  evidenceScope={result.meta.evidence_scope}
                />

                {/* Evidence - Grouped by Source Type */}
                {result.evidence.length > 0 && (
                  <div className="workflow-evidence">
                    <h4 className="workflow-evidence-title">
                      {t('evidenceHeading', { count: result.evidence.length })}
                    </h4>
                    <GroupedEvidenceList
                      evidence={result.evidence.map(toEvidenceItemFromChunk)}
                      maxItemsPerSection={5}
                      showGlobalLawBanner={true}
                      showMore={true}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="workflow-empty">
              <div className="workflow-empty-icon">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <p className="workflow-empty-title">{t('enterResearchQuery')}</p>
              <p className="workflow-empty-desc">
                {t('enterResearchQueryDesc')}
              </p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
