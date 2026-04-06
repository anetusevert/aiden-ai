'use client';

import { useState, useMemo, useCallback, useEffect } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { useNewsPolling } from '@/hooks/useNewsPolling';
import { useAuth } from '@/lib/AuthContext';
import { useAminContext } from '@/components/amin/AminProvider';
import { reportScreenContext } from '@/lib/screenContext';
import { apiClient, type LegalNewsItem } from '@/lib/apiClient';
import { WikiCitationChip } from '@/components/wiki/WikiCitationChip';
import { ArticleModal } from '@/components/news/ArticleModal';
import {
  SOURCE_COLORS,
  SOURCE_NAME_COLORS,
  CATEGORY_ICONS,
  CATEGORIES,
  JURISDICTIONS,
} from '@/components/news/constants';
import {
  glassReveal,
  staggerContainer,
  staggerItem,
  tileMotion,
} from '@/lib/motion';

// ── helpers ────────────────────────────────────────────────────────────

function relTime(dateStr: string): string {
  const ms = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 1) return 'Just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function srcColor(item: LegalNewsItem): string {
  return (
    SOURCE_NAME_COLORS[item.source_name] ??
    SOURCE_COLORS[item.source_category] ??
    '#94a3b8'
  );
}

// ── page ───────────────────────────────────────────────────────────────

