'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { apiClient, type SoulDetail } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { SoulConstellation } from '@/components/amin/SoulConstellation';

type Tab = 'overview' | 'soul' | 'twin';

export default function MemberDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
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

  return (
    <motion.div {...fadeUp}>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <button
              className="btn btn-sm"
              onClick={() => router.push('/members')}
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
                background: 'rgba(212,160,23,0.12)',
                border: '1px solid rgba(212,160,23,0.25)',
                color: 'rgba(212,160,23,0.9)',
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
                  ? '2px solid var(--amin-accent, #d4a017)'
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
          style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}
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
                style={{ fontSize: 14, marginBottom: 12 }}
              >
                Profile
              </h3>
              {Object.keys(soul.profile || {}).length > 0 ? (
                <dl style={{ margin: 0 }}>
                  {Object.entries(soul.profile).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 8 }}>
                      <dt
                        style={{
                          fontSize: 11,
                          color: 'var(--text-secondary)',
                          textTransform: 'capitalize',
                        }}
                      >
                        {k.replace(/_/g, ' ')}
                      </dt>
                      <dd style={{ fontSize: 13, margin: 0 }}>{String(v)}</dd>
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
                style={{ fontSize: 14, marginBottom: 12 }}
              >
                Preferences
              </h3>
              {Object.keys(soul.preferences || {}).length > 0 ? (
                <dl style={{ margin: 0 }}>
                  {Object.entries(soul.preferences).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 8 }}>
                      <dt
                        style={{
                          fontSize: 11,
                          color: 'var(--text-secondary)',
                          textTransform: 'capitalize',
                        }}
                      >
                        {k.replace(/_/g, ' ')}
                      </dt>
                      <dd style={{ fontSize: 13, margin: 0 }}>
                        {typeof v === 'object' ? JSON.stringify(v) : String(v)}
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
            <pre
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: 16,
                borderRadius: 8,
                fontSize: 12,
                overflow: 'auto',
                maxHeight: 400,
                color: 'var(--text-primary)',
              }}
            >
              {JSON.stringify(soul.profile || {}, null, 2)}
            </pre>
          )}

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Work Patterns
          </h3>
          <pre
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: 16,
              borderRadius: 8,
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 300,
              color: 'var(--text-primary)',
            }}
          >
            {JSON.stringify(soul.work_patterns || {}, null, 2)}
          </pre>

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Drafting Style
          </h3>
          <pre
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: 16,
              borderRadius: 8,
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 300,
              color: 'var(--text-primary)',
            }}
          >
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
            <pre
              style={{
                background: 'rgba(0,0,0,0.2)',
                padding: 16,
                borderRadius: 8,
                fontSize: 12,
                overflow: 'auto',
                maxHeight: 400,
                color: 'var(--text-primary)',
              }}
            >
              {JSON.stringify(soul.personality_model || {}, null, 2)}
            </pre>
          )}

          <h3
            className="card-title"
            style={{ marginTop: 24, marginBottom: 12 }}
          >
            Review Priorities
          </h3>
          <pre
            style={{
              background: 'rgba(0,0,0,0.2)',
              padding: 16,
              borderRadius: 8,
              fontSize: 12,
              overflow: 'auto',
              maxHeight: 300,
              color: 'var(--text-primary)',
            }}
          >
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
