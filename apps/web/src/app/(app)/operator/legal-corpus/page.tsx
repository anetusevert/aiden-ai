'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import {
  apiClient,
  LegalInstrumentWithLatestVersion,
  LegalInstrumentWithVersions,
  LegalVersionSummary,
  PurgeResponse,
} from '@/lib/apiClient';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

// Jurisdiction options
const JURISDICTIONS = [
  { value: 'UAE', label: 'UAE' },
  { value: 'DIFC', label: 'DIFC' },
  { value: 'ADGM', label: 'ADGM' },
  { value: 'KSA', label: 'KSA' },
  { value: 'OMAN', label: 'Oman' },
  { value: 'BAHRAIN', label: 'Bahrain' },
  { value: 'QATAR', label: 'Qatar' },
  { value: 'KUWAIT', label: 'Kuwait' },
];

// Instrument type options
const INSTRUMENT_TYPES = [
  { value: 'law', label: 'Law' },
  { value: 'federal_law', label: 'Federal Law' },
  { value: 'local_law', label: 'Local Law' },
  { value: 'decree', label: 'Decree' },
  { value: 'royal_decree', label: 'Royal Decree' },
  { value: 'regulation', label: 'Regulation' },
  { value: 'ministerial_resolution', label: 'Ministerial Resolution' },
  { value: 'circular', label: 'Circular' },
  { value: 'guideline', label: 'Guideline' },
  { value: 'directive', label: 'Directive' },
  { value: 'order', label: 'Order' },
  { value: 'other', label: 'Other' },
];

// Language options
const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ar', label: 'Arabic' },
  { value: 'mixed', label: 'Mixed' },
];

