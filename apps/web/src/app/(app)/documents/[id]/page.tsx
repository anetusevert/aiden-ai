'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  DocumentWithVersionsAndIndexing,
  DocumentVersionSummaryWithIndexing,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { officeApi } from '@/lib/officeApi';
import { OfficeDocDetail } from './OfficeDocDetail';

type DocKind = 'loading' | 'office' | 'legal' | 'not-found';

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const { isAuthenticated, isLoading: authLoading, canEdit, user } = useAuth();

  const [docKind, setDocKind] = useState<DocKind>('loading');

  const [document, setDocument] =
    useState<DocumentWithVersionsAndIndexing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showVersionForm, setShowVersionForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const [reindexingVersions, setReindexingVersions] = useState<Set<string>>(
    new Set()
  );
  const [reindexMessage, setReindexMessage] = useState<{
    versionId: string;
    success: boolean;
    message: string;
  } | null>(null);

  const isAdmin = user?.role === 'ADMIN';

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;

    let cancelled = false;

    async function resolve() {
      try {
        await officeApi.getDocument(documentId);
        if (!cancelled) setDocKind('office');
      } catch {
        if (!cancelled) setDocKind('legal');
      }
    }

    void resolve();
    return () => { cancelled = true; };
  }, [authLoading, isAuthenticated, documentId]);

  const fetchDocument = useCallback(async () => {
    try {
      setLoading(true);
      const doc = await apiClient.getDocument(documentId);
      setDocument(doc);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
    if (!authLoading && isAuthenticated && docKind === 'legal') {
      fetchDocument();
    }
  }, [authLoading, isAuthenticated, router, fetchDocument, docKind]);

  const handleUploadVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);

    try {
      await apiClient.uploadVersion(documentId, file);
      setFile(null);
      setShowVersionForm(false);
      fetchDocument();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (versionId: string, fileName: string) => {
    try {
      const blob = await apiClient.downloadVersion(documentId, versionId);
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = fileName;
      window.document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      alert(
        'Download failed: ' +
          (err instanceof Error ? err.message : 'Unknown error')
      );
    }
  };

  const handleReindex = async (versionId: string) => {
    if (!isAdmin) return;

    setReindexingVersions(prev => new Set(prev).add(versionId));
    setReindexMessage(null);

    try {
      const response = await apiClient.reindexVersion(
        documentId,
        versionId,
        true
      );
      setReindexMessage({
        versionId,
        success: response.success,
        message: response.message || 'Reindexing started successfully',
      });
      setTimeout(() => {
        fetchDocument();
      }, 2000);
    } catch (err) {
      setReindexMessage({
        versionId,
        success: false,
        message: err instanceof Error ? err.message : 'Reindexing failed',
      });
    } finally {
      setReindexingVersions(prev => {
        const next = new Set(prev);
        next.delete(versionId);
        return next;
      });
    }
  };

  const renderIndexingStatus = (
    version: DocumentVersionSummaryWithIndexing
  ) => {
    if (version.is_indexed) {
      return (
        <div
          style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}
        >
          <span className="badge badge-success">Indexed</span>
          {version.indexed_at && (
            <span className="text-sm text-muted">
              {formatDate(version.indexed_at)}
            </span>
          )}
          {version.embedding_model && (
            <span className="text-sm text-muted">
              Model: {version.embedding_model}
            </span>
          )}
        </div>
      );
    }
    return <span className="badge badge-muted">Not indexed</span>;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (authLoading || docKind === 'loading') {
    return <div className="loading">Loading...</div>;
  }

  if (docKind === 'office') {
    return <OfficeDocDetail docId={documentId} />;
  }

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (error) {
    return (
      <div>
        <div className="alert alert-error">{error}</div>
        <Link href="/documents" className="btn btn-outline">
          Back to Documents
        </Link>
      </div>
    );
  }

  if (!document) {
    return (
      <div>
        <div className="alert alert-error">Document not found</div>
        <Link href="/documents" className="btn btn-outline">
          Back to Documents
        </Link>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      <div className="mb-4">
        <Link
          href="/documents"
          style={{ color: 'var(--muted)', fontSize: '0.875rem' }}
        >
          &larr; Back to Documents
        </Link>
      </div>

      <div className="page-header flex items-center justify-between">
        <div>
          <h1 className="page-title">{document.title}</h1>
          <p className="page-subtitle">Document details and version history</p>
        </div>
        {canEdit && (
          <button
            onClick={() => setShowVersionForm(!showVersionForm)}
            className="btn btn-primary"
          >
            {showVersionForm ? 'Cancel' : 'Upload New Version'}
          </button>
        )}
      </div>

      {showVersionForm && (
        <div className="card mb-4">
          <div className="card-header">
            <h3 className="card-title">Upload New Version</h3>
          </div>

          <form onSubmit={handleUploadVersion}>
            {uploadError && (
              <div className="alert alert-error">{uploadError}</div>
            )}

            <div className="form-group">
              <label htmlFor="versionFile" className="form-label">
                File *
              </label>
              <input
                id="versionFile"
                type="file"
                className="form-input"
                onChange={e => setFile(e.target.files?.[0] || null)}
                accept=".pdf,.doc,.docx,.txt"
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={uploading || !file}
            >
              {uploading ? 'Uploading...' : 'Upload Version'}
            </button>
          </form>
        </div>
      )}

      <div className="card mb-4">
        <div className="card-header">
          <h3 className="card-title">Metadata</h3>
        </div>

        <div className="grid grid-2">
          <div>
            <p className="text-sm text-muted mb-2">Document Type</p>
            <span className="badge badge-info">{document.document_type}</span>
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Jurisdiction</p>
            <span>{document.jurisdiction}</span>
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Language</p>
            <span>{document.language}</span>
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Confidentiality</p>
            <span className="badge badge-warning">
              {document.confidentiality}
            </span>
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Document ID</p>
            <code className="mono">{document.id}</code>
          </div>
          <div>
            <p className="text-sm text-muted mb-2">Created</p>
            <span>{formatDate(document.created_at)}</span>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div
          className="card-header"
          style={{ margin: '1.5rem 1.5rem 0', padding: 0 }}
        >
          <h3 className="card-title">Version History</h3>
        </div>

        {reindexMessage && (
          <div
            className={`alert ${reindexMessage.success ? 'alert-success' : 'alert-error'}`}
            style={{ margin: '1rem 1.5rem 0' }}
          >
            {reindexMessage.message}
          </div>
        )}

        {document.versions.length === 0 ? (
          <p
            className="text-muted"
            style={{ padding: '1.5rem', textAlign: 'center' }}
          >
            No versions available
          </p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Version</th>
                <th>File Name</th>
                <th>Size</th>
                <th>Indexing Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {document.versions.map((version, index) => (
                <tr key={version.id}>
                  <td>
                    <span className="badge badge-info">
                      v{version.version_number}
                    </span>
                    {index === 0 && (
                      <span
                        className="badge badge-success"
                        style={{ marginLeft: '0.5rem' }}
                      >
                        Latest
                      </span>
                    )}
                  </td>
                  <td>{version.file_name}</td>
                  <td>{formatBytes(version.size_bytes)}</td>
                  <td>{renderIndexingStatus(version)}</td>
                  <td className="text-sm text-muted">
                    {formatDate(version.created_at)}
                  </td>
                  <td>
                    <div
                      style={{
                        display: 'flex',
                        gap: '0.5rem',
                        flexWrap: 'wrap',
                      }}
                    >
                      <button
                        onClick={() =>
                          handleDownload(version.id, version.file_name)
                        }
                        className="btn btn-sm btn-outline"
                      >
                        Download
                      </button>
                      <Link
                        href={`/contract-review?documentId=${document.id}&versionId=${version.id}&title=${encodeURIComponent(document.title)}`}
                        className={`btn btn-sm ${canEdit ? 'btn-primary' : 'btn-outline'}`}
                        style={{
                          pointerEvents: canEdit ? 'auto' : 'none',
                          opacity: canEdit ? 1 : 0.5,
                        }}
                        title={
                          canEdit
                            ? 'Run contract review'
                            : 'VIEWER role cannot run reviews'
                        }
                      >
                        Review
                      </Link>
                      <Link
                        href={`/clause-redlines?documentId=${document.id}&versionId=${version.id}&title=${encodeURIComponent(document.title)}`}
                        className={`btn btn-sm ${canEdit ? 'btn-outline' : 'btn-outline'}`}
                        style={{
                          pointerEvents: canEdit ? 'auto' : 'none',
                          opacity: canEdit ? 1 : 0.5,
                        }}
                        title={
                          canEdit
                            ? 'Run clause redlines analysis'
                            : 'VIEWER role cannot run redlines'
                        }
                      >
                        Redlines
                      </Link>
                      {isAdmin && (
                        <button
                          onClick={() => handleReindex(version.id)}
                          className="btn btn-sm btn-outline"
                          disabled={reindexingVersions.has(version.id)}
                          title="Reindex this version (replace existing embeddings)"
                        >
                          {reindexingVersions.has(version.id)
                            ? 'Reindexing...'
                            : 'Reindex'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </motion.div>
  );
}
