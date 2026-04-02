'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  apiClient,
  DocumentWithLatestVersionAndIndexing,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

type DocumentType = 'contract' | 'policy' | 'memo' | 'regulatory' | 'other';
type Jurisdiction = 'UAE' | 'DIFC' | 'ADGM' | 'KSA';
type Language = 'en' | 'ar' | 'mixed';
type Confidentiality =
  | 'public'
  | 'internal'
  | 'confidential'
  | 'highly_confidential';

export default function DocumentsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, canEdit } = useAuth();
  const [documents, setDocuments] = useState<
    DocumentWithLatestVersionAndIndexing[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType>('contract');
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>('UAE');
  const [language, setLanguage] = useState<Language>('en');
  const [confidentiality, setConfidentiality] =
    useState<Confidentiality>('internal');

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.listDocuments();
      setDocuments(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (!authLoading && isAuthenticated) {
      fetchDocuments();
    }
  }, [authLoading, isAuthenticated, router, fetchDocuments]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(false);

    try {
      await apiClient.uploadDocument(file, {
        title,
        document_type: documentType,
        jurisdiction,
        language,
        confidentiality,
      });

      setUploadSuccess(true);
      setFile(null);
      setTitle('');

      // Refresh list and close form after delay
      setTimeout(() => {
        setShowUploadForm(false);
        setUploadSuccess(false);
        fetchDocuments();
      }, 1500);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getIndexStatus = (doc: DocumentWithLatestVersionAndIndexing) => {
    if (!doc.latest_version) return { status: 'none', label: 'No version' };
    if (doc.latest_version.is_indexed)
      return { status: 'indexed', label: 'Indexed' };
    return { status: 'pending', label: 'Pending' };
  };

  if (authLoading) {
    return (
      <div className="loading">
        <span className="spinner" />
        <span style={{ marginLeft: 'var(--space-3)' }}>Loading...</span>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h1 className="page-title">Document Vault</h1>
            <p className="page-subtitle">
              Securely manage and index your legal documents
            </p>
          </div>
          {canEdit && (
            <button
              onClick={() => {
                setShowUploadForm(!showUploadForm);
                setUploadError(null);
                setUploadSuccess(false);
              }}
              className={`btn ${showUploadForm ? 'btn-outline' : 'btn-primary'}`}
            >
              {showUploadForm ? 'Cancel' : 'Upload Document'}
            </button>
          )}
        </div>
      </div>

      {/* View-only notice */}
      {!canEdit && (
        <div className="alert alert-neutral">
          You have read-only access to this workspace. Contact an administrator
          to request edit permissions.
        </div>
      )}

      {/* Upload Form */}
      {showUploadForm && (
        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="card-header">
            <h3 className="card-title">Upload New Document</h3>
          </div>

          <form onSubmit={handleUpload}>
            {uploadError && (
              <div className="alert alert-error">{uploadError}</div>
            )}
            {uploadSuccess && (
              <div className="alert alert-success">
                Document uploaded successfully. Indexing will begin shortly.
              </div>
            )}

            <div className="form-group">
              <label htmlFor="file" className="form-label">
                Document File
              </label>
              <input
                id="file"
                type="file"
                className="form-input"
                onChange={e => setFile(e.target.files?.[0] || null)}
                accept=".pdf,.doc,.docx,.txt"
                required
                disabled={uploading}
              />
              <span className="form-hint">
                Supported formats: PDF, Word (.doc, .docx), Plain text
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="title" className="form-label">
                Document Title
              </label>
              <input
                id="title"
                type="text"
                className="form-input"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="Enter a descriptive title"
                required
                disabled={uploading}
              />
            </div>

            <div className="form-row form-row-2">
              <div className="form-group">
                <label htmlFor="docType" className="form-label">
                  Document Type
                </label>
                <select
                  id="docType"
                  className="form-select"
                  value={documentType}
                  onChange={e =>
                    setDocumentType(e.target.value as DocumentType)
                  }
                  disabled={uploading}
                >
                  <option value="contract">Contract</option>
                  <option value="policy">Policy</option>
                  <option value="memo">Memo</option>
                  <option value="regulatory">Regulatory</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="docJurisdiction" className="form-label">
                  Jurisdiction
                </label>
                <select
                  id="docJurisdiction"
                  className="form-select"
                  value={jurisdiction}
                  onChange={e =>
                    setJurisdiction(e.target.value as Jurisdiction)
                  }
                  disabled={uploading}
                >
                  <option value="UAE">UAE</option>
                  <option value="DIFC">DIFC</option>
                  <option value="ADGM">ADGM</option>
                  <option value="KSA">KSA</option>
                </select>
              </div>
            </div>

            <div className="form-row form-row-2">
              <div className="form-group">
                <label htmlFor="docLanguage" className="form-label">
                  Language
                </label>
                <select
                  id="docLanguage"
                  className="form-select"
                  value={language}
                  onChange={e => setLanguage(e.target.value as Language)}
                  disabled={uploading}
                >
                  <option value="en">English</option>
                  <option value="ar">Arabic</option>
                  <option value="mixed">Mixed</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="docConfidentiality" className="form-label">
                  Confidentiality
                </label>
                <select
                  id="docConfidentiality"
                  className="form-select"
                  value={confidentiality}
                  onChange={e =>
                    setConfidentiality(e.target.value as Confidentiality)
                  }
                  disabled={uploading}
                >
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="highly_confidential">
                    Highly Confidential
                  </option>
                </select>
              </div>
            </div>

            <div
              className="card-footer"
              style={{
                marginTop: 'var(--space-4)',
                paddingTop: 'var(--space-4)',
                borderTop: '1px solid var(--border)',
                justifyContent: 'flex-start',
              }}
            >
              <button
                type="submit"
                className="btn btn-primary"
                disabled={uploading || !file}
              >
                {uploading ? (
                  <>
                    <span className="spinner spinner-sm" />
                    Uploading...
                  </>
                ) : (
                  'Upload Document'
                )}
              </button>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setShowUploadForm(false)}
                disabled={uploading}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Error State */}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Loading State */}
      {loading ? (
        <div className="card">
          <div style={{ padding: 'var(--space-4)' }}>
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="skeleton-row">
                <div
                  className="skeleton skeleton-text"
                  style={{ width: '30%' }}
                />
                <div
                  className="skeleton skeleton-text"
                  style={{ width: '10%' }}
                />
                <div
                  className="skeleton skeleton-text"
                  style={{ width: '10%' }}
                />
                <div
                  className="skeleton skeleton-text"
                  style={{ width: '8%' }}
                />
                <div
                  className="skeleton skeleton-text"
                  style={{ width: '8%' }}
                />
              </div>
            ))}
          </div>
        </div>
      ) : documents.length === 0 ? (
        /* Empty State */
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
            </div>
            <h3 className="empty-state-title">No documents yet</h3>
            <p className="empty-state-description">
              {canEdit
                ? 'Upload your first document to begin building your legal knowledge base.'
                : 'No documents have been uploaded to this workspace yet.'}
            </p>
            {canEdit && (
              <button
                onClick={() => setShowUploadForm(true)}
                className="btn btn-primary"
              >
                Upload Document
              </button>
            )}
          </div>
        </div>
      ) : (
        /* Documents Table */
        <div className="card card-flush">
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Jurisdiction</th>
                  <th>Language</th>
                  <th>Version</th>
                  <th>Index Status</th>
                  <th>Size</th>
                  <th>Created</th>
                </tr>
              </thead>
              <motion.tbody
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {documents.map(doc => {
                  const indexStatus = getIndexStatus(doc);
                  return (
                    <motion.tr key={doc.id} variants={staggerItem}>
                      <td>
                        <Link
                          href={`/documents/${doc.id}`}
                          className="doc-title-link"
                        >
                          {doc.title}
                        </Link>
                      </td>
                      <td>
                        <span className="badge badge-muted badge-normal-case">
                          {doc.document_type}
                        </span>
                      </td>
                      <td className="text-sm">{doc.jurisdiction}</td>
                      <td className="text-sm">
                        {doc.language === 'en'
                          ? 'English'
                          : doc.language === 'ar'
                            ? 'Arabic'
                            : 'Mixed'}
                      </td>
                      <td className="text-sm">
                        {doc.latest_version
                          ? `v${doc.latest_version.version_number}`
                          : '—'}
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            indexStatus.status === 'indexed'
                              ? 'badge-success'
                              : indexStatus.status === 'pending'
                                ? 'badge-warning'
                                : 'badge-muted'
                          }`}
                        >
                          {indexStatus.label}
                        </span>
                      </td>
                      <td className="text-sm text-muted">
                        {doc.latest_version
                          ? formatBytes(doc.latest_version.size_bytes)
                          : '—'}
                      </td>
                      <td className="text-sm text-muted">
                        {formatDate(doc.created_at)}
                      </td>
                    </motion.tr>
                  );
                })}
              </motion.tbody>
            </table>
          </div>

          {/* Table Footer */}
          <div className="table-footer">
            <span className="text-sm text-muted">
              {documents.length} document{documents.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      )}
    </motion.div>
  );
}
