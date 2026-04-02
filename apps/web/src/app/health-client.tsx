'use client';

import { useEffect, useState } from 'react';
import { fetchHealth, getClientApiBaseUrl } from '@/lib/api';

interface HealthStatus {
  status: string;
}

/**
 * Client-side health check component.
 * Uses NEXT_PUBLIC_API_BASE_URL (http://localhost:8000 from browser).
 */
export function HealthClient() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const clientUrl = getClientApiBaseUrl();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const data = await fetchHealth('client');
        setHealth(data);
        setError(null);
        setLastChecked(new Date());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch health');
        setHealth(null);
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    // Poll every 10 seconds
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={styles.card}>
      <h2 style={styles.cardTitle}>Client-Side Health</h2>
      <p style={styles.cardSubtitle}>Fetched from browser (live polling)</p>
      <div style={styles.status}>
        {loading ? (
          <span style={styles.loading}>Checking...</span>
        ) : (
          <>
            <span
              style={{
                ...styles.indicator,
                backgroundColor:
                  health?.status === 'ok' ? 'var(--success)' : 'var(--error)',
              }}
            ></span>
            {error ? (
              <span style={styles.error}>Error: {error}</span>
            ) : (
              <span style={styles.success}>
                Status: {health?.status || 'unknown'}
              </span>
            )}
          </>
        )}
      </div>
      <p style={styles.endpoint}>URL: {clientUrl}/health</p>
      {lastChecked && (
        <p style={styles.timestamp}>
          Last checked: {lastChecked.toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}

const styles: { [key: string]: React.CSSProperties } = {
  card: {
    background: 'var(--background)',
    border: '1px solid #e5e7eb',
    borderRadius: '12px',
    padding: '1.5rem',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    textAlign: 'left',
  },
  cardTitle: {
    fontSize: '1.125rem',
    fontWeight: 600,
    marginBottom: '0.25rem',
  },
  cardSubtitle: {
    fontSize: '0.875rem',
    color: 'var(--muted)',
    marginBottom: '1rem',
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  indicator: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  loading: {
    color: 'var(--muted)',
    fontSize: '0.9rem',
  },
  success: {
    color: 'var(--success)',
    fontWeight: 500,
    fontSize: '0.9rem',
  },
  error: {
    color: 'var(--error)',
    fontWeight: 500,
    fontSize: '0.9rem',
  },
  endpoint: {
    fontSize: '0.75rem',
    color: 'var(--muted)',
    fontFamily: 'monospace',
    wordBreak: 'break-all',
  },
  timestamp: {
    fontSize: '0.7rem',
    color: 'var(--muted)',
    marginTop: '0.5rem',
  },
};
