'use client';

import { useEffect, useState, useCallback } from 'react';
import { getApiBaseUrl } from '@/lib/api';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

interface TwinProfile {
  id?: string;
  profile?: Record<string, unknown>;
  preferences?: Record<string, unknown>;
  work_patterns?: Record<string, unknown>;
  drafting_style?: Record<string, unknown>;
  review_priorities?: Record<string, unknown>;
  learned_corrections?: Record<string, unknown>;
  [key: string]: unknown;
}

const SECTIONS = [
  { key: 'profile', label: 'Profile' },
  { key: 'preferences', label: 'Preferences' },
  { key: 'work_patterns', label: 'Work Patterns' },
  { key: 'drafting_style', label: 'Drafting Style' },
  { key: 'review_priorities', label: 'Review Priorities' },
  { key: 'learned_corrections', label: 'Learned Corrections' },
] as const;

export default function TwinProfilePage() {
  const [twin, setTwin] = useState<TwinProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set(['profile']));

  const loadTwin = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/twin/me`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTwin(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTwin();
  }, [loadTwin]);

  const toggleSection = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const renderValue = (val: unknown): React.ReactNode => {
    if (val === null || val === undefined) {
      return (
        <span style={{ color: 'var(--foreground-muted)', fontStyle: 'italic' }}>
          Not set
        </span>
      );
    }
    if (typeof val === 'boolean') {
      return (
        <span style={{ color: val ? 'var(--success)' : 'var(--error)' }}>
          {val ? 'Yes' : 'No'}
        </span>
      );
    }
    if (typeof val === 'object') {
      return (
        <pre
          style={{
            background: 'var(--secondary-light)',
            padding: 'var(--space-2) var(--space-3)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-sm)',
            fontFamily: 'var(--font-family-mono)',
            overflow: 'auto',
            margin: 0,
          }}
        >
          {JSON.stringify(val, null, 2)}
        </pre>
      );
    }
    return String(val);
  };

  return (
    <motion.div className="page-container" {...fadeUp}>
      <div className="page-header">
        <div>
          <h1 className="page-title">My AI Profile</h1>
          <p className="page-subtitle">
            How Amin understands your work style and preferences
          </p>
        </div>
      </div>

      {loading && (
        <div
          className="card"
          style={{ textAlign: 'center', padding: 'var(--space-8)' }}
        >
          <span className="spinner spinner-lg" />
          <p
            style={{
              marginTop: 'var(--space-3)',
              color: 'var(--foreground-muted)',
            }}
          >
            Loading profile…
          </p>
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          <p>{error}</p>
          <button className="btn btn-sm" onClick={loadTwin}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && !twin && (
        <div
          className="card"
          style={{ textAlign: 'center', padding: 'var(--space-12)' }}
        >
          <h3 style={{ marginBottom: 'var(--space-2)' }}>No AI profile yet</h3>
          <p style={{ color: 'var(--foreground-muted)' }}>
            Your AI profile is built as you interact with Amin. Start a
            conversation to begin.
          </p>
        </div>
      )}

      {!loading && !error && twin && (
        <motion.div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-4)',
          }}
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {SECTIONS.map(({ key, label }) => {
            const data = twin[key];
            const isOpen = expanded.has(key);
            const isEmpty =
              !data ||
              (typeof data === 'object' &&
                Object.keys(data as object).length === 0);

            return (
              <motion.div
                key={key}
                className="card"
                style={{ overflow: 'hidden' }}
                variants={staggerItem}
              >
                <button
                  onClick={() => toggleSection(key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: 'var(--space-4)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--foreground)',
                    fontFamily: 'var(--font-heading)',
                    fontSize: 'var(--text-md)',
                    fontWeight: 'var(--font-semibold)',
                  }}
                >
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--space-2)',
                    }}
                  >
                    {label}
                    {isEmpty && (
                      <span
                        style={{
                          fontSize: 'var(--text-xs)',
                          color: 'var(--foreground-muted)',
                          fontWeight: 'normal',
                        }}
                      >
                        (empty)
                      </span>
                    )}
                  </span>
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    style={{
                      transform: isOpen ? 'rotate(180deg)' : 'rotate(0)',
                      transition: 'transform var(--transition-fast)',
                    }}
                  >
                    <polyline points="6,9 12,15 18,9" />
                  </svg>
                </button>
                {isOpen && (
                  <div
                    style={{
                      padding: '0 var(--space-4) var(--space-4)',
                      borderTop: '1px solid var(--border)',
                    }}
                  >
                    {isEmpty ? (
                      <p
                        style={{
                          color: 'var(--foreground-muted)',
                          fontSize: 'var(--text-sm)',
                          paddingTop: 'var(--space-3)',
                        }}
                      >
                        No data available yet.
                      </p>
                    ) : typeof data === 'object' && data !== null ? (
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 'var(--space-3)',
                          paddingTop: 'var(--space-3)',
                        }}
                      >
                        {Object.entries(data as Record<string, unknown>).map(
                          ([k, v]) => (
                            <div key={k}>
                              <div
                                style={{
                                  fontSize: 'var(--text-sm)',
                                  fontWeight: 'var(--font-medium)',
                                  color: 'var(--foreground)',
                                  marginBottom: 'var(--space-1)',
                                  textTransform: 'capitalize',
                                }}
                              >
                                {k.replace(/_/g, ' ')}
                              </div>
                              <div style={{ fontSize: 'var(--text-sm)' }}>
                                {renderValue(v)}
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    ) : (
                      <div style={{ paddingTop: 'var(--space-3)' }}>
                        {renderValue(data)}
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}