export default function NewsPage() {
  const { user } = useAuth();
  const { openPanel } = useAminContext();

  const [category, setCategory] = useState('');
  const [jurisdiction, setJurisdiction] = useState('');
  const [highOnly, setHighOnly] = useState(false);
  const [modalItem, setModalItem] = useState<LegalNewsItem | null>(null);

  const query = useMemo(
    () => ({
      category: category || undefined,
      jurisdiction: jurisdiction || undefined,
      importance: highOnly ? 'high' : undefined,
      limit: 40,
    }),
    [category, jurisdiction, highOnly]
  );

  const { items, total, isLoading, error, refresh, loadMore, breakingItems } =
    useNewsPolling(query);

  // screen context on mount
  useEffect(() => {
    reportScreenContext({
      route: '/news',
      page_title: 'Legal Intelligence',
      document: null,
      ui_state: {
        active_category: category,
        active_jurisdiction: jurisdiction,
      },
    });
  }, [category, jurisdiction]);

  // wiki-file callback from modal
  const handleWikiFiled = useCallback(
    (itemId: string, slug: string) => {
      // optimistic UI update is handled by the modal internally
    },
    []
  );

  const featured = items[0] ?? null;
  const gridItems = useMemo(() => items.slice(1), [items]);

  // Ask Amin shortcut
  const askAmin = useCallback(
    (item: LegalNewsItem) => {
      openPanel();
      setTimeout(() => {
        window.dispatchEvent(
          new CustomEvent('amin-prefill', {
            detail: { text: `Tell me about: ${item.title}` },
          })
        );
      }, 200);
    },
    [openPanel]
  );

  // file to wiki from card
  const [filingId, setFilingId] = useState<string | null>(null);
  const fileToWiki = useCallback(async (item: LegalNewsItem) => {
    setFilingId(item.id);
    try {
      await apiClient.fileNewsToWiki(item.id);
      // trigger re-fetch to get updated wiki_filed
      // The item will show the chip on next refresh
    } catch {
      // silent
    } finally {
      setFilingId(null);
    }
  }, []);

  // ── render ─────────────────────────────────────────────────────────

  return (
    <div className="news-shell">
      {/* ── ZONE 1 : BREAKING BAR ── */}
      <div className="news-breaking-bar">
        {breakingItems.length > 0 ? (
          <>
            <div className="news-breaking-label">
              <span className="news-breaking-dot" />
              BREAKING
            </div>
            <div className="news-ticker-wrap">
              <div className="news-ticker">
                {breakingItems.map(b => (
                  <button
                    key={b.id}
                    className="news-ticker-item"
                    onClick={() => setModalItem(b)}
                  >
                    {b.title}
                    <span className="news-ticker-sep">·</span>
                  </button>
                ))}
                {/* duplicate for seamless loop */}
                {breakingItems.map(b => (
                  <button
                    key={`dup-${b.id}`}
                    className="news-ticker-item"
                    onClick={() => setModalItem(b)}
                  >
                    {b.title}
                    <span className="news-ticker-sep">·</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="news-breaking-idle">
            <span>Legal Intelligence — Updated {items.length > 0 ? relTime(items[0].published_at) : 'recently'}</span>
            <button
              className="news-refresh-btn"
              onClick={() => void refresh()}
              disabled={isLoading}
              title="Refresh news"
            >
              ↻
            </button>
          </div>
        )}
      </div>

      {/* ── ZONE 2 + 3 : BODY ── */}
      <div className="news-body">
        {/* ── FILTER RAIL ── */}
        <aside className="news-filter-rail">
          <span className="news-rail-label">FILTER</span>

          <div className="news-rail-categories">
            {CATEGORIES.map(c => (
              <button
                key={c.key}
                className={`news-rail-cat${category === c.key ? ' news-rail-cat--active' : ''}`}
                onClick={() => setCategory(c.key)}
              >
                {c.icon ? <span className="news-rail-cat-icon">{c.icon}</span> : null}
                {c.label}
              </button>
            ))}
          </div>

          <div className="news-rail-jurisdictions">
            <button
              className={`news-rail-jur${jurisdiction === '' ? ' news-rail-jur--active' : ''}`}
              onClick={() => setJurisdiction('')}
            >
              All
            </button>
            {JURISDICTIONS.map(j => (
              <button
                key={j}
                className={`news-rail-jur${jurisdiction === j ? ' news-rail-jur--active' : ''}`}
                onClick={() => setJurisdiction(j)}
              >
                {j}
              </button>
            ))}
          </div>

          <span className="news-rail-label">SOURCES</span>
          <div className="news-rail-sources">
            {Object.entries(SOURCE_NAME_COLORS).map(([name, color]) => (
              <div key={name} className="news-rail-source">
                <span
                  className="news-rail-source-dot"
                  style={{ background: color }}
                />
                <span className="news-rail-source-name">{name}</span>
              </div>
            ))}
          </div>

          <label className="news-rail-toggle">
            <input
              type="checkbox"
              checked={highOnly}
              onChange={e => setHighOnly(e.target.checked)}
            />
            <span>High priority only</span>
          </label>
        </aside>

        {/* ── CONTENT AREA ── */}
        <div className="news-content">
          {error && <div className="alert alert-error">{error}</div>}

          {isLoading && items.length === 0 ? (
            <div className="news-loading">
              <span className="spinner spinner-lg" />
            </div>
          ) : items.length === 0 ? (
            <div className="news-empty-state">
              <h2>No news available</h2>
              <p>Try adjusting your filters or trigger a refresh.</p>
              <button className="btn btn-outline" onClick={() => void refresh()}>
                Refresh
              </button>
            </div>
          ) : (
            <>
              {/* ── FEATURED CARD ── */}
              {featured && (
                <motion.div className="news-featured" {...glassReveal}>
                  <div className="news-featured-inner">
                    {featured.image_url ? (
                      <div className="news-featured-media">
                        <Image
                          src={featured.image_url}
                          alt=""
                          fill
                          sizes="50vw"
                          unoptimized
                        />
                        <div className="news-featured-media-overlay" />
                      </div>
                    ) : (
                      <div className="news-featured-icon-area">
                        <span className="news-featured-icon">
                          {CATEGORY_ICONS[featured.source_category] ?? '📰'}
                        </span>
                      </div>
                    )}
                    <div className="news-featured-body">
                      <div className="news-featured-badges">
                        <span
                          className="news-source-badge"
                          style={{ background: srcColor(featured) }}
                        >
                          {featured.source_name}
                        </span>
                        <span className="news-category-badge">
                          {CATEGORY_ICONS[featured.source_category] ?? ''}{' '}
                          {featured.source_category}
                        </span>
                      </div>
                      <h2 className="news-featured-title">{featured.title}</h2>
                      {featured.amin_summary && (
                        <p className="news-amin-quote">
                          Amin: {featured.amin_summary}
                        </p>
                      )}
                      <p className="news-featured-summary">
                        {featured.summary}
                      </p>
                      <span className="news-featured-time">
                        {relTime(featured.published_at)}
                      </span>
                      <div className="news-featured-actions">
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => setModalItem(featured)}
                        >
                          Read →
                        </button>
                        <button
                          className="btn btn-sm btn-outline"
                          onClick={() => askAmin(featured)}
                        >
                          Ask Amin
                        </button>
                        {featured.wiki_filed && featured.wiki_page_slug ? (
                          <WikiCitationChip slug={featured.wiki_page_slug} />
                        ) : (
                          <button
                            className="btn btn-sm btn-outline"
                            onClick={() => fileToWiki(featured)}
                            disabled={filingId === featured.id}
                          >
                            {filingId === featured.id ? '…' : 'File to Wiki'}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {/* ── ARTICLE GRID ── */}
              <motion.div
                className="news-grid"
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {gridItems.map(item => (
                  <motion.div
                    key={item.id}
                    className={`news-card${item.importance === 'high' ? ' news-card--high' : ''}`}
                    variants={staggerItem}
                    whileHover={tileMotion.hover}
                    whileTap={tileMotion.tap}
                  >
                    <div className="news-card-top">
                      <span
                        className="news-source-badge news-source-badge--sm"
                        style={{ background: srcColor(item) }}
                      >
                        {item.source_name}
                      </span>
                      <span className="news-card-cat">
                        {CATEGORY_ICONS[item.source_category] ?? ''}
                      </span>
                      <span className="news-card-time">
                        {relTime(item.published_at)}
                      </span>
                    </div>
                    <div className="news-card-body-row">
                      <div className="news-card-text">
                        <h3 className="news-card-title">{item.title}</h3>
                        <p className="news-card-summary">{item.summary}</p>
                      </div>
                      {item.image_url && (
                        <div className="news-card-thumb">
                          <Image
                            src={item.image_url}
                            alt=""
                            fill
                            sizes="80px"
                            unoptimized
                          />
                        </div>
                      )}
                    </div>
                    <div className="news-card-footer">
                      <button
                        className="news-card-btn"
                        onClick={() => setModalItem(item)}
                      >
                        Read
                      </button>
                      <button
                        className="news-card-btn"
                        onClick={() => askAmin(item)}
                        title="Ask Amin"
                      >
                        💬
                      </button>
                      {item.wiki_filed && item.wiki_page_slug ? (
                        <WikiCitationChip slug={item.wiki_page_slug} />
                      ) : (
                        <button
                          className="news-card-btn"
                          onClick={() => fileToWiki(item)}
                          disabled={filingId === item.id}
                          title="File to Wiki"
                        >
                          {filingId === item.id ? '…' : '+'}
                        </button>
                      )}
                    </div>
                  </motion.div>
                ))}
              </motion.div>

              {/* ── PAGINATION ── */}
              {items.length < total && (
                <div className="news-load-more">
                  <button
                    className="btn btn-outline btn-sm"
                    onClick={() => void loadMore()}
                  >
                    Load more
                  </button>
                  <span className="news-count">
                    Showing {items.length} of {total} items
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── ARTICLE MODAL ── */}
      <ArticleModal
        item={modalItem}
        onClose={() => setModalItem(null)}
        onWikiFiled={handleWikiFiled}
      />
    </div>
  );
}
