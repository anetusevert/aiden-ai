'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { getApiBaseUrl } from '@/lib/api';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';
import { useTranslations } from 'next-intl';
import { WorkflowLaunchBanner } from '@/components/workflows/WorkflowLaunchBanner';

interface ConversationRow {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at?: string;
  last_message_preview?: string;
}

export default function ConversationsPage() {
  const t = useTranslations('common');
  const [conversations, setConversations] = useState<ConversationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/conversations?limit=50&offset=0`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setConversations(data.conversations ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('failedLoad'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleNew = async () => {
    try {
      const baseUrl = getApiBaseUrl();
      const res = await fetch(`${baseUrl}/conversations`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadConversations();
    } catch {
      // silently ignore
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const baseUrl = getApiBaseUrl();
      await fetch(`${baseUrl}/conversations/${id}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      setConversations(prev => prev.filter(c => c.id !== id));
    } catch {
      // silently ignore
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  return (
    <motion.div className="page-container" {...fadeUp}>
      <WorkflowLaunchBanner currentRoute="/conversations" />

      <div className="page-header">
        <div>
          <h1 className="page-title">Conversations</h1>
          <p className="page-subtitle">Your chat history with Amin</p>
        </div>
        <button className="btn btn-primary" onClick={handleNew}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Conversation
        </button>
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
            {t('loadingConversations')}
          </p>
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          <p>{error}</p>
          <button className="btn btn-sm" onClick={loadConversations}>
            {t('retry')}
          </button>
        </div>
      )}

      {!loading && !error && conversations.length === 0 && (
        <div
          className="card"
          style={{ textAlign: 'center', padding: 'var(--space-12)' }}
        >
          <svg
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--foreground-muted)"
            strokeWidth="1"
            style={{ marginBottom: 'var(--space-4)' }}
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <h3 style={{ marginBottom: 'var(--space-2)' }}>
            No conversations yet
          </h3>
          <p
            style={{
              color: 'var(--foreground-muted)',
              marginBottom: 'var(--space-4)',
            }}
          >
            Start a conversation with Amin to get legal assistance.
          </p>
          <button className="btn btn-primary" onClick={handleNew}>
            Start Conversation
          </button>
        </div>
      )}

      {!loading && !error && conversations.length > 0 && (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>{t('tableTitle')}</th>
                <th>{t('tableDate')}</th>
                <th>{t('status')}</th>
                <th style={{ width: 80 }} />
              </tr>
            </thead>
            <motion.tbody
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {conversations.map(c => (
                <motion.tr key={c.id} variants={staggerItem}>
                  <td>
                    <span style={{ fontWeight: 'var(--font-medium)' }}>
                      {c.title || 'Untitled conversation'}
                    </span>
                    {c.last_message_preview && (
                      <p
                        style={{
                          fontSize: 'var(--text-sm)',
                          color: 'var(--foreground-muted)',
                          margin: '2px 0 0',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: 400,
                        }}
                      >
                        {c.last_message_preview}
                      </p>
                    )}
                  </td>
                  <td
                    style={{
                      color: 'var(--foreground-muted)',
                      fontSize: 'var(--text-sm)',
                    }}
                  >
                    {formatDate(c.created_at)}
                  </td>
                  <td>
                    <span
                      className={`badge badge-${c.status === 'active' ? 'success' : 'default'}`}
                    >
                      {c.status === 'active'
                        ? t('conversationStatusActive')
                        : c.status === 'archived'
                          ? t('conversationStatusArchived')
                          : c.status}
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => handleDelete(c.id)}
                      aria-label={t('archiveConversation')}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <polyline points="3,6 5,6 21,6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </td>
                </motion.tr>
              ))}
            </motion.tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}
