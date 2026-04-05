'use client';

import { useMemo } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { useNewsPolling } from '@/hooks/useNewsPolling';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';
import {
  fadeUp,
  staggerContainer,
  staggerItem,
  tileMotion,
} from '@/lib/motion';

function formatUpdatedAt(dateStr: string | null): string {
  if (!dateStr) return 'Just now';
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatPublished(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export default function NewsPage() {
  const { items, isLoading, error, fetchedAt, refresh } = useNewsPolling();
  const { user } = useAuth();
  const { navigateTo } = useNavigation();
  const isAdmin = user?.role === 'ADMIN';

  const featured = items[0];
  const highlights = useMemo(() => items.slice(1, 3), [items]);
  const feed = useMemo(() => items.slice(3), [items]);

  return (
    <motion.div className="news-page" {...fadeUp}>
      <div className="news-toolbar">
        <div className="news-toolbar-left">
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={() => void refresh()}
            disabled={isLoading}
          >
            {isLoading ? 'Updating...' : 'Update Feed'}
          </button>
          <span className="news-toolbar-updated">
            Last updated {formatUpdatedAt(fetchedAt)}
          </span>
        </div>
        {isAdmin && (
          <button
            type="button"
            className="btn btn-outline btn-sm news-toolbar-settings"
            onClick={() => navigateTo('/news/settings')}
            title="Configure news sources"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Sources
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {featured ? (
        <section className="news-feature-grid">
          <motion.a
            href={featured.url}
            target="_blank"
            rel="noopener noreferrer"
            className="news-feature-card"
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
          >
            <div className="news-feature-card-media">
              {featured.image_url ? (
                <Image
                  src={featured.image_url}
                  alt=""
                  fill
                  sizes="(max-width: 1024px) 100vw, 60vw"
                  unoptimized
                />
              ) : (
                <div className="news-feature-card-fallback">Amin</div>
              )}
            </div>
            <div className="news-feature-card-body">
              <div className="news-card-meta">
                <span className="news-card-source">{featured.source}</span>
                <span className="news-card-date">
                  {formatPublished(featured.published_at)}
                </span>
              </div>
              <h2 className="news-feature-card-title">{featured.title}</h2>
              <p className="news-feature-card-summary">{featured.summary}</p>
              <span className="news-card-link">Open original article</span>
            </div>
          </motion.a>

          <div className="news-highlight-column">
            {highlights.map(item => (
              <motion.a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="news-highlight-card"
                whileHover={tileMotion.hover}
                whileTap={tileMotion.tap}
              >
                <div className="news-card-meta">
                  <span className="news-card-source">{item.source}</span>
                  <span className="news-card-date">
                    {formatPublished(item.published_at)}
                  </span>
                </div>
                <h3 className="news-highlight-title">{item.title}</h3>
                <p className="news-highlight-summary">{item.summary}</p>
              </motion.a>
            ))}
          </div>
        </section>
      ) : null}

      {isLoading && items.length === 0 ? (
        <section className="news-feed-grid">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="news-feed-card news-feed-card-skeleton">
              <div className="news-feed-card-image home-skeleton-pulse" />
              <div className="news-feed-card-body">
                <div className="home-skeleton-line home-skeleton-pulse" />
                <div className="home-skeleton-line home-skeleton-pulse" />
                <div className="home-skeleton-line home-skeleton-line--medium home-skeleton-pulse" />
              </div>
            </div>
          ))}
        </section>
      ) : feed.length > 0 ? (
        <motion.section
          className="news-feed-grid"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {feed.map(item => (
            <motion.a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="news-feed-card"
              variants={staggerItem}
              whileHover={tileMotion.hover}
              whileTap={tileMotion.tap}
            >
              <div className="news-feed-card-image">
                {item.image_url ? (
                  <Image
                    src={item.image_url}
                    alt=""
                    fill
                    sizes="(max-width: 1024px) 100vw, 33vw"
                    unoptimized
                  />
                ) : (
                  <div className="news-feed-card-fallback">{item.source}</div>
                )}
              </div>
              <div className="news-feed-card-body">
                <div className="news-card-meta">
                  <span className="news-card-source">{item.source}</span>
                  <span className="news-card-date">
                    {formatPublished(item.published_at)}
                  </span>
                </div>
                <h3 className="news-feed-card-title">{item.title}</h3>
                <p className="news-feed-card-summary">{item.summary}</p>
                <span className="news-card-link">Read article</span>
              </div>
            </motion.a>
          ))}
        </motion.section>
      ) : !isLoading ? (
        <div className="news-empty-state">
          <h2>No news available right now</h2>
          <p>
            Trigger an update to pull the latest legal intelligence into this
            briefing room.
          </p>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => void refresh()}
          >
            Retry update
          </button>
        </div>
      ) : null}
    </motion.div>
  );
}
