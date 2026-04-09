'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { apiClient, type SoulDetail } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { SoulConstellation } from '@/components/amin/SoulConstellation';

type Tab = 'overview' | 'soul' | 'twin';

const TAB_ORDER: Tab[] = ['overview', 'soul', 'twin'];

function isFilledValue(value: unknown): boolean {
  if (value === null || value === undefined) {
    return false;
  }
  if (typeof value === 'string') {
    return value.trim().length > 0;
  }
  if (typeof value === 'number') {
    return value > 0;
  }
  if (typeof value === 'boolean') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === 'object') {
    return Object.values(value as Record<string, unknown>).some(isFilledValue);
  }

  return true;
}

function countFilledEntries(value: unknown): number {
  if (Array.isArray(value)) {
    return value.filter(isFilledValue).length;
  }
  if (value && typeof value === 'object') {
    return Object.values(value as Record<string, unknown>).filter(isFilledValue)
      .length;
  }

  return isFilledValue(value) ? 1 : 0;
}

function formatLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, letter => letter.toUpperCase());
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function clampPercentage(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export default function MemberDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { navigateTo } = useNavigation();
  const userId = params.id as string;

  const [soul, setSoul] = useState<SoulDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const [editingProfile, setEditingProfile] = useState(false);
  const [profileJson, setProfileJson] = useState('');
  const [editingTwin, setEditingTwin] = useState(false);
  const [twinJson, setTwinJson] = useState('');

  const isAdmin = user?.role === 'ADMIN';

  const loadSoul = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAdminSoulDetail(userId);
      setSoul(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load soul data');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (userId && isAdmin) loadSoul();
  }, [userId, isAdmin, loadSoul]);

  useEffect(() => {
    if (success) {
      const t = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(t);
    }
  }, [success]);

  useEffect(() => {
    const nextTab = searchParams.get('tab');
    if (nextTab && TAB_ORDER.includes(nextTab as Tab)) {
      setActiveTab(nextTab as Tab);
    }
  }, [searchParams]);

  const handleSaveProfile = async () => {
    try {
      const doc = JSON.parse(profileJson);
      const updated = await apiClient.updateSoulProfile(userId, doc);
      setSoul(updated);
      setEditingProfile(false);
      setSuccess('Profile updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  const handleSaveTwin = async () => {
    try {
      const doc = JSON.parse(twinJson);
      const updated = await apiClient.updateSoulTwin(userId, doc);
      setSoul(updated);
      setEditingTwin(false);
      setSuccess('Digital Twin updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid JSON');
    }
  };

  if (!isAdmin) {
    return (
      <motion.div {...fadeUp}>
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <p className="text-muted">
            Only administrators can view member details.
          </p>
        </div>
      </motion.div>
    );
  }

  if (loading) {
    return (
      <div className="loading">
        <span className="spinner" />
        <span style={{ marginLeft: 'var(--space-3)' }}>
          Loading soul data...
        </span>
      </div>
    );
  }

  const soulSignals = soul
    ? [
        {
          label: 'Profile',
          value: countFilledEntries(soul.profile),
        },
        {
          label: 'Work patterns',
          value: countFilledEntries(soul.work_patterns),
        },
        {
          label: 'Drafting style',
          value: countFilledEntries(soul.drafting_style),
        },
        {
          label: 'Soul dimensions',
          value: soul.soul_dimensions.length,
        },
        {
          label: 'Interactions',
          value: soul.interaction_count,
        },
      ]
    : [];

  const twinSignals = soul
    ? [
        {
          label: 'Personality model',
          value: countFilledEntries(soul.personality_model),
        },
        {
          label: 'Review priorities',
          value: countFilledEntries(soul.review_priorities),
        },
        {
          label: 'Learned corrections',
          value: soul.learned_corrections.length,
        },
        {
          label: 'Preferences',
          value: countFilledEntries(soul.preferences),
        },
        {
          label: 'Consolidated snapshot',
          value: soul.consolidated_at ? 1 : 0,
        },
      ]
    : [];

  const soulProgress = clampPercentage(
    (soulSignals.filter(signal => signal.value > 0).length /
      Math.max(soulSignals.length, 1)) *
      100
  );
  const twinProgress = clampPercentage(
    (twinSignals.filter(signal => signal.value > 0).length /
      Math.max(twinSignals.length, 1)) *
      100
  );

  const overviewStats = soul
    ? [
        {
          label: 'Interactions',
          value: `${soul.interaction_count}`,
        },
        {
          label: 'Soul maturity',
          value: formatLabel(soul.maturity || 'nascent'),
        },
        {
          label: 'Last consolidation',
          value: soul.consolidated_at
            ? new Date(soul.consolidated_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            : 'Pending',
        },
        {
          label: 'Last updated',
          value: soul.updated_at
            ? new Date(soul.updated_at).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
              })
            : 'Not yet updated',
        },
      ]
    : [];

  const codeBlockStyle = {
    background: 'rgba(255,255,255,0.04)',
    padding: 16,
    borderRadius: 8,
    fontSize: 12,
    overflow: 'auto' as const,
    maxHeight: 400,
    color: 'var(--text-primary)',
    border: '1px solid var(--glass-border, rgba(255,255,255,0.07))',
  };

  return (
    <motion.div {...fadeUp}>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <button
              className="btn btn-sm"
              onClick={() => navigateTo('/members')}
              style={{ marginBottom: 8, opacity: 0.7 }}
            >
              &larr; Back to Members
            </button>
            <h1 className="page-title">
              {soul?.user_full_name || soul?.user_email || 'Unknown User'}
            </h1>
            <p className="page-subtitle">Soul & Digital Twin Management</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span
              style={{
                padding: '4px 12px',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                color: 'rgba(255,255,255,0.9)',
                textTransform: 'capitalize',
              }}
            >
              {soul?.maturity ?? 'nascent'}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {soul?.interaction_count ?? 0} interactions
            </span>
          </div>
        </div>
      </div>

      {success && <div className="alert alert-success mb-4">{success}</div>}
      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Tabs */}
      <div
        style={{
          display: 'flex',
          gap: 2,
          marginBottom: 24,
          borderBottom: '1px solid var(--glass-border, rgba(255,255,255,0.07))',
        }}
      >
        {(['overview', 'soul', 'twin'] as Tab[]).map(tab => (
          <button
            key={tab}
            className="btn btn-sm"
            onClick={() => setActiveTab(tab)}
            style={{
              borderRadius: '6px 6px 0 0',
              borderBottom:
                activeTab === tab
                  ? '2px solid rgba(255,255,255,0.9)'
                  : '2px solid transparent',
              background:
                activeTab === tab ? 'rgba(255,255,255,0.03)' : 'transparent',
              fontWeight: activeTab === tab ? 600 : 400,
              textTransform: 'capitalize',
            }}
          >
            {tab === 'twin' ? 'Digital Twin' : tab}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && soul && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1.15fr 0.85fr',
            gap: 24,
          }}
        >
          <div
            className="card"
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              paddingTop: 32,
              paddingBottom: 48,
            }}
          >
            <SoulConstellation
              dimensions={soul.soul_dimensions || []}
              maturity={soul.maturity}
              interactionCount={soul.interaction_count}
            />
          </div>

          <div>
            <div className="card mb-4">
              <h3
                className="card-title"
                style={{
                  fontSize: 14,
                  marginBottom: 16,
                  color: 'var(--text-primary)',
                }}
              >
                Build Progress
              </h3>
              <div style={{ display: 'grid', gap: 16 }}>
                {[
                  {
                    title: 'Soul',
                    percent: soulProgress,
                    caption: `${soulSignals.filter(signal => signal.value > 0).length}/${soulSignals.length} signals in place`,
                    items: soulSignals,
                  },
                  {
                    title: 'Digital Twin',
                    percent: twinProgress,
                    caption: `${twinSignals.filter(signal => signal.value > 0).length}/${twinSignals.length} signals in place`,
                    items: twinSignals,
                  },
                ].map(section => (
                  <div
                    key={section.title}
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background: 'rgba(255,255,255,0.03)',
                      border:
                        '1px solid var(--glass-border, rgba(255,255,255,0.07))',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 10,
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: 14,
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                          }}
                        >
                          {section.title}
                        </div>
                        <div
                          style={{
                            fontSize: 12,
                            color: 'var(--text-secondary)',
                            marginTop: 2,
                          }}
                        >
                          {section.caption}
                        </div>
                      </div>
                      <div
                        style={{
                          fontSize: 20,
                          fontWeight: 700,
                          color: 'var(--text-primary)',
                        }}
                      >
                        {section.percent}%
                      </div>
                    </div>
                    <div
                      style={{
                        height: 8,
                        borderRadius: 999,
                        background: 'rgba(255,255,255,0.08)',
                        overflow: 'hidden',
                        marginBottom: 12,
                      }}
                    >
                      <div
                        style={{
                          width: `${section.percent}%`,
                          height: '100%',
                          borderRadius: 999,
                          background:
                            section.title === 'Soul'
                              ? 'linear-gradient(90deg, rgba(255,255,255,0.92), rgba(255,255,255,0.6))'
                              : 'linear-gradient(90deg, rgba(96,165,250,0.95), rgba(167,139,250,0.95))',
                        }}
                      />
                    </div>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: 8,
                      }}
                    >
                      {section.items.map(item => (
                        <div
                          key={item.label}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            gap: 12,
                            fontSize: 12,
                            color: 'var(--text-secondary)',
                          }}
                        >
                          <span>{item.label}</span>
                          <span style={{ color: 'var(--text-primary)' }}>
                            {item.value}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div
              className="card mb-4"
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 12,
              }}
            >
              {overviewStats.map(stat => (
                <div
                  key={stat.label}
                  style={{
                    padding: 14,
                    borderRadius: 10,
                    background: 'rgba(255,255,255,0.03)',
                    border:
                      '1px solid var(--glass-border, rgba(255,255,255,0.07))',
                  }}
                >
                  <div
                    style={{
                      fontSize: 11,
                      textTransform: 'uppercase',
                      letterSpacing: '0.08em',
                      color: 'var(--text-secondary)',
                      marginBottom: 6,
                    }}
                  >
                    {stat.label}
                  </div>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                    }}
                  >
                    {stat.value}
                  </div>
                </div>
              ))}
            </div>

            <div className="card mb-4">
              <h3
                className="card-title"
                style={{
                  fontSize: 14,
                  marginBottom: 12,
                  color: 'var(--text-primary)',
                }}
              >
                Profile
              </h3>
              {Object.keys(soul.profile || {}).length > 0 ? (
                <dl style={{ margin: 0, display: 'grid', gap: 10 }}>
                  {Object.entries(soul.profile).map(([k, v]) => (
                    <div
                      key={k}
                      style={{
                        padding: 12,
                        borderRadius: 10,
                        background: 'rgba(255,255,255,0.03)',
                        border:
                          '1px solid var(--glass-border, rgba(255,255,255,0.07))',
                      }}
                    >
                      <dt
                        style={{
                          fontSize: 11,
                          color: 'var(--text-secondary)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.08em',
                          marginBottom: 4,
                        }}
                      >
                        {formatLabel(k)}
                      </dt>
                      <dd
                        style={{
                          fontSize: 13,
                          margin: 0,
                          color: 'var(--text-primary)',
                          wordBreak: 'break-word',
                        }}
                      >
                        {formatValue(v)}
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-muted" style={{ fontSize: 13 }}>
                  No profile data yet.
                </p>
              )}
            </div>

            <div className="card">
              <h3
                className="card-title"
                style={{
                  fontSize: 14,
                  marginBottom: 12,
                  color: 'var(--text-primary)',
                }}
              >
                Preferences
              </h3>
              {Object.keys(soul.preferences || {}).length > 0 ? (
                <dl style={{ margin: 0, display: 'grid', gap: 10 }}>
                  {Object.entries(soul.preferences).map(([k, v]) => (
                    <div
                      key={k}
                      style={{
                        padding: 12,
                        borderRadius: 10,
                        background: 'rgba(255,255,255,0.03)',
                        border:
                          '1px solid var(--glass-border, rgba(255,255,255,0.07))',
                      }}
                    >
                      <dt
                        style={{
                          fontSize: 11,
                          color: 'var(--text-secondary)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.08em',
                          marginBottom: 4,
                        }}
                      >
                        {formatLabel(k)}
                      </dt>
                      <dd style={{ fontSize: 13, margin: 0 }}>
                        <span
                          style={{
                            color: 'var(--text-primary)',
                            wordBreak: 'break-word',
                          }}
                        >
                          {formatValue(v)}
                        </span>
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-muted" style={{ fontSize: 13 }}>
                  No preferences recorded yet.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Soul Tab */}
      {activeTab === 'soul' && soul && (
        <div className="card">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            <h3 className="card-title" style={{ margin: 0 }}>
              Soul Profile
            </h3>
            {isAdmin && (
              <button
                className="btn btn-sm btn-outline"
                onClick={() => {
                  if (editingProfile) {
                    setEditingProfile(false);
                  } else {
                    setProfileJson(JSON.stringify(soul.profile || {}, null, 2));
                    setEditingProfile(true);
                  }
                }}
              >
                {editingProfile ? 'Cancel' : 'Edit'}
              </button>
            )}
          </div>

          {editingProfile ? (
            <>
              <textarea
                className="form-input"
                rows={12}
                value={profileJson}
                onChange={e => setProfileJson(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: 12 }}
              />
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveProfile}
                style={{ marginTop: 8 }}
              >
                Save Profile
              </button>
            </>
          ) : (
            <pre style={codeBlockStyle}>
              {JSON.stringify(soul.profile || {}, null, 2)}
            </pre>
          )}

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Work Patterns
          </h3>
          <pre style={{ ...codeBlockStyle, maxHeight: 300 }}>
            {JSON.stringify(soul.work_patterns || {}, null, 2)}
          </pre>

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Drafting Style
          </h3>
          <pre style={{ ...codeBlockStyle, maxHeight: 300 }}>
            {JSON.stringify(soul.drafting_style || {}, null, 2)}
          </pre>
        </div>
      )}

      {/* Twin Tab */}
      {activeTab === 'twin' && soul && (
        <div className="card">
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 16,
            }}
          >
            <h3 className="card-title" style={{ margin: 0 }}>
              Digital Twin — Personality Model
            </h3>
            {isAdmin && (
              <button
                className="btn btn-sm btn-outline"
                onClick={() => {
                  if (editingTwin) {
                    setEditingTwin(false);
                  } else {
                    setTwinJson(
                      JSON.stringify(soul.personality_model || {}, null, 2)
                    );
                    setEditingTwin(true);
                  }
                }}
              >
                {editingTwin ? 'Cancel' : 'Edit'}
              </button>
            )}
          </div>

          {editingTwin ? (
            <>
              <textarea
                className="form-input"
                rows={12}
                value={twinJson}
                onChange={e => setTwinJson(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: 12 }}
              />
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveTwin}
                style={{ marginTop: 8 }}
              >
                Save Twin
              </button>
            </>
          ) : (
            <pre style={codeBlockStyle}>
              {JSON.stringify(soul.personality_model || {}, null, 2)}
            </pre>
          )}

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Review Priorities
          </h3>
          <pre style={{ ...codeBlockStyle, maxHeight: 300 }}>
            {JSON.stringify(soul.review_priorities || {}, null, 2)}
          </pre>

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Learned Corrections
          </h3>
          {Array.isArray(soul.learned_corrections) &&
          soul.learned_corrections.length > 0 ? (
            <ul style={{ paddingLeft: 20 }}>
              {soul.learned_corrections.slice(-10).map((c, i) => (
                <li
                  key={i}
                  style={{
                    fontSize: 13,
                    marginBottom: 6,
                    color: 'var(--text-secondary)',
                  }}
                >
                  {typeof c === 'object' && c !== null
                    ? (c as { summary?: string }).summary || JSON.stringify(c)
                    : String(c)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted" style={{ fontSize: 13 }}>
              No corrections recorded yet.
            </p>
          )}
        </div>
      )}
    </motion.div>
  );
}
