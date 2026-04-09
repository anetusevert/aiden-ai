'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import { resolveApiUrl } from '@/lib/api';

type SeedAction = 'created' | 'already_exists' | 'refreshed' | 'wiped';

interface SeedResponsePayload {
  action?: SeedAction;
  cases_count?: number;
  clients_count?: number;
  documents_count?: number;
  notes_count?: number;
  events_count?: number;
  warnings?: string[];
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

function getStatusMessage(action: string, status: number): string {
  switch (status) {
    case 401:
      return `Could not ${action}. Your session has expired or the API did not accept your login cookie.`;
    case 403:
      return `Could not ${action}. Only admins can manage demo data.`;
    case 404:
      return `Could not ${action}. The demo-data API route is not reachable from this app.`;
    default:
      return `Could not ${action}. Request failed with status ${status}.`;
  }
}

async function getRequestErrorMessage(
  action: string,
  response: Response
): Promise<string> {
  const baseMessage = getStatusMessage(action, response.status);
  const detail = await readResponseDetail(response);

  if (!detail || baseMessage.toLowerCase().includes(detail.toLowerCase())) {
    return baseMessage;
  }

  return `${baseMessage} ${detail}`;
}

function getSeedNotice(
  payload: SeedResponsePayload | null,
  mode: 'load' | 'wipe'
): string {
  const clientsCount = payload?.clients_count ?? 0;
  const casesCount = payload?.cases_count ?? 0;
  const documentsCount = payload?.documents_count ?? 0;
  const notesCount = payload?.notes_count ?? 0;
  const eventsCount = payload?.events_count ?? 0;
  const warningSuffix = payload?.warnings?.length
    ? ` ${payload.warnings[0]}`
    : '';

  if (mode === 'load') {
    return `KSA demo data loaded: ${clientsCount} clients, ${casesCount} cases, ${documentsCount} documents, ${notesCount} notes, and ${eventsCount} timeline events.${warningSuffix}`;
  }

  return `KSA demo data removed: ${casesCount} cases, ${clientsCount} clients, ${documentsCount} documents, ${notesCount} notes, and ${eventsCount} timeline events.`;
}

export function DemoDataManager() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [summary, setSummary] = useState<SeedResponsePayload | null>(null);

  if (user?.role !== 'ADMIN') {
    return (
      <div className="settings-card">
        <h2 className="settings-card-title">Demo Data</h2>
        <p className="settings-notice">
          Admin access required to manage presentation datasets.
        </p>
      </div>
    );
  }

  const runAction = async (
    method: 'POST' | 'DELETE',
    mode: 'load' | 'wipe'
  ) => {
    setLoading(true);
    setError(null);
    setNotice(null);

    try {
      const response = await fetch(resolveApiUrl('/api/v1/seed/mock-cases'), {
        method,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(
          await getRequestErrorMessage(`${mode} demo data`, response)
        );
      }

      const data = (await response
        .json()
        .catch(() => null)) as SeedResponsePayload | null;
      setSummary(data);
      setNotice(getSeedNotice(data, mode));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `Could not ${mode === 'load' ? 'load' : 'wipe'} demo data.`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-card">
      <div className="settings-card-header">
        <div className="settings-card-icon">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M4 19h16" />
            <path d="M5 17V7l7-4 7 4v10" />
            <path d="M9 11h6" />
            <path d="M9 15h4" />
          </svg>
        </div>
        <div>
          <h2 className="settings-card-title">Demo Data</h2>
          <p className="settings-card-desc">
            Load or wipe a fully fictional, Saudi-specific law firm portfolio
            for presentations. Only demo-tagged records are affected.
          </p>
        </div>
      </div>

      <div className="settings-form">
        <div className="settings-alert" style={{ marginBottom: '1rem' }}>
          This dataset seeds nationwide KSA clients, active and closed matters,
          bilingual case records, and mock office files including PDF case
          documents.
        </div>

        {notice ? (
          <div className="settings-alert settings-alert-success">{notice}</div>
        ) : null}

        {error ? (
          <div className="settings-alert settings-alert-error">{error}</div>
        ) : null}

        {summary ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: '0.75rem',
              marginBottom: '1rem',
            }}
          >
            {[
              ['Clients', summary.clients_count ?? 0],
              ['Cases', summary.cases_count ?? 0],
              ['Documents', summary.documents_count ?? 0],
              ['Notes', summary.notes_count ?? 0],
              ['Events', summary.events_count ?? 0],
            ].map(([label, value]) => (
              <div
                key={label}
                className="detail-card"
                style={{ marginBottom: 0 }}
              >
                <div className="detail-label">{label}</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>
                  {value}
                </div>
              </div>
            ))}
          </div>
        ) : null}

        <div className="settings-actions">
          <button
            className="settings-btn settings-btn-primary"
            onClick={() => void runAction('POST', 'load')}
            disabled={loading}
          >
            {loading ? 'Working...' : 'Load Demo Data'}
          </button>
          <button
            className="settings-btn settings-btn-secondary"
            onClick={() => void runAction('DELETE', 'wipe')}
            disabled={loading}
          >
            {loading ? 'Working...' : 'Wipe Demo Data'}
          </button>
        </div>
      </div>
    </div>
  );
}
