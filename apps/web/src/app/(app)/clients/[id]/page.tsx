'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { resolveApiUrl } from '@/lib/api';
import { reportScreenContext } from '@/lib/screenContext';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

const TYPE_COLORS: Record<string, string> = {
  individual: 'rgba(255,255,255,0.9)',
  company: 'rgba(255,255,255,0.85)',
  organisation: 'rgba(255,255,255,0.8)',
};
const PRIORITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#94a3b8',
  low: '#64748b',
};

interface ClientDetailError {
  title: string;
  message: string;
}

async function readResponseDetail(response: Response): Promise<string | null> {
  try {
    const data = await response.json();
    const detail = data?.detail;

    if (typeof detail === 'string' && detail.trim()) {
      return detail.trim();
    }

    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = detail.message;
      if (typeof message === 'string' && message.trim()) {
        return message.trim();
      }
    }
  } catch {
    try {
      const text = await response.text();
      if (text.trim()) {
        return text.trim();
      }
    } catch {
      /* */
    }
  }

  return null;
}

function getClientDetailError(
  status: number,
  detail: string | null
): ClientDetailError {
  if (status === 401) {
    return {
      title: 'Session expired',
      message:
        'Your login session is no longer valid for the API. Sign in again and retry the client detail page.',
    };
  }

  if (status === 403) {
    return {
      title: 'Access denied',
      message:
        detail ||
        'Your account is authenticated, but it does not have permission to load this client.',
    };
  }

  if (status === 404) {
    if (detail === 'Client not found') {
      return {
        title: 'Client not found',
        message:
          'This client does not exist or is not visible to your current organisation.',
      };
    }

    return {
      title: 'Client API route not found',
      message:
        'The deployed API returned 404 for the client detail route. Check `NEXT_PUBLIC_API_BASE_URL` and confirm the API is serving `/api/v1/clients/{client_id}`.',
    };
  }

  if (status >= 500) {
    return {
      title: 'API error',
      message:
        detail ||
        `The API returned status ${status} while loading this client detail page.`,
    };
  }

  return {
    title: 'Client request failed',
    message:
      detail || `The API returned status ${status} while loading this client.`,
  };
}

function getClientNetworkError(requestUrl: string): ClientDetailError {
  const isCrossOrigin = /^https?:\/\//.test(requestUrl);
  return {
    title: 'Client request blocked',
    message: isCrossOrigin
      ? 'The browser could not read the API response. On Railway, this usually means `CORS_ORIGINS_STR` does not include the deployed web origin exactly, or `NEXT_PUBLIC_API_BASE_URL` points at the wrong API host.'
      : 'The browser could not reach the API. Check your network connection and the deployed API route.',
  };
}

