'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { staggerContainer, staggerItem } from '@/lib/motion';
import {
  apiClient,
  type WikiPageSummary,
  type WikiHealthResponse,
} from '@/lib/apiClient';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';

const CATEGORY_COLORS: Record<string, string> = {
  law: 'rgba(255,255,255,0.92)',
  regulation: 'rgba(255,255,255,0.82)',
  concept: 'rgba(255,255,255,0.72)',
  entity: 'rgba(255,255,255,0.62)',
  research: 'rgba(255,255,255,0.52)',
  synthesis: 'rgba(255,255,255,0.9)',
  case: 'rgba(255,255,255,0.78)',
};

const CATEGORIES = [
  'All',
  'Laws',
  'Regulations',
  'Concepts',
  'Entities',
  'Research',
  'Synthesis',
] as const;
const CATEGORY_MAP: Record<string, string> = {
  Laws: 'law',
  Regulations: 'regulation',
  Concepts: 'concept',
  Entities: 'entity',
  Research: 'research',
  Synthesis: 'synthesis',
};

const JURISDICTIONS = ['All', 'UAE', 'KSA', 'Qatar', 'GCC'] as const;
const JURISDICTION_MAP: Record<string, string> = {
  UAE: 'UAE',
  KSA: 'KSA',
  Qatar: 'QATAR',
  GCC: 'GCC',
};

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
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

export function WikiPageList() {
  const { navigateTo } = useNavigation();
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const [pages, setPages] = useState<WikiPageSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [activeJurisdiction, setActiveJurisdiction] = useState('All');
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<WikiHealthResponse | null>(null);
  const [lintRunning, setLintRunning] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const fetchPages = useCallback(
    async (searchVal: string, cat: string, jur: string) => {
      setLoading(true);
      try {
        const params: {
          search?: string;
          category?: string;
          jurisdiction?: string;
        } = {};
        if (searchVal) params.search = searchVal;
        if (cat !== 'All') params.category = CATEGORY_MAP[cat];
        if (jur !== 'All') params.jurisdiction = JURISDICTION_MAP[jur];
        const res = await apiClient.getWikiPages(params);
        setPages(res.items);
        setTotal(res.total);
      } catch {
        setPages([]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchPages(search, activeCategory, activeJurisdiction);
  }, [activeCategory, activeJurisdiction]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchPages(search, activeCategory, activeJurisdiction);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isAdmin) {
      apiClient
        .getWikiHealth()
        .then(setHealth)
        .catch(() => {});
    }
  }, [isAdmin]);

  const handleLint = async () => {
    setLintRunning(true);
    try {
      await apiClient.runWikiLint();
    } catch {
      /* ignore */
    }
    setLintRunning(false);
  };

  return (
    <div className="wiki-list-col">
      {/* Search */}
      <div style={{ padding: '16px 16px 0' }}>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search the legal wiki..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', paddingRight: search ? 32 : undefined }}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              style={{
                position: 'absolute',
                right: 8,
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: 16,
                lineHeight: 1,
              }}
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* Category chips */}
      <div
        style={{
          padding: '12px 16px 0',
          display: 'flex',
          gap: 6,
          overflowX: 'auto',
          flexShrink: 0,
        }}
      >
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            className={`badge ${activeCategory === cat ? 'badge-gold' : 'badge-muted'}`}
            onClick={() => setActiveCategory(cat)}
            style={
              activeCategory === cat
                ? {
                    borderColor: 'rgba(255,255,255,0.45)',
                    background: 'rgba(255,255,255,0.12)',
                  }
                : undefined
            }
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Jurisdiction chips */}
      <div
        style={{
          padding: '8px 16px 12px',
          display: 'flex',
          gap: 6,
          overflowX: 'auto',
          flexShrink: 0,
          borderBottom: '1px solid var(--border)',
        }}
      >
        {JURISDICTIONS.map(jur => (
          <button
            key={jur}
            className={`badge ${activeJurisdiction === jur ? 'badge-gold' : 'badge-muted'}`}
            onClick={() => setActiveJurisdiction(jur)}
            style={
              activeJurisdiction === jur
                ? {
                    borderColor: 'rgba(255,255,255,0.45)',
                    background: 'rgba(255,255,255,0.12)',
                  }
                : undefined
            }
          >
            {jur}
          </button>
        ))}
      </div>

      {/* Page list */}
      <div className="wiki-page-list">
        {loading ? (
          <div
            style={{ display: 'flex', justifyContent: 'center', padding: 40 }}
          >
            <span className="spinner" />
          </div>
        ) : pages.length === 0 ? (
          <div
            style={{
              padding: 40,
              textAlign: 'center',
              color: 'var(--text-muted)',
            }}
          >
            No wiki pages yet. Amin will build this as you research.
          </div>
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {pages.map(page => (
              <motion.div
                key={page.id}
                variants={staggerItem}
                className="wiki-page-row"
                onClick={() => navigateTo(`/wiki/${page.slug}`)}
              >
                <span
                  className="wiki-dot"
                  style={{
                    background: CATEGORY_COLORS[page.category] || '#888',
                  }}
                />
                <span className="wiki-page-title">{page.title}</span>
                <span className="wiki-page-meta">
                  {page.jurisdiction && (
                    <span
                      className="badge badge-muted"
                      style={{ fontSize: 10 }}
                    >
                      {page.jurisdiction}
                    </span>
                  )}
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    v{page.version}
                  </span>
                </span>
                <span className="wiki-page-time">
                  {timeAgo(page.updated_at)}
                </span>
                {page.has_contradictions && (
                  <span
                    title="Contradictions detected"
                    style={{ color: '#ef4444', fontSize: 14 }}
                  >
                    ⚠
                  </span>
                )}
                {page.is_stale && (
                  <span
                    title="Page may be outdated"
                    style={{ color: 'rgba(255,255,255,0.55)', fontSize: 14 }}
                  >
                    ⏰
                  </span>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>

      {/* Health bar */}
      {isAdmin && health && (
        <div className="wiki-health-bar">
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            {health.page_count} pages · {health.orphan_count} orphans ·{' '}
            {health.stale_count} stale · {health.contradiction_count}{' '}
            contradictions
          </span>
          <button
            className="btn btn-outline"
            style={{ fontSize: 11, padding: '2px 8px' }}
            onClick={handleLint}
            disabled={lintRunning}
          >
            {lintRunning ? 'Running...' : 'Run Health Check'}
          </button>
        </div>
      )}
    </div>
  );
}
