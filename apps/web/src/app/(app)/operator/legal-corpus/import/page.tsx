'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useAuth } from '@/lib/AuthContext';
import {
  apiClient,
  SnapshotImportResponse,
  SnapshotImportFailure,
  BatchStatusResponse,
  BatchReindexResponse,
  BatchReindexFailure,
  ApiClientError,
} from '@/lib/apiClient';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';

export default function SnapshotImportPage() {
  const { user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<SnapshotImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reindex state
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(
    null
  );
  const [reindexing, setReindexing] = useState(false);
  const [reindexResult, setReindexResult] =
    useState<BatchReindexResponse | null>(null);
  const [reindexError, setReindexError] = useState<string | null>(null);

  // Check if user is platform admin
  const isPlatformAdmin = user?.is_platform_admin === true;

  // Load batch status when result changes
  const loadBatchStatus = useCallback(async (batchId: string) => {
    try {
      const status = await apiClient.getImportBatchStatus(batchId);
      setBatchStatus(status);
    } catch (err) {
      // Silently fail - status is optional
      console.error('Failed to load batch status:', err);
    }
  }, []);

  useEffect(() => {
    if (result?.import_batch_id) {
      loadBatchStatus(result.import_batch_id);
    }
  }, [result?.import_batch_id, loadBatchStatus]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.name.endsWith('.zip')) {
        setError('Please select a .zip file');
        setSelectedFile(null);
        return;
      }
      setSelectedFile(file);
      setError(null);
      setResult(null);
      setBatchStatus(null);
      setReindexResult(null);
      setReindexError(null);
    }
  };

  const handleImport = async () => {
    if (!selectedFile) return;

    setImporting(true);
    setError(null);
    setResult(null);
    setBatchStatus(null);
    setReindexResult(null);
    setReindexError(null);

    try {
      const response = await apiClient.importSnapshot(selectedFile);
      setResult(response);
      // Clear file selection on success
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 403) {
          setError(
            'Access denied: Platform administrator privileges required.'
          );
        } else if (err.status === 400) {
          setError(err.message);
        } else {
          setError(err.message || 'Import failed. Please try again.');
        }
      } else if (err instanceof Error) {
        setError(
          err.message ||
            'Network error. Please check your connection and try again.'
        );
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setImporting(false);
    }
  };

  const handleReindex = async (indexAll: boolean = false) => {
    if (!result?.import_batch_id) return;

    setReindexing(true);
    setReindexError(null);
    setReindexResult(null);

    try {
      const response = await apiClient.reindexImportBatch(
        result.import_batch_id,
        indexAll ? 5000 : 25,
        indexAll
      );
      setReindexResult(response);
      // Refresh status
      await loadBatchStatus(result.import_batch_id);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 403) {
          setReindexError(
            'Access denied: Platform administrator privileges required.'
          );
        } else if (err.status === 400) {
          setReindexError(err.message);
        } else {
          setReindexError(err.message || 'Reindex failed. Please try again.');
        }
      } else if (err instanceof Error) {
        setReindexError(
          err.message ||
            'Network error. Please check your connection and try again.'
        );
      } else {
        setReindexError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setReindexing(false);
    }
  };

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`;
    const seconds = (ms / 1000).toFixed(1);
    return `${seconds}s`;
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Access denied for non-platform admins
  if (!isPlatformAdmin) {
    return (
      <motion.div className="page-container" {...fadeUp}>
        <div className="alert alert-error">
          <h3>Platform Administrator Required</h3>
          <p>
            This page is only available to platform administrators. Contact your
            system administrator if you need access to snapshot import
            functionality.
          </p>
        </div>
        <style jsx>{pageStyles}</style>
      </motion.div>
    );
  }

  return (
    <motion.div className="page-container" {...fadeUp}>
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link href="/operator/legal-corpus">Global Legal Corpus</Link>
            <span className="breadcrumb-separator">/</span>
            <span>Snapshot Import</span>
          </div>
          <h1>Import Harvester Snapshot</h1>
          <p className="text-secondary">
            Upload a gcc-harvester snapshot ZIP to bulk import legal instruments
            into the global corpus.
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="alert alert-error">
          <div className="alert-content">
            <strong>Import Failed</strong>
            <p>{error}</p>
          </div>
          <button className="alert-dismiss" onClick={() => setError(null)}>
            &times;
          </button>
        </div>
      )}

      {/* Upload Card */}
      <div className="upload-card">
        <div className="upload-icon">
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>

        <div className="upload-content">
          <h2>Select Snapshot ZIP</h2>
          <p className="text-secondary">
            Upload a harvester snapshot archive containing manifest.json,
            records/*.jsonl, and raw artifacts.
          </p>

          <div className="file-input-wrapper">
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={handleFileSelect}
              disabled={importing}
              className="file-input"
              id="snapshot-file"
            />
            <label
              htmlFor="snapshot-file"
              className={`file-label ${importing ? 'disabled' : ''}`}
            >
              {selectedFile ? (
                <span className="file-selected">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  {selectedFile.name} ({formatFileSize(selectedFile.size)})
                </span>
              ) : (
                <span>Choose .zip file...</span>
              )}
            </label>
          </div>

          <button
            className="btn btn-primary btn-large"
            onClick={handleImport}
            disabled={!selectedFile || importing}
          >
            {importing ? (
              <>
                <span className="spinner"></span>
                Importing...
              </>
            ) : (
              'Upload & Import'
            )}
          </button>
        </div>
      </div>

      {/* Result Card */}
      {result && (
        <div className="result-card">
          <div className="result-header">
            <div className="result-icon success">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <div>
              <h2>Import Complete</h2>
              <p className="text-secondary">
                Batch ID: <code>{result.import_batch_id}</code>
              </p>
            </div>
          </div>

          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value created">
                {result.instruments_created}
              </div>
              <div className="stat-label">Instruments Created</div>
            </div>
            <div className="stat-item">
              <div className="stat-value existing">
                {result.instruments_existing}
              </div>
              <div className="stat-label">Instruments Existing</div>
            </div>
            <div className="stat-item">
              <div className="stat-value created">
                {result.versions_created}
              </div>
              <div className="stat-label">Versions Created</div>
            </div>
            <div className="stat-item">
              <div className="stat-value existing">
                {result.versions_existing}
              </div>
              <div className="stat-label">Versions Existing</div>
            </div>
            <div className="stat-item">
              <div
                className={`stat-value ${result.failure_count > 0 ? 'failed' : 'success'}`}
              >
                {result.failure_count}
              </div>
              <div className="stat-label">Failures</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">
                {formatDuration(result.processing_time_ms)}
              </div>
              <div className="stat-label">Processing Time</div>
            </div>
          </div>

          {/* Import Failures Table */}
          {result.failures.length > 0 && (
            <div className="failures-section">
              <h3>
                Import Failures ({result.failure_count} total, showing first{' '}
                {result.failures.length})
              </h3>
              <div className="failures-table-wrapper">
                <table className="failures-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Source URL</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.failures.map(
                      (failure: SnapshotImportFailure, index: number) => (
                        <tr key={index}>
                          <td className="failure-index">
                            {failure.record_index}
                          </td>
                          <td className="failure-url">
                            {failure.source_url ? (
                              <a
                                href={failure.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {failure.source_url.length > 60
                                  ? failure.source_url.substring(0, 60) + '...'
                                  : failure.source_url}
                              </a>
                            ) : (
                              <span className="text-muted">-</span>
                            )}
                          </td>
                          <td className="failure-error">{failure.error}</td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Reindex Section */}
          <div className="reindex-section">
            <div className="reindex-header">
              <h3>Index Imported Versions</h3>
              {batchStatus && (
                <div className="index-status">
                  <span className="status-badge indexed">
                    {batchStatus.indexed_versions} indexed
                  </span>
                  <span className="status-badge pending">
                    {batchStatus.pending_versions} pending
                  </span>
                </div>
              )}
            </div>

            <p className="text-secondary">
              Imported versions have <code>is_indexed=false</code>. Index
              versions in batches of 25, or index all at once.
            </p>

            {reindexError && (
              <div className="alert alert-error" style={{ marginTop: '1rem' }}>
                <div className="alert-content">
                  <strong>Reindex Failed</strong>
                  <p>{reindexError}</p>
                </div>
                <button
                  className="alert-dismiss"
                  onClick={() => setReindexError(null)}
                >
                  &times;
                </button>
              </div>
            )}

            <div className="reindex-actions">
              <button
                className="btn btn-primary"
                onClick={() => handleReindex(false)}
                disabled={reindexing || batchStatus?.pending_versions === 0}
              >
                {reindexing ? (
                  <>
                    <span className="spinner"></span>
                    Reindexing...
                  </>
                ) : (
                  `Reindex Next 25${batchStatus?.pending_versions === 0 ? ' (None Pending)' : ''}`
                )}
              </button>
              <button
                className="btn btn-success"
                onClick={() => handleReindex(true)}
                disabled={reindexing || batchStatus?.pending_versions === 0}
              >
                {reindexing ? (
                  <>
                    <span className="spinner"></span>
                    Indexing All...
                  </>
                ) : (
                  `Index All${batchStatus?.pending_versions ? ` (${batchStatus.pending_versions})` : ''}`
                )}
              </button>
              <Link href="/operator/legal-corpus" className="btn btn-secondary">
                View Legal Corpus
              </Link>
            </div>

            {/* Reindex Result */}
            {reindexResult && (
              <div className="reindex-result">
                <div className="reindex-stats">
                  <span className="stat-badge">
                    <strong>{reindexResult.attempted}</strong> attempted
                  </span>
                  <span className="stat-badge success">
                    <strong>{reindexResult.indexed}</strong> indexed
                  </span>
                  {reindexResult.failed > 0 && (
                    <span className="stat-badge failed">
                      <strong>{reindexResult.failed}</strong> failed
                    </span>
                  )}
                </div>

                {/* Reindex Failures Table */}
                {reindexResult.failures.length > 0 && (
                  <div
                    className="failures-section"
                    style={{ marginTop: '1rem', paddingTop: '1rem' }}
                  >
                    <h4>Reindex Failures ({reindexResult.failed} total)</h4>
                    <div className="failures-table-wrapper">
                      <table className="failures-table">
                        <thead>
                          <tr>
                            <th>Version ID</th>
                            <th>Instrument ID</th>
                            <th>Error</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reindexResult.failures.map(
                            (failure: BatchReindexFailure, index: number) => (
                              <tr key={index}>
                                <td className="failure-id">
                                  <code>
                                    {failure.version_id.substring(0, 8)}...
                                  </code>
                                </td>
                                <td className="failure-id">
                                  <code>
                                    {failure.instrument_id.substring(0, 8)}...
                                  </code>
                                </td>
                                <td className="failure-error">
                                  {failure.error}
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{pageStyles}</style>
    </motion.div>
  );
}

const pageStyles = `
  .page-container {
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  .breadcrumb {
    font-size: 0.85rem;
    color: var(--text-secondary, #6b7280);
    margin-bottom: 0.5rem;
  }

  .breadcrumb a {
    color: var(--primary-color, #3b82f6);
    text-decoration: none;
  }

  .breadcrumb a:hover {
    text-decoration: underline;
  }

  .breadcrumb-separator {
    margin: 0 0.5rem;
    color: var(--text-muted, #9ca3af);
  }

  .page-header h1 {
    margin: 0 0 0.5rem 0;
  }

  .text-secondary {
    color: var(--text-secondary, #6b7280);
    margin: 0;
  }

  .text-muted {
    color: var(--text-muted, #9ca3af);
  }

  /* Alert */
  .alert {
    padding: 1rem 1.25rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .alert-error {
    background: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
  }

  .alert-content strong {
    display: block;
    margin-bottom: 0.25rem;
  }

  .alert-content p {
    margin: 0;
    font-size: 0.95rem;
  }

  .alert-dismiss {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    color: inherit;
    opacity: 0.7;
    padding: 0;
    line-height: 1;
  }

  .alert-dismiss:hover {
    opacity: 1;
  }

  /* Upload Card */
  .upload-card {
    background: var(--card-bg, #fff);
    border: 2px dashed var(--border-color, #e5e7eb);
    border-radius: 12px;
    padding: 3rem 2rem;
    text-align: center;
    margin-bottom: 2rem;
  }

  .upload-icon {
    color: var(--text-secondary, #6b7280);
    margin-bottom: 1rem;
  }

  .upload-content h2 {
    margin: 0 0 0.5rem 0;
    font-size: 1.25rem;
  }

  .upload-content p {
    max-width: 500px;
    margin: 0 auto 1.5rem;
  }

  .file-input-wrapper {
    margin-bottom: 1.5rem;
  }

  .file-input {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
  }

  .file-label {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    background: var(--secondary-bg, #f3f4f6);
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.95rem;
    color: var(--text-primary, #374151);
    transition: background-color 0.2s;
  }

  .file-label:hover {
    background: var(--secondary-hover, #e5e7eb);
  }

  .file-label.disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .file-selected {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--primary-color, #3b82f6);
  }

  /* Buttons */
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    text-decoration: none;
    transition: background-color 0.2s, opacity 0.2s;
  }

  .btn-primary {
    background: var(--primary-color, #3b82f6);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
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

  .btn-success {
    background: #16a34a;
    color: white;
  }

  .btn-success:hover:not(:disabled) {
    background: #15803d;
  }

  .btn-success:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-large {
    padding: 0.75rem 2rem;
    font-size: 1rem;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* Result Card */
  .result-card {
    background: var(--card-bg, #fff);
    border: 1px solid var(--border-color, #e5e7eb);
    border-radius: 12px;
    padding: 1.5rem;
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-color, #e5e7eb);
  }

  .result-icon {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .result-icon.success {
    background: #dcfce7;
    color: #166534;
  }

  .result-header h2 {
    margin: 0;
    font-size: 1.25rem;
  }

  .result-header code {
    background: var(--secondary-bg, #f3f4f6);
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  /* Stats Grid */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .stat-item {
    text-align: center;
    padding: 1rem;
    background: var(--secondary-bg, #f9fafb);
    border-radius: 8px;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: 0.25rem;
  }

  .stat-value.created {
    color: #166534;
  }

  .stat-value.existing {
    color: var(--text-secondary, #6b7280);
  }

  .stat-value.failed {
    color: #991b1b;
  }

  .stat-value.success {
    color: #166534;
  }

  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary, #6b7280);
  }

  /* Failures Section */
  .failures-section {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-color, #e5e7eb);
  }

  .failures-section h3,
  .failures-section h4 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    color: #991b1b;
  }

  .failures-table-wrapper {
    overflow-x: auto;
  }

  .failures-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }

  .failures-table th,
  .failures-table td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--border-color, #e5e7eb);
  }

  .failures-table th {
    font-weight: 500;
    color: var(--text-secondary, #6b7280);
    background: var(--secondary-bg, #f9fafb);
  }

  .failure-index,
  .failure-id {
    width: 100px;
    color: var(--text-muted, #9ca3af);
  }

  .failure-url {
    max-width: 300px;
    word-break: break-all;
  }

  .failure-url a {
    color: var(--primary-color, #3b82f6);
    text-decoration: none;
  }

  .failure-url a:hover {
    text-decoration: underline;
  }

  .failure-error {
    color: #991b1b;
  }

  /* Reindex Section */
  .reindex-section {
    margin-top: 1.5rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-color, #e5e7eb);
  }

  .reindex-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .reindex-header h3 {
    margin: 0;
    font-size: 1rem;
  }

  .index-status {
    display: flex;
    gap: 0.5rem;
  }

  .status-badge {
    font-size: 0.8rem;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-weight: 500;
  }

  .status-badge.indexed {
    background: #dcfce7;
    color: #166534;
  }

  .status-badge.pending {
    background: #fef3c7;
    color: #92400e;
  }

  .reindex-section code {
    background: var(--secondary-bg, #f3f4f6);
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
    font-size: 0.85rem;
  }

  .reindex-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
    flex-wrap: wrap;
  }

  .reindex-result {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--secondary-bg, #f9fafb);
    border-radius: 8px;
  }

  .reindex-stats {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .stat-badge {
    font-size: 0.85rem;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    background: white;
    border: 1px solid var(--border-color, #e5e7eb);
  }

  .stat-badge.success {
    background: #dcfce7;
    border-color: #bbf7d0;
    color: #166534;
  }

  .stat-badge.failed {
    background: #fef2f2;
    border-color: #fecaca;
    color: #991b1b;
  }

  @media (max-width: 600px) {
    .page-container {
      padding: 1rem;
    }

    .upload-card {
      padding: 2rem 1rem;
    }

    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .reindex-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .reindex-actions {
      flex-direction: column;
    }

    .reindex-actions .btn {
      width: 100%;
    }
  }
`;
