'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { apiClient, type NewsSourceEntry } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

export default function NewsSettingsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const { navigateTo } = useNavigation();

  const [sources, setSources] = useState<NewsSourceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const isAdmin = user?.role === 'ADMIN';

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      router.push('/news');
    }
  }, [authLoading, isAdmin, router]);

  const fetchSources = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.getNewsSources();
      setSources(res.sources);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin) {
      void fetchSources();
    }
  }, [isAdmin, fetchSources]);

  function toggleSource(sourceId: string) {
    setSources(prev =>
      prev.map(s => (s.id === sourceId ? { ...s, enabled: !s.enabled } : s))
    );
    setSuccess(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const enabledIds = sources.filter(s => s.enabled).map(s => s.id);
      const res = await apiClient.updateNewsSources(enabledIds);
      setSources(res.sources);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  if (authLoading || !isAdmin) {
    return <div className="loading">Loading...</div>;
  }

  const enabledCount = sources.filter(s => s.enabled).length;

  return (
    <motion.div className="news-settings-page" {...fadeUp}>
      <div className="news-settings-header">
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={() => navigateTo('/news')}
        >
          &larr; Back to feed
        </button>
      </div>

      <div className="page-header">
        <h1 className="page-title">News Sources</h1>
        <p className="page-subtitle">
          Choose which legal news sources appear in your workspace feed.
          {enabledCount > 0 && (
            <span className="news-settings-count">
              {' '}
              {enabledCount} of {sources.length} enabled
            </span>
          )}
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && (
        <div className="alert alert-success">Sources updated successfully.</div>
      )}

      {loading ? (
        <div className="loading">Loading sources...</div>
      ) : (
        <motion.div
          className="news-settings-grid"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {sources.map(source => (
            <motion.div
              key={source.id}
              className={`news-source-card${source.enabled ? ' news-source-card--active' : ''}`}
              variants={staggerItem}
              onClick={() => toggleSource(source.id)}
            >
              <div className="news-source-card-top">
                <div className="news-source-card-info">
                  <h3 className="news-source-card-name">{source.name}</h3>
                  <p className="news-source-card-desc">{source.description}</p>
                </div>
                <div
                  className={`news-source-toggle${source.enabled ? ' news-source-toggle--on' : ''}`}
                  role="switch"
                  aria-checked={source.enabled}
                >
                  <div className="news-source-toggle-knob" />
                </div>
              </div>
              <div className="news-source-card-badges">
                <span className="badge badge-info">{source.region}</span>
                <span className="badge badge-muted">{source.category}</span>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}

      <div className="news-settings-save-bar">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void handleSave()}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Sources'}
        </button>
      </div>
    </motion.div>
  );
}