export default function LegalCorpusPage() {
  const { user } = useAuth();
  const [instruments, setInstruments] = useState<
    LegalInstrumentWithLatestVersion[]
  >([]);
  const [selectedInstrument, setSelectedInstrument] =
    useState<LegalInstrumentWithVersions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [reindexingVersionId, setReindexingVersionId] = useState<string | null>(
    null
  );
  const [showPurgeModal, setShowPurgeModal] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeResult, setPurgeResult] = useState<PurgeResponse | null>(null);

  // Create form state
  const [createForm, setCreateForm] = useState({
    jurisdiction: 'UAE',
    instrument_type: 'law',
    title: '',
    title_ar: '',
    official_source_url: '',
    published_at: '',
    effective_at: '',
    status: 'active',
    version_label: '',
    language: 'en',
  });
  const [createFile, setCreateFile] = useState<File | null>(null);
  const [creating, setCreating] = useState(false);

  // Version form state
  const [versionForm, setVersionForm] = useState({
    version_label: '',
    language: 'en',
  });
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [uploadingVersion, setUploadingVersion] = useState(false);

  // Check if user is platform admin
  const isPlatformAdmin = user?.is_platform_admin === true;

  // Load instruments
  const loadInstruments = useCallback(async () => {
    if (!isPlatformAdmin) return;

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.listLegalInstruments({ limit: 100 });
      setInstruments(response.items);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load instruments'
      );
    } finally {
      setLoading(false);
    }
  }, [isPlatformAdmin]);

  useEffect(() => {
    loadInstruments();
  }, [loadInstruments]);

  // Load instrument detail
  const loadInstrumentDetail = async (instrumentId: string) => {
    try {
      const detail = await apiClient.getLegalInstrument(instrumentId);
      setSelectedInstrument(detail);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load instrument details'
      );
    }
  };

  // Create instrument
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);

    try {
      await apiClient.createLegalInstrument(
        {
          ...createForm,
          title_ar: createForm.title_ar || undefined,
          official_source_url: createForm.official_source_url || undefined,
          published_at: createForm.published_at || undefined,
          effective_at: createForm.effective_at || undefined,
          version_label: createFile ? createForm.version_label : undefined,
          language: createFile ? createForm.language : undefined,
        },
        createFile || undefined
      );
      setShowCreateModal(false);
      setCreateForm({
        jurisdiction: 'UAE',
        instrument_type: 'law',
        title: '',
        title_ar: '',
        official_source_url: '',
        published_at: '',
        effective_at: '',
        status: 'active',
        version_label: '',
        language: 'en',
      });
      setCreateFile(null);
      await loadInstruments();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create instrument'
      );
    } finally {
      setCreating(false);
    }
  };

  // Upload version
  const handleUploadVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInstrument || !versionFile) return;

    setUploadingVersion(true);
    setError(null);

    try {
      await apiClient.uploadLegalVersion(
        selectedInstrument.id,
        versionForm.version_label,
        versionForm.language,
        versionFile
      );
      setShowVersionModal(false);
      setVersionForm({ version_label: '', language: 'en' });
      setVersionFile(null);
      await loadInstrumentDetail(selectedInstrument.id);
      await loadInstruments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload version');
    } finally {
      setUploadingVersion(false);
    }
  };

  // Reindex version
  const handleReindex = async (instrumentId: string, versionId: string) => {
    setReindexingVersionId(versionId);
    setError(null);

    try {
      await apiClient.reindexLegalVersion(instrumentId, versionId, true);
      if (selectedInstrument?.id === instrumentId) {
        await loadInstrumentDetail(instrumentId);
      }
      await loadInstruments();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to reindex version'
      );
    } finally {
      setReindexingVersionId(null);
    }
  };

  // Purge all legal corpus data
  const handlePurge = async () => {
    setPurging(true);
    setError(null);
    setPurgeResult(null);

    try {
      const result = await apiClient.purgeAllLegalCorpus();
      setPurgeResult(result);
      setSelectedInstrument(null);
      await loadInstruments();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to purge legal corpus'
      );
      setShowPurgeModal(false);
    } finally {
      setPurging(false);
    }
  };

  // Format date for display
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  // Access denied for non-platform admins
  if (!isPlatformAdmin) {
    return (
      <div className="page-container">
        <div className="alert alert-error">
          <h3>Access Denied</h3>
          <p>This page is only available to platform administrators.</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp} className="page-container">
      <div className="page-header">
        <div>
          <h1>Global Legal Corpus</h1>
          <p className="text-secondary">
            Manage baseline laws and regulations across GCC jurisdictions.
          </p>
        </div>
        <div className="page-header-actions">
          <button
            className="btn btn-danger"
            onClick={() => setShowPurgeModal(true)}
            disabled={instruments.length === 0}
          >
            Purge All Data
          </button>
          <Link
            href="/operator/legal-corpus/import"
            className="btn btn-secondary"
          >
            Import Snapshot
          </Link>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
          >
            Add Legal Instrument
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: '1rem' }}>
            Dismiss
          </button>
        </div>
      )}

      <div className="legal-corpus-layout">
        {/* Instruments List */}
        <div className="instruments-panel">
          <h2>Legal Instruments ({instruments.length})</h2>

          {loading ? (
            <div className="loading-state">Loading...</div>
          ) : instruments.length === 0 ? (
            <div className="empty-state">
              <p>No legal instruments yet.</p>
              <p>Click &ldquo;Add Legal Instrument&rdquo; to get started.</p>
            </div>
          ) : (
            <div className="instruments-list">
              {instruments.map(instrument => (
                <div
                  key={instrument.id}
                  className={`instrument-card ${selectedInstrument?.id === instrument.id ? 'selected' : ''}`}
                  onClick={() => loadInstrumentDetail(instrument.id)}
                >
                  <div className="instrument-header">
                    <span className="jurisdiction-badge">
                      {instrument.jurisdiction}
                    </span>
                    <span className="type-badge">
                      {instrument.instrument_type.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`status-badge status-${instrument.status}`}
                    >
                      {instrument.status}
                    </span>
                  </div>
                  <h3>{instrument.title}</h3>
                  {instrument.title_ar && (
                    <p className="title-ar" dir="rtl">
                      {instrument.title_ar}
                    </p>
                  )}
                  <div className="instrument-meta">
                    {instrument.latest_version ? (
                      <>
                        <span>
                          {instrument.latest_version.is_indexed
                            ? '✓ Indexed'
                            : '○ Not indexed'}
                        </span>
                        <span>{instrument.latest_version.version_label}</span>
                      </>
                    ) : (
                      <span className="text-muted">No versions</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        <div className="detail-panel">
          {selectedInstrument ? (
            <>
              <div className="detail-header">
                <h2>{selectedInstrument.title}</h2>
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowVersionModal(true)}
                >
                  Upload Version
                </button>
              </div>

              {selectedInstrument.title_ar && (
                <p className="title-ar" dir="rtl">
                  {selectedInstrument.title_ar}
                </p>
              )}

              <div className="detail-meta">
                <div className="meta-item">
                  <label>Jurisdiction:</label>
                  <span>{selectedInstrument.jurisdiction}</span>
                </div>
                <div className="meta-item">
                  <label>Type:</label>
                  <span>
                    {selectedInstrument.instrument_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="meta-item">
                  <label>Status:</label>
                  <span
                    className={`status-badge status-${selectedInstrument.status}`}
                  >
                    {selectedInstrument.status}
                  </span>
                </div>
                <div className="meta-item">
                  <label>Published:</label>
                  <span>{formatDate(selectedInstrument.published_at)}</span>
                </div>
                <div className="meta-item">
                  <label>Effective:</label>
                  <span>{formatDate(selectedInstrument.effective_at)}</span>
                </div>
                {selectedInstrument.official_source_url && (
                  <div className="meta-item">
                    <label>Official Source:</label>
                    <a
                      href={selectedInstrument.official_source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View Source
                    </a>
                  </div>
                )}
              </div>

              <h3>Versions ({selectedInstrument.versions.length})</h3>
              {selectedInstrument.versions.length === 0 ? (
                <p className="text-muted">No versions uploaded yet.</p>
              ) : (
                <div className="versions-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Language</th>
                        <th>File</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <motion.tbody
                      variants={staggerContainer}
                      initial="hidden"
                      animate="visible"
                    >
                      {selectedInstrument.versions.map(version => (
                        <motion.tr variants={staggerItem} key={version.id}>
                          <td>{version.version_label}</td>
                          <td>{version.language.toUpperCase()}</td>
                          <td>{version.file_name}</td>
                          <td>
                            {version.is_indexed ? (
                              <span className="indexed-badge">
                                ✓ Indexed ({version.embedding_model})
                              </span>
                            ) : (
                              <span className="not-indexed-badge">
                                ○ Not indexed
                              </span>
                            )}
                          </td>
                          <td>
                            <button
                              className="btn btn-sm btn-secondary"
                              onClick={() =>
                                handleReindex(selectedInstrument.id, version.id)
                              }
                              disabled={reindexingVersionId === version.id}
                            >
                              {reindexingVersionId === version.id
                                ? 'Reindexing...'
                                : 'Reindex'}
                            </button>
                          </td>
                        </motion.tr>
                      ))}
                    </motion.tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <p>Select a legal instrument to view details.</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div
          className="modal-overlay"
          onClick={() => setShowCreateModal(false)}
        >
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Add Legal Instrument</h2>
              <button
                className="modal-close"
                onClick={() => setShowCreateModal(false)}
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="modal-body">
                <div className="form-row">
                  <div className="form-group">
                    <label>Jurisdiction *</label>
                    <select
                      value={createForm.jurisdiction}
                      onChange={e =>
                        setCreateForm({
                          ...createForm,
                          jurisdiction: e.target.value,
                        })
                      }
                      required
                    >
                      {JURISDICTIONS.map(j => (
                        <option key={j.value} value={j.value}>
                          {j.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Instrument Type *</label>
                    <select
                      value={createForm.instrument_type}
                      onChange={e =>
                        setCreateForm({
                          ...createForm,
                          instrument_type: e.target.value,
                        })
                      }
                      required
                    >
                      {INSTRUMENT_TYPES.map(t => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label>Title (English) *</label>
                  <input
                    type="text"
                    value={createForm.title}
                    onChange={e =>
                      setCreateForm({ ...createForm, title: e.target.value })
                    }
                    required
                    placeholder="Official title in English"
                  />
                </div>

                <div className="form-group">
                  <label>Title (Arabic)</label>
                  <input
                    type="text"
                    value={createForm.title_ar}
                    onChange={e =>
                      setCreateForm({ ...createForm, title_ar: e.target.value })
                    }
                    placeholder="Official title in Arabic"
                    dir="rtl"
                  />
                </div>

                <div className="form-group">
                  <label>Official Source URL</label>
                  <input
                    type="url"
                    value={createForm.official_source_url}
                    onChange={e =>
                      setCreateForm({
                        ...createForm,
                        official_source_url: e.target.value,
                      })
                    }
                    placeholder="https://..."
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Published Date</label>
                    <input
                      type="date"
                      value={createForm.published_at}
                      onChange={e =>
                        setCreateForm({
                          ...createForm,
                          published_at: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="form-group">
                    <label>Effective Date</label>
                    <input
                      type="date"
                      value={createForm.effective_at}
                      onChange={e =>
                        setCreateForm({
                          ...createForm,
                          effective_at: e.target.value,
                        })
                      }
                    />
                  </div>
                </div>

                <hr />

                <h3>Initial Version (Optional)</h3>
                <p className="text-muted">
                  Upload a document to create the first version.
                </p>

                <div className="form-row">
                  <div className="form-group">
                    <label>Version Label</label>
                    <input
                      type="text"
                      value={createForm.version_label}
                      onChange={e =>
                        setCreateForm({
                          ...createForm,
                          version_label: e.target.value,
                        })
                      }
                      placeholder="e.g., v1.0, 2024-original"
                    />
                  </div>
                  <div className="form-group">
                    <label>Language</label>
                    <select
                      value={createForm.language}
                      onChange={e =>
                        setCreateForm({
                          ...createForm,
                          language: e.target.value,
                        })
                      }
                    >
                      {LANGUAGES.map(l => (
                        <option key={l.value} value={l.value}>
                          {l.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label>Document File</label>
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={e => setCreateFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={creating}
                >
                  {creating ? 'Creating...' : 'Create Instrument'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload Version Modal */}
      {showVersionModal && selectedInstrument && (
        <div
          className="modal-overlay"
          onClick={() => setShowVersionModal(false)}
        >
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Upload Version</h2>
              <button
                className="modal-close"
                onClick={() => setShowVersionModal(false)}
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleUploadVersion}>
              <div className="modal-body">
                <p>
                  Uploading version for:{' '}
                  <strong>{selectedInstrument.title}</strong>
                </p>

                <div className="form-row">
                  <div className="form-group">
                    <label>Version Label *</label>
                    <input
                      type="text"
                      value={versionForm.version_label}
                      onChange={e =>
                        setVersionForm({
                          ...versionForm,
                          version_label: e.target.value,
                        })
                      }
                      required
                      placeholder="e.g., v1.0, 2024-amendment"
                    />
                  </div>
                  <div className="form-group">
                    <label>Language *</label>
                    <select
                      value={versionForm.language}
                      onChange={e =>
                        setVersionForm({
                          ...versionForm,
                          language: e.target.value,
                        })
                      }
                      required
                    >
                      {LANGUAGES.map(l => (
                        <option key={l.value} value={l.value}>
                          {l.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label>Document File *</label>
                  <input
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={e => setVersionFile(e.target.files?.[0] || null)}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowVersionModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploadingVersion || !versionFile}
                >
                  {uploadingVersion ? 'Uploading...' : 'Upload Version'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Purge Confirmation Modal */}
      {showPurgeModal && (
        <div
          className="modal-overlay"
          onClick={() => !purging && setShowPurgeModal(false)}
        >
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{purgeResult ? 'Purge Complete' : 'Confirm Purge'}</h2>
              <button
                className="modal-close"
                onClick={() => {
                  setShowPurgeModal(false);
                  setPurgeResult(null);
                }}
                disabled={purging}
              >
                &times;
              </button>
            </div>
            <div className="modal-body">
              {purgeResult ? (
                <div className="purge-result">
                  <div className="purge-success-icon">✓</div>
                  <p className="purge-message">{purgeResult.message}</p>
                  <div className="purge-stats">
                    <div className="purge-stat">
                      <span className="purge-stat-value">
                        {purgeResult.instruments_deleted}
                      </span>
                      <span className="purge-stat-label">Instruments</span>
                    </div>
                    <div className="purge-stat">
                      <span className="purge-stat-value">
                        {purgeResult.versions_deleted}
                      </span>
                      <span className="purge-stat-label">Versions</span>
                    </div>
                    <div className="purge-stat">
                      <span className="purge-stat-value">
                        {purgeResult.chunks_deleted}
                      </span>
                      <span className="purge-stat-label">Chunks</span>
                    </div>
                    <div className="purge-stat">
                      <span className="purge-stat-value">
                        {purgeResult.embeddings_deleted}
                      </span>
                      <span className="purge-stat-label">Embeddings</span>
                    </div>
                  </div>
                  <p
                    className="text-muted"
                    style={{ marginTop: '1rem', fontSize: '0.85rem' }}
                  >
                    Note: S3 files were NOT deleted. You can now re-import a
                    snapshot.
                  </p>
                </div>
              ) : (
                <>
                  <div className="purge-warning">
                    <div className="purge-warning-icon">⚠️</div>
                    <h3>This action cannot be undone!</h3>
                    <p>
                      You are about to delete ALL legal corpus data, including:
                    </p>
                    <ul>
                      <li>
                        <strong>{instruments.length}</strong> legal instruments
                      </li>
                      <li>All associated versions, chunks, and embeddings</li>
                    </ul>
                    <p>
                      S3 files will NOT be deleted. After purging, you can
                      re-import a snapshot.
                    </p>
                  </div>
                </>
              )}
            </div>
            <div className="modal-footer">
              {purgeResult ? (
                <button
                  className="btn btn-primary"
                  onClick={() => {
                    setShowPurgeModal(false);
                    setPurgeResult(null);
                  }}
                >
                  Done
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setShowPurgeModal(false)}
                    disabled={purging}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={handlePurge}
                    disabled={purging}
                  >
                    {purging ? 'Purging...' : 'Yes, Purge All Data'}
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .page-container {
          padding: 2rem;
          max-width: 1400px;
          margin: 0 auto;
        }

        .page-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 2rem;
        }

        .page-header h1 {
          margin: 0 0 0.5rem 0;
        }

        .page-header-actions {
          display: flex;
          gap: 0.75rem;
        }

        .page-header-actions .btn-secondary {
          text-decoration: none;
        }

        .text-secondary {
          color: var(--text-secondary, #6b7280);
          margin: 0;
        }

        .text-muted {
          color: var(--text-muted, #9ca3af);
        }

        .legal-corpus-layout {
          display: grid;
          grid-template-columns: 400px 1fr;
          gap: 2rem;
          min-height: 600px;
        }

        .instruments-panel,
        .detail-panel {
          background: var(--card-bg, #fff);
          border-radius: 8px;
          border: 1px solid var(--border-color, #e5e7eb);
          padding: 1.5rem;
        }

        .instruments-panel h2,
        .detail-panel h2 {
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
        }

        .instruments-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          max-height: 600px;
          overflow-y: auto;
        }

        .instrument-card {
          padding: 1rem;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 6px;
          cursor: pointer;
          transition:
            border-color 0.2s,
            background-color 0.2s;
        }

        .instrument-card:hover {
          border-color: var(--primary-color, #3b82f6);
        }

        .instrument-card.selected {
          border-color: var(--primary-color, #3b82f6);
          background-color: var(--primary-bg-light, #eff6ff);
        }

        .instrument-header {
          display: flex;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .jurisdiction-badge,
        .type-badge,
        .status-badge {
          font-size: 0.75rem;
          padding: 0.125rem 0.5rem;
          border-radius: 4px;
          background: var(--badge-bg, #f3f4f6);
          color: var(--badge-text, #374151);
        }

        .status-active {
          background: #dcfce7;
          color: #166534;
        }
        .status-superseded {
          background: #fef3c7;
          color: #92400e;
        }
        .status-repealed {
          background: #fee2e2;
          color: #991b1b;
        }
        .status-draft {
          background: #e0e7ff;
          color: #3730a3;
        }

        .instrument-card h3 {
          margin: 0 0 0.25rem 0;
          font-size: 0.95rem;
          font-weight: 500;
        }

        .title-ar {
          font-size: 0.9rem;
          color: var(--text-secondary, #6b7280);
          margin: 0.25rem 0;
        }

        .instrument-meta {
          display: flex;
          gap: 1rem;
          font-size: 0.8rem;
          color: var(--text-secondary, #6b7280);
          margin-top: 0.5rem;
        }

        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .detail-header h2 {
          margin: 0;
        }

        .detail-meta {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1rem;
          margin: 1.5rem 0;
          padding: 1rem;
          background: var(--meta-bg, #f9fafb);
          border-radius: 6px;
        }

        .meta-item label {
          display: block;
          font-size: 0.75rem;
          color: var(--text-secondary, #6b7280);
          margin-bottom: 0.25rem;
        }

        .versions-table {
          margin-top: 1rem;
        }

        .versions-table table {
          width: 100%;
          border-collapse: collapse;
        }

        .versions-table th,
        .versions-table td {
          padding: 0.75rem;
          text-align: left;
          border-bottom: 1px solid var(--border-color, #e5e7eb);
        }

        .versions-table th {
          font-weight: 500;
          font-size: 0.85rem;
          color: var(--text-secondary, #6b7280);
        }

        .indexed-badge {
          color: #166534;
          font-size: 0.85rem;
        }

        .not-indexed-badge {
          color: #92400e;
          font-size: 0.85rem;
        }

        .empty-state,
        .loading-state {
          padding: 2rem;
          text-align: center;
          color: var(--text-secondary, #6b7280);
        }

        .alert {
          padding: 1rem;
          border-radius: 6px;
          margin-bottom: 1rem;
        }

        .alert-error {
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fecaca;
        }

        /* Modal styles */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: var(--card-bg, #fff);
          border-radius: 8px;
          width: 100%;
          max-width: 600px;
          max-height: 90vh;
          overflow-y: auto;
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem;
          border-bottom: 1px solid var(--border-color, #e5e7eb);
        }

        .modal-header h2 {
          margin: 0;
        }

        .modal-close {
          background: none;
          border: none;
          font-size: 1.5rem;
          cursor: pointer;
          color: var(--text-secondary, #6b7280);
        }

        .modal-body {
          padding: 1.5rem;
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 1rem;
          padding: 1.5rem;
          border-top: 1px solid var(--border-color, #e5e7eb);
        }

        .form-group {
          margin-bottom: 1rem;
        }

        .form-group label {
          display: block;
          margin-bottom: 0.5rem;
          font-weight: 500;
          font-size: 0.9rem;
        }

        .form-group input,
        .form-group select {
          width: 100%;
          padding: 0.5rem 0.75rem;
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 6px;
          font-size: 0.95rem;
        }

        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        hr {
          border: none;
          border-top: 1px solid var(--border-color, #e5e7eb);
          margin: 1.5rem 0;
        }

        .btn {
          padding: 0.5rem 1rem;
          border-radius: 6px;
          font-weight: 500;
          cursor: pointer;
          border: none;
          transition: background-color 0.2s;
        }

        .btn-primary {
          background: var(--primary-color, #3b82f6);
          color: white;
        }

        .btn-primary:hover {
          background: var(--primary-hover, #2563eb);
        }

        .btn-primary:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .btn-secondary {
          background: var(--secondary-bg, #f3f4f6);
          color: var(--text-primary, #374151);
        }

        .btn-secondary:hover {
          background: var(--secondary-hover, #e5e7eb);
        }

        .btn-danger {
          background: #dc2626;
          color: white;
        }

        .btn-danger:hover:not(:disabled) {
          background: #b91c1c;
        }

        .btn-danger:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .btn-sm {
          padding: 0.25rem 0.5rem;
          font-size: 0.85rem;
        }

        /* Purge modal styles */
        .purge-warning {
          text-align: center;
          padding: 1rem;
        }

        .purge-warning-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .purge-warning h3 {
          color: #dc2626;
          margin: 0 0 1rem 0;
        }

        .purge-warning ul {
          text-align: left;
          margin: 1rem 0;
          padding-left: 1.5rem;
        }

        .purge-warning li {
          margin: 0.5rem 0;
        }

        .purge-result {
          text-align: center;
          padding: 1rem;
        }

        .purge-success-icon {
          font-size: 3rem;
          color: #16a34a;
          background: #dcfce7;
          width: 80px;
          height: 80px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 1rem;
        }

        .purge-message {
          font-weight: 500;
          margin-bottom: 1.5rem;
        }

        .purge-stats {
          display: flex;
          justify-content: center;
          gap: 1.5rem;
          flex-wrap: wrap;
        }

        .purge-stat {
          text-align: center;
          padding: 0.75rem 1rem;
          background: var(--secondary-bg, #f3f4f6);
          border-radius: 8px;
          min-width: 80px;
        }

        .purge-stat-value {
          display: block;
          font-size: 1.5rem;
          font-weight: 600;
          color: #dc2626;
        }

        .purge-stat-label {
          display: block;
          font-size: 0.75rem;
          color: var(--text-secondary, #6b7280);
          margin-top: 0.25rem;
        }

        @media (max-width: 900px) {
          .legal-corpus-layout {
            grid-template-columns: 1fr;
          }

          .form-row {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </motion.div>
  );
}
