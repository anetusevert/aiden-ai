'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  ViewerInstrumentListItem,
  ViewerInstrumentListResponse,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';
import { WorkflowLaunchBanner } from '@/components/workflows/WorkflowLaunchBanner';

const JURISDICTIONS = [
  'UAE',
  'DIFC',
  'ADGM',
  'KSA',
  'OMAN',
  'BAHRAIN',
  'QATAR',
  'KUWAIT',
];
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

export default function GlobalLegalPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<ViewerInstrumentListResponse | null>(null);

  // Filters
  const [jurisdictionFilter, setJurisdictionFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  // Pagination
  const [offset, setOffset] = useState(0);
  const limit = 20;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.listGlobalLegalInstruments({
          limit,
          offset,
          jurisdiction: jurisdictionFilter || undefined,
          instrument_type: typeFilter || undefined,
        });
        setData(response);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('Failed to load global legal library');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [authLoading, isAuthenticated, offset, jurisdictionFilter, typeFilter]);

  const handleFilterChange = () => {
    setOffset(0); // Reset to first page when filter changes
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const getTypeLabel = (type: string): string => {
    const found = INSTRUMENT_TYPES.find(t => t.value === type);
    return found ? found.label : type;
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
      <WorkflowLaunchBanner currentRoute="/global-legal" />

      {/* Header */}
      <div className="page-header">
        <div className="flex items-center gap-3">
          <h1 className="page-title">Global Legal Library</h1>
          <span className="badge badge-info">Read-Only</span>
        </div>
        <p className="page-subtitle">
          Browse the global legal corpus. Public law reference — not workspace
          content.
        </p>
      </div>

      {/* Read-Only Disclaimer */}
      <div
        className="alert alert-info"
        style={{ marginBottom: 'var(--space-6)' }}
      >
        <strong>Global Law (Read-Only)</strong>
        <p
          style={{ margin: 'var(--space-2) 0 0 0', fontSize: 'var(--text-sm)' }}
        >
          This is a global legal reference. These laws are maintained by the
          platform and filtered by your workspace policy.
        </p>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
        <div className="card-body">
          <div className="flex flex-wrap gap-4">
            <div
              className="form-group"
              style={{ minWidth: '200px', margin: 0 }}
            >
              <label className="form-label">Jurisdiction</label>
              <select
                className="form-select"
                value={jurisdictionFilter}
                onChange={e => {
                  setJurisdictionFilter(e.target.value);
                  handleFilterChange();
                }}
              >
                <option value="">All Jurisdictions</option>
                {JURISDICTIONS.map(j => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>

            <div
              className="form-group"
              style={{ minWidth: '200px', margin: 0 }}
            >
              <label className="form-label">Instrument Type</label>
              <select
                className="form-select"
                value={typeFilter}
                onChange={e => {
                  setTypeFilter(e.target.value);
                  handleFilterChange();
                }}
              >
                <option value="">All Types</option>
                {INSTRUMENT_TYPES.map(t => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="loading">
          <span className="spinner" />
          <span style={{ marginLeft: 'var(--space-3)' }}>
            Loading instruments...
          </span>
        </div>
      )}

      {/* Error */}
      {error && <div className="alert alert-error">{error}</div>}

      {/* Results */}
      {!loading && !error && data && (
        <>
          {data.items.length === 0 ? (
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
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
              </div>
              <p className="empty-state-title">No Legal Instruments Found</p>
              <p className="empty-state-description">
                {jurisdictionFilter || typeFilter
                  ? 'No instruments match your filters. Try adjusting your selection.'
                  : 'No global legal instruments are available for your workspace policy.'}
              </p>
            </div>
          ) : (
            <>
              {/* Results count */}
              <div
                style={{
                  marginBottom: 'var(--space-4)',
                  color: 'var(--text-secondary)',
                }}
              >
                Showing {data.items.length} of {data.total} instruments
              </div>

              {/* Table */}
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Title</th>
                      <th>Jurisdiction</th>
                      <th>Type</th>
                      <th>Effective Date</th>
                      <th>Latest Version</th>
                      <th></th>
                    </tr>
                  </thead>
                  <motion.tbody
                    variants={staggerContainer}
                    initial="hidden"
                    animate="visible"
                  >
                    {data.items.map((item: ViewerInstrumentListItem) => (
                      <motion.tr variants={staggerItem} key={item.id}>
                        <td>
                          <Link
                            href={`/global-legal/${item.id}`}
                            className="link"
                          >
                            {item.title}
                          </Link>
                          {item.title_ar && (
                            <div className="text-sm text-muted" dir="rtl">
                              {item.title_ar}
                            </div>
                          )}
                        </td>
                        <td>
                          <span className="badge badge-muted">
                            {item.jurisdiction}
                          </span>
                        </td>
                        <td>{getTypeLabel(item.instrument_type)}</td>
                        <td>{formatDate(item.effective_at)}</td>
                        <td>{formatDate(item.latest_version_date)}</td>
                        <td>
                          {item.official_source_url && (
                            <a
                              href={item.official_source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-sm btn-secondary"
                              title="View Official Source"
                            >
                              Official ↗
                            </a>
                          )}
                        </td>
                      </motion.tr>
                    ))}
                  </motion.tbody>
                </table>
              </div>

              {/* Pagination */}
              {data.total > limit && (
                <div
                  className="flex justify-center gap-2"
                  style={{ marginTop: 'var(--space-6)' }}
                >
                  <button
                    className="btn btn-secondary"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                  >
                    Previous
                  </button>
                  <span
                    style={{
                      padding: 'var(--space-2) var(--space-4)',
                      alignSelf: 'center',
                    }}
                  >
                    Page {Math.floor(offset / limit) + 1} of{' '}
                    {Math.ceil(data.total / limit)}
                  </span>
                  <button
                    className="btn btn-secondary"
                    disabled={offset + limit >= data.total}
                    onClick={() => setOffset(offset + limit)}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </motion.div>
  );
}
