'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { apiClient, ViewerInstrumentDetail } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';

interface InstrumentParams {
  params: {
    instrumentId: string;
  };
}

const INSTRUMENT_TYPES: Record<string, string> = {
  law: 'Law',
  federal_law: 'Federal Law',
  local_law: 'Local Law',
  decree: 'Decree',
  royal_decree: 'Royal Decree',
  regulation: 'Regulation',
  ministerial_resolution: 'Ministerial Resolution',
  circular: 'Circular',
  guideline: 'Guideline',
  directive: 'Directive',
  order: 'Order',
  other: 'Other',
};

export default function GlobalLegalInstrumentPage({
  params,
}: InstrumentParams) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { instrumentId } = params;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ViewerInstrumentDetail | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !instrumentId) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response =
          await apiClient.getGlobalLegalInstrumentDetail(instrumentId);
        setData(response);
      } catch (err) {
        if (err instanceof Error) {
          if (err.message.includes('403')) {
            setError(
              'Access denied: This instrument is not available in your workspace policy.'
            );
          } else if (err.message.includes('404')) {
            setError('Legal instrument not found.');
          } else {
            setError(err.message);
          }
        } else {
          setError('Failed to load instrument');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [authLoading, isAuthenticated, instrumentId]);

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const getTypeLabel = (type: string): string => {
    return INSTRUMENT_TYPES[type] || type;
  };

  if (authLoading || loading) {
    return (
      <div>
        <div className="page-breadcrumb">
          <Link href="/global-legal">Global Legal Library</Link>
          <span className="page-breadcrumb-separator">›</span>
          <span>Loading...</span>
        </div>
        <div className="loading">
          <span className="spinner" />
          <span style={{ marginLeft: 'var(--space-3)' }}>
            Loading instrument...
          </span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="page-breadcrumb">
          <Link href="/global-legal">Global Legal Library</Link>
          <span className="page-breadcrumb-separator">›</span>
          <span>Error</span>
        </div>
        <div className="page-header">
          <h1 className="page-title">Legal Instrument</h1>
        </div>
        <div className="alert alert-error">{error}</div>
        <div style={{ marginTop: 'var(--space-4)' }}>
          <Link href="/global-legal" className="btn btn-secondary">
            ← Back to Global Legal Library
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <motion.div {...fadeUp}>
      {/* Breadcrumb */}
      <div className="page-breadcrumb">
        <Link href="/global-legal">Global Legal Library</Link>
        <span className="page-breadcrumb-separator">›</span>
        <span>{data.title}</span>
      </div>

      {/* Header */}
      <div className="page-header">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="page-title">{data.title}</h1>
          <span className="badge badge-info">Global Law (Read-Only)</span>
          <span className="badge badge-muted">{data.jurisdiction}</span>
        </div>
        {data.title_ar && (
          <p
            className="page-subtitle"
            dir="rtl"
            style={{ fontSize: 'var(--text-lg)' }}
          >
            {data.title_ar}
          </p>
        )}
      </div>

      {/* Read-Only Disclaimer */}
      <div
        className="alert alert-info"
        style={{ marginBottom: 'var(--space-6)' }}
      >
        <strong>This is a global legal reference. Read-only.</strong>
        <p
          style={{ margin: 'var(--space-2) 0 0 0', fontSize: 'var(--text-sm)' }}
        >
          Public law reference — not workspace content. No editing or uploading
          permitted.
        </p>
      </div>

      {/* Metadata Card */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card-header">
          <h3 className="card-title">Instrument Details</h3>
        </div>
        <div className="card-body">
          <div className="grid grid-cols-2 gap-4" style={{ maxWidth: '800px' }}>
            <div>
              <label className="form-label">Jurisdiction</label>
              <div>
                <span className="badge badge-muted">{data.jurisdiction}</span>
              </div>
            </div>
            <div>
              <label className="form-label">Instrument Type</label>
              <div>{getTypeLabel(data.instrument_type)}</div>
            </div>
            <div>
              <label className="form-label">Publication Date</label>
              <div>{formatDate(data.published_at)}</div>
            </div>
            <div>
              <label className="form-label">Effective Date</label>
              <div>{formatDate(data.effective_at)}</div>
            </div>
            <div>
              <label className="form-label">Status</label>
              <div>
                <span
                  className={`badge ${data.status === 'active' ? 'badge-success' : 'badge-warning'}`}
                >
                  {data.status}
                </span>
              </div>
            </div>
            <div>
              <label className="form-label">Added to Corpus</label>
              <div>{formatDate(data.created_at)}</div>
            </div>
          </div>

          {/* Official Source Link */}
          {data.official_source_url && (
            <div style={{ marginTop: 'var(--space-6)' }}>
              <a
                href={data.official_source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
              >
                View Official Source ↗
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Versions */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Versions</h3>
          <span className="badge badge-muted">{data.versions.length}</span>
        </div>
        <div className="card-body">
          {data.versions.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state-description">No versions available.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Language</th>
                    <th>Indexed</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.versions.map(version => (
                    <tr key={version.id}>
                      <td>
                        <strong>{version.version_label}</strong>
                      </td>
                      <td>
                        <span className="badge badge-muted">
                          {version.language.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        {version.is_indexed ? (
                          <span className="badge badge-success">Indexed</span>
                        ) : (
                          <span className="badge badge-warning">
                            Not Indexed
                          </span>
                        )}
                      </td>
                      <td>{formatDate(version.created_at)}</td>
                      <td>
                        {version.is_indexed ? (
                          <Link
                            href={`/global-legal/${instrumentId}/versions/${version.id}`}
                            className="btn btn-sm btn-primary"
                          >
                            Read
                          </Link>
                        ) : (
                          <span className="text-muted text-sm">
                            Not available
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
