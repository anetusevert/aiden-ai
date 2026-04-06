'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';
import { apiClient, type WikiLogEntry } from '@/lib/apiClient';
import { reportScreenContext } from '@/lib/screenContext';

const OP_COLORS: Record<string, string> = {
  ingest: '#638cff',
  query: '#38bdf8',
  update: '#f59e0b',
  create: '#34d399',
  lint: '#94a3b8',
};

const FILTER_OPS = ['All', 'Ingest', 'Query', 'Update', 'Create', 'Lint'] as const;

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

export default function WikiLogPage() {
  const [logs, setLogs] = useState<WikiLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeOp, setActiveOp] = useState('All');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    reportScreenContext({
      route: '/wiki/log',
      page_title: 'Wiki Log',
      document: null,
      ui_state: {},
    });
  }, []);

  const fetchLogs = useCallback(async (op: string) => {
    setLoading(true);
    try {
      const params: { operation?: string } = {};
      if (op !== 'All') params.operation = op.toLowerCase();
      const res = await apiClient.getWikiLogs(params);
      setLogs(res.items);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs(activeOp);
  }, [activeOp, fetchLogs]);

  return (
    <motion.div {...fadeUp} style={{ padding: 24 }}>
      <div className="page-header" style={{ marginBottom: 16 }}>
        <h1 className="page-title">Wiki Log</h1>
        <p className="page-subtitle">Every operation Amin performs on the knowledge base</p>
      </div>

      {/* Filter chips */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
        {FILTER_OPS.map(op => (
          <button
            key={op}
            className={`badge ${activeOp === op ? 'badge-gold' : 'badge-muted'}`}
            onClick={() => setActiveOp(op)}
            style={activeOp === op ? { borderColor: '#d4a017', background: 'rgba(212,160,23,0.15)' } : undefined}
          >
            {op}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <span className="spinner" />
        </div>
      ) : logs.length === 0 ? (
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          No wiki log entries yet.
        </div>
      ) : (
        <motion.div variants={staggerContainer} initial="hidden" animate="visible">
          {logs.map(log => (
            <motion.div
              key={log.id}
              variants={staggerItem}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
                padding: '12px 0',
                borderBottom: '1px solid var(--border)',
                cursor: 'pointer',
              }}
              onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
            >
              <span
                className="badge"
                style={{
                  background: (OP_COLORS[log.operation] || '#888') + '22',
                  color: OP_COLORS[log.operation] || '#888',
                  border: `1px solid ${OP_COLORS[log.operation] || '#888'}44`,
                  fontSize: 11,
                  flexShrink: 0,
                }}
              >
                {log.operation}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, color: '#fff' }}>{log.amin_summary}</div>
                {expandedId === log.id && log.pages_affected.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {log.pages_affected.map((slug, i) => (
                      <span key={i} className="badge badge-muted" style={{ fontSize: 11 }}>
                        {slug}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', flexShrink: 0 }}>
                {timeAgo(log.created_at)}
              </span>
            </motion.div>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}