export default function ClientDetailPage() {
  const params = useParams<{ id: string }>();
  const { navigateTo } = useNavigation();
  const [client, setClient] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState<ClientDetailError | null>(null);
  const clientUrl = resolveApiUrl(`/api/v1/clients/${params.id}`);

  useEffect(() => {
    let cancelled = false;

    const loadClient = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(clientUrl, {
          credentials: 'include',
        });

        if (!response.ok) {
          const detail = await readResponseDetail(response);
          if (!cancelled) {
            setClient(null);
            setError(getClientDetailError(response.status, detail));
          }
          return;
        }

        const data = await response.json();
        if (!cancelled) {
          setClient(data);
        }
      } catch {
        if (!cancelled) {
          setClient(null);
          setError(getClientNetworkError(clientUrl));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadClient();

    return () => {
      cancelled = true;
    };
  }, [clientUrl]);

  useEffect(() => {
    if (!client) return;
    reportScreenContext({
      route: `/clients/${params.id}`,
      page_title: `Client: ${client.display_name}`,
      document: null,
      ui_state: { client_id: params.id, client_type: client.client_type },
    });
  }, [client, params.id]);

  const handleCaseClick = (caseItem: any) => {
    fetch(resolveApiUrl(`/api/v1/cases/${caseItem.id}/set-active`), {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {});
    navigateTo(`/cases/${caseItem.id}`);
  };

  if (loading)
    return (
      <div
        className="page-container"
        style={{
          height: '100%',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div className="client-detail-header">
          <div className="skeleton-group" style={{ gap: 8 }}>
            <div
              className="skeleton-line skeleton-line-xl"
              style={{ width: '40%' }}
            />
            <div className="skeleton-line" style={{ width: '20%' }} />
          </div>
        </div>
        <div
          style={{
            flex: 1,
            display: 'flex',
            gap: 'var(--space-6)',
            padding: 'var(--space-4)',
          }}
        >
          <div
            style={{
              width: '35%',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-4)',
            }}
          >
            <div className="skeleton-card" style={{ height: 160 }} />
            <div className="skeleton-card" style={{ height: 200 }} />
          </div>
          <div style={{ flex: 1 }}>
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton-row">
                <div className="skeleton-dot" />
                <div className="skeleton-group">
                  <div
                    className="skeleton-line"
                    style={{ width: `${70 - i * 10}%` }}
                  />
                  <div
                    className="skeleton-line skeleton-line-sm"
                    style={{ width: '30%' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  if (!client)
    return (
      <div className="page-empty">
        {error ? (
          <div style={{ maxWidth: 560 }}>
            <div className="alert alert-error" style={{ marginBottom: 16 }}>
              <strong>{error.title}</strong>
              <div>{error.message}</div>
            </div>
          </div>
        ) : (
          <div className="page-empty-icon">
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        )}
        <h3>{error?.title ?? 'Client not found'}</h3>
        {error ? (
          <p>{error.message}</p>
        ) : (
          <p>This client could not be found.</p>
        )}
        <button
          type="button"
          className="btn btn-outline"
          onClick={() => navigateTo('/clients')}
          style={{ marginTop: 12 }}
        >
          Back to Clients
        </button>
      </div>
    );

  const filteredCases = statusFilter
    ? (client.cases ?? []).filter((c: any) => c.status === statusFilter)
    : (client.cases ?? []);

  return (
    <motion.div
      className="page-container"
      {...fadeUp}
      style={{
        height: '100%',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div className="client-detail-header">
        <div
          className="client-detail-icon"
          style={{ color: TYPE_COLORS[client.client_type] }}
        >
          {client.client_type === 'company'
            ? '🏢'
            : client.client_type === 'organisation'
              ? '🌐'
              : '👤'}
        </div>
        <div className="client-detail-name-block">
          <h1 className="client-detail-name">{client.display_name}</h1>
          <div className="client-detail-badges">
            <span className="badge badge-type">{client.client_type}</span>
            <span
              className={`badge ${client.is_active ? 'badge-active' : 'badge-inactive'}`}
            >
              {client.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </div>

      <div
        className="client-detail-body"
        style={{
          flex: 1,
          display: 'flex',
          gap: 'var(--space-6)',
          overflow: 'hidden',
          padding: 'var(--space-4)',
        }}
      >
        <div
          className="client-detail-left"
          style={{ width: '35%', overflow: 'auto' }}
        >
          {(client.email || client.phone || client.address) && (
            <div className="detail-card">
              <h3 className="detail-card-title">Contact</h3>
              {client.email && (
                <div className="detail-field">
                  <span className="detail-label">Email</span>
                  <span>{client.email}</span>
                </div>
              )}
              {client.phone && (
                <div className="detail-field">
                  <span className="detail-label">Phone</span>
                  <span>{client.phone}</span>
                </div>
              )}
              {client.address && (
                <div className="detail-field">
                  <span className="detail-label">Address</span>
                  <span>{client.address}</span>
                </div>
              )}
            </div>
          )}

          <div className="detail-card">
            <h3 className="detail-card-title">Identity</h3>
            {client.national_id && (
              <div className="detail-field">
                <span className="detail-label">National ID</span>
                <span>{client.national_id}</span>
              </div>
            )}
            {client.nationality && (
              <div className="detail-field">
                <span className="detail-label">Nationality</span>
                <span>{client.nationality}</span>
              </div>
            )}
            {client.cr_number && (
              <div className="detail-field">
                <span className="detail-label">CR Number</span>
                <span>{client.cr_number}</span>
              </div>
            )}
            {client.vat_number && (
              <div className="detail-field">
                <span className="detail-label">VAT Number</span>
                <span>{client.vat_number}</span>
              </div>
            )}
            {client.trade_name && (
              <div className="detail-field">
                <span className="detail-label">Trade Name</span>
                <span>{client.trade_name}</span>
              </div>
            )}
            {client.sector && (
              <div className="detail-field">
                <span className="detail-label">Sector</span>
                <span>{client.sector}</span>
              </div>
            )}
            {client.org_type && (
              <div className="detail-field">
                <span className="detail-label">Org Type</span>
                <span>{client.org_type}</span>
              </div>
            )}
          </div>

          {client.notes && (
            <div className="detail-card">
              <h3 className="detail-card-title">Notes</h3>
              <p className="detail-notes">{client.notes}</p>
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary btn-full"
            onClick={() => navigateTo(`/cases?new=true&client_id=${client.id}`)}
          >
            + New Case for this Client
          </button>
        </div>

        <div
          className="client-detail-right"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div className="cases-section-header">
            <h2>Cases ({client.case_count})</h2>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={() =>
                navigateTo(`/cases?new=true&client_id=${client.id}`)
              }
            >
              + New Case
            </button>
          </div>
          <div
            className="page-filter-chips"
            style={{ marginBottom: 'var(--space-3)' }}
          >
            {['', 'active', 'on_hold', 'closed'].map(s => (
              <button
                key={s || 'all'}
                type="button"
                className={`chip${statusFilter === s ? ' chip-active' : ''}`}
                onClick={() => setStatusFilter(s)}
              >
                {s || 'All'}
              </button>
            ))}
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {filteredCases.map((c: any) => (
                <motion.div
                  key={c.id}
                  variants={staggerItem}
                  className="case-row"
                  onClick={() => handleCaseClick(c)}
                >
                  <span
                    className="case-row-priority"
                    style={{ backgroundColor: PRIORITY_COLORS[c.priority] }}
                  />
                  <span className="case-row-title">{c.title}</span>
                  <span
                    className={`badge badge-status badge-status-${c.status}`}
                  >
                    {c.status}
                  </span>
                  {c.next_deadline && (
                    <span className="case-row-deadline">{c.next_deadline}</span>
                  )}
                </motion.div>
              ))}
            </motion.div>
            {filteredCases.length === 0 && (
              <div className="page-empty">
                <p>No cases</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
