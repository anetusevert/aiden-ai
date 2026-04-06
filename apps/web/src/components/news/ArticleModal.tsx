'use client';

import { useState, useCallback, useEffect } from 'react';
import Image from 'next/image';
import { motion, AnimatePresence } from 'framer-motion';
import { glassReveal, glassBackdrop } from '@/lib/motion';
import { apiClient, type LegalNewsItem } from '@/lib/apiClient';
import { WikiCitationChip } from '@/components/wiki/WikiCitationChip';
import { useAminContext } from '@/components/amin/AminProvider';
import { reportScreenContext } from '@/lib/screenContext';
import { SOURCE_COLORS, CATEGORY_ICONS } from './constants';

interface ArticleModalProps {
  item: LegalNewsItem | null;
  onClose: () => void;
  onWikiFiled?: (itemId: string, slug: string) => void;
}

export function ArticleModal({
  item,
  onClose,
  onWikiFiled,
}: ArticleModalProps) {
  const { openPanel } = useAminContext();
  const [filing, setFiling] = useState(false);
  const [filed, setFiled] = useState(false);
  const [filedSlug, setFiledSlug] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (item) {
      setFiled(item.wiki_filed);
      setFiledSlug(item.wiki_page_slug ?? null);
      reportScreenContext({
        route: '/news',
        page_title: 'Legal Intelligence',
        document: null,
        ui_state: {
          reading_article: {
            title: item.title,
            source: item.source_name,
            category: item.source_category,
            importance: item.importance,
            wiki_filed: item.wiki_filed,
          },
        },
      });
    }
  }, [item]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const handleFileToWiki = useCallback(async () => {
    if (!item || filing || filed) return;
    setFiling(true);
    try {
      const res = await apiClient.fileNewsToWiki(item.id);
      setFiled(true);
      setFiledSlug(res.wiki_page_slug);
      onWikiFiled?.(item.id, res.wiki_page_slug);
    } catch {
      // silent
    } finally {
      setFiling(false);
    }
  }, [item, filing, filed, onWikiFiled]);

  const handleAskAmin = useCallback(() => {
    if (!item) return;
    onClose();
    openPanel();
    setTimeout(() => {
      window.dispatchEvent(
        new CustomEvent('amin-prefill', {
          detail: {
            text: `I'm reading: ${item.title} from ${item.source_name}. `,
          },
        })
      );
    }, 200);
  }, [item, onClose, openPanel]);

  const handleCopy = useCallback(() => {
    if (!item) return;
    navigator.clipboard.writeText(item.url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [item]);

  const srcColor =
    SOURCE_COLORS[item?.source_category ?? ''] ?? 'var(--text-muted)';

  return (
    <AnimatePresence>
      {item && (
        <motion.div
          className="article-modal"
          {...glassBackdrop}
          onClick={onClose}
        >
          <motion.div
            className="article-modal-content"
            {...glassReveal}
            onClick={e => e.stopPropagation()}
          >
            {/* Header */}
            <div className="article-modal-header">
              <div className="article-modal-badges">
                <span
                  className="news-source-badge"
                  style={{ background: srcColor }}
                >
                  {item.source_name}
                </span>
                <span className="news-jurisdiction-badge">
                  {item.jurisdiction}
                </span>
                <span className="news-category-badge">
                  {CATEGORY_ICONS[item.source_category] ?? '📰'}{' '}
                  {item.source_category}
                </span>
              </div>
              <h2 className="article-modal-title">{item.title}</h2>
              <p className="article-modal-meta">
                {formatRelativeTime(item.published_at)} · By {item.source_name}
              </p>
              <button
                className="article-modal-close"
                onClick={onClose}
                aria-label="Close"
              >
                ×
              </button>
            </div>

            {/* Scrollable content */}
            <div className="article-modal-body">
              {item.image_url && (
                <div className="article-modal-hero">
                  <Image
                    src={item.image_url}
                    alt=""
                    fill
                    sizes="720px"
                    unoptimized
                  />
                </div>
              )}

              {item.amin_summary && (
                <div className="article-modal-amin-take">
                  <span className="article-modal-amin-icon">⚡</span>
                  <span>
                    <strong>Amin&apos;s take:</strong> {item.amin_summary}
                  </span>
                </div>
              )}

              <p className="article-modal-summary">
                {item.summary || 'No summary available.'}
              </p>

              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="article-modal-read-link"
              >
                Read full article →
              </a>
            </div>

            {/* Footer */}
            <div className="article-modal-footer">
              <button
                className="btn btn-outline btn-sm"
                onClick={handleAskAmin}
              >
                Ask Amin about this
              </button>

              {filed || item.wiki_filed ? (
                <WikiCitationChip
                  slug={filedSlug || item.wiki_page_slug || ''}
                />
              ) : (
                <button
                  className="btn btn-outline btn-sm"
                  onClick={handleFileToWiki}
                  disabled={filing}
                >
                  {filing ? (
                    <span className="spinner spinner-sm" />
                  ) : (
                    'File to Wiki'
                  )}
                </button>
              )}

              <button className="btn btn-outline btn-sm" onClick={handleCopy}>
                {copied ? '✓ Copied' : 'Copy link'}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}
