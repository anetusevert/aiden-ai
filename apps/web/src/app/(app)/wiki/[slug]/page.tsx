'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { fadeUp } from '@/lib/motion';
import { apiClient, type WikiPageDetail } from '@/lib/apiClient';
import { reportScreenContext } from '@/lib/screenContext';
import { useNavigation } from '@/components/NavigationLoader';
import { useAminContext } from '@/components/amin/AminProvider';
import { WikiCitationChip } from '@/components/wiki/WikiCitationChip';

function timeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / 86400000);
  if (diffDays < 1) return 'today';
  if (diffDays === 1) return '1 day ago';
  if (diffDays < 30) return `${diffDays} days ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
}

export default function WikiPageView() {
  const params = useParams();
  const slug = params.slug as string;
  const { navigateTo } = useNavigation();
  const { openPanel } = useAminContext();

  const [page, setPage] = useState<WikiPageDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [updateOpen, setUpdateOpen] = useState(false);
  const [updateText, setUpdateText] = useState('');
  const [updating, setUpdating] = useState(false);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getWikiPage(slug);
      setPage(data);
    } catch {
      setError('Wiki page not found');
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  useEffect(() => {
    if (!page) return;
    reportScreenContext({
      route: `/wiki/${slug}`,
      page_title: page.title,
      document: null,
      ui_state: {
        wiki_slug: slug,
        wiki_category: page.category,
        wiki_jurisdiction: page.jurisdiction,
        wiki_has_contradictions: page.has_contradictions,
      },
    });
  }, [page, slug]);

  const handleUpdate = async () => {
    if (!updateText.trim()) return;
    setUpdating(true);
    try {
      await apiClient.updateWikiPage(slug, updateText);
      setUpdateText('');
      setUpdateOpen(false);
      await loadPage();
    } catch {
      /* ignore */
    }
    setUpdating(false);
  };

  const handleAskAmin = () => {
    if (!page) return;
    openPanel();
    setTimeout(() => {
      window.dispatchEvent(
        new CustomEvent('amin-prefill', {
          detail: { text: `I'm reading the wiki page on ${page.title}. ` },
        })
      );
    }, 100);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <span className="spinner spinner-lg" />
      </div>
    );
  }

  if (error || !page) {
    return (
      <div
        style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}
      >
        {error || 'Page not found'}
      </div>
    );
  }

  return (
    <motion.div className="wiki-page-layout" {...fadeUp}>
      {/* Left — Content */}
      <div className="wiki-content-col">
        <div className="wiki-content-scroll">
          {/* Breadcrumb */}
          <div
            style={{
              fontSize: 13,
              color: 'var(--text-muted)',
              marginBottom: 16,
              display: 'flex',
              gap: 6,
            }}
          >
            <button
              className="wiki-breadcrumb-link"
              onClick={() => navigateTo('/wiki')}
            >
              Wiki
            </button>
            <span>→</span>
            <button
              className="wiki-breadcrumb-link"
              onClick={() => navigateTo(`/wiki?category=${page.category}`)}
            >
              {page.category.charAt(0).toUpperCase() + page.category.slice(1)}
            </button>
            <span>→</span>
            <span style={{ color: '#fff' }}>{page.title}</span>
          </div>

          {/* Header */}
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: '#fff',
              marginBottom: 12,
            }}
          >
            {page.title}
          </h1>
          <div
            style={{
              display: 'flex',
              gap: 8,
              flexWrap: 'wrap',
              marginBottom: 16,
            }}
          >
            {page.jurisdiction && (
              <span className="badge badge-muted">{page.jurisdiction}</span>
            )}
            <span
              className="badge"
              style={{
                background: 'rgba(255,255,255,0.1)',
                color: 'rgba(255,255,255,0.92)',
                border: '1px solid rgba(255,255,255,0.22)',
              }}
            >
              {page.category}
            </span>
            <span className="badge badge-muted">v{page.version}</span>
            <span className="badge badge-muted">
              Updated {timeAgo(page.updated_at)}
            </span>
          </div>

          {/* Banners */}
          {page.is_stale && (
            <div
              className="alert alert-neutral"
              style={{ marginBottom: 12, borderColor: 'rgba(255,255,255,0.2)' }}
            >
              ⏰ This page may be outdated — last updated{' '}
              {timeAgo(page.updated_at)}
            </div>
          )}
          {page.has_contradictions && (
            <div className="alert alert-error" style={{ marginBottom: 12 }}>
              ⚠ Contradictions detected on this page. Review with Amin
              recommended.
            </div>
          )}

          {/* Markdown content */}
          <div className="wiki-markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => {
                  return <p>{processWikiLinks(children)}</p>;
                },
                li: ({ children }) => {
                  return <li>{processWikiLinks(children)}</li>;
                },
              }}
            >
              {page.content_md}
            </ReactMarkdown>
          </div>

          {/* Actions */}
          <div
            style={{
              borderTop: '1px solid var(--border)',
              marginTop: 24,
              paddingTop: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <button className="btn btn-outline" onClick={handleAskAmin}>
              Ask Amin about this →
            </button>

            <div>
              <button
                className="btn btn-outline"
                onClick={() => setUpdateOpen(!updateOpen)}
                style={{ width: '100%', textAlign: 'left' }}
              >
                {updateOpen
                  ? '▼ Update with new info'
                  : '▶ Update with new info'}
              </button>
              {updateOpen && (
                <div style={{ marginTop: 8 }}>
                  <textarea
                    className="form-textarea"
                    placeholder="Paste new information or describe what's changed..."
                    value={updateText}
                    onChange={e => setUpdateText(e.target.value)}
                    style={{ minHeight: 100, width: '100%' }}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={handleUpdate}
                    disabled={updating || !updateText.trim()}
                    style={{ marginTop: 8 }}
                  >
                    {updating ? 'Updating...' : 'Submit Update'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right — Sidebar */}
      <div className="wiki-sidebar">
        {/* Sources */}
        <div style={{ marginBottom: 24 }}>
          <div className="wiki-sidebar-label">SOURCES</div>
          {page.source_doc_ids.length > 0 ? (
            page.source_doc_ids.map((id, i) => (
              <div
                key={i}
                style={{
                  fontSize: 13,
                  color: 'var(--text-muted)',
                  marginBottom: 4,
                  wordBreak: 'break-all',
                }}
              >
                {id}
              </div>
            ))
          ) : (
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              No source documents linked
            </div>
          )}
        </div>

        {/* Backlinks */}
        <div style={{ marginBottom: 24 }}>
          <div className="wiki-sidebar-label">LINKED FROM</div>
          {page.backlinks.length > 0 ? (
            page.backlinks.map(bl => (
              <div key={bl.slug} style={{ marginBottom: 8 }}>
                <button
                  className="wiki-sidebar-link"
                  onClick={() => navigateTo(`/wiki/${bl.slug}`)}
                >
                  {bl.title}
                </button>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {bl.context}
                </div>
              </div>
            ))
          ) : (
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              No pages link here yet — this may be an orphan page
            </div>
          )}
        </div>

        {/* Outlinks */}
        <div style={{ marginBottom: 24 }}>
          <div className="wiki-sidebar-label">LINKS TO</div>
          {page.outlinks.length > 0 ? (
            page.outlinks.map(ol => (
              <div
                key={ol.slug}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  marginBottom: 6,
                }}
              >
                <span
                  className="wiki-dot"
                  style={{ background: 'rgba(255,255,255,0.9)' }}
                />
                <button
                  className="wiki-sidebar-link"
                  onClick={() => navigateTo(`/wiki/${ol.slug}`)}
                >
                  {ol.title}
                </button>
              </div>
            ))
          ) : (
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              No outbound links
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

/**
 * Walk React children and replace [[slug]] text nodes with WikiCitationChip.
 */
function processWikiLinks(children: React.ReactNode): React.ReactNode {
  if (typeof children === 'string') {
    const parts = children.split(/(\[\[[a-z0-9-]+\]\])/g);
    if (parts.length === 1) return children;
    return parts.map((part, i) => {
      const m = part.match(/^\[\[([a-z0-9-]+)\]\]$/);
      if (m) return <WikiCitationChip key={i} slug={m[1]} />;
      return part;
    });
  }
  if (Array.isArray(children)) {
    return children.map((child, i) =>
      typeof child === 'string' ? processWikiLinks(child) : child
    );
  }
  return children;
}
