'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import type { LegalNewsItem } from '@/lib/apiClient';
import { tileMotion } from '@/lib/motion';

interface HomeNewsCardProps {
  item: LegalNewsItem;
  index: number;
}

function timeAgo(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = Date.now();
    const diff = now - date.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

const SOURCE_COLORS: Record<string, string> = {
  'JD Supra': '#638cff',
  'JD Supra Commercial': '#34d399',
  Jurist: '#ff8c00',
  SCOTUSblog: '#a78bfa',
  'Volokh Conspiracy': '#f472b6',
  'Law.com': '#fbbf24',
  'ABA Journal': '#63b4ff',
};

export function HomeNewsCard({ item, index }: HomeNewsCardProps) {
  const [imgError, setImgError] = useState(false);
  const accentColor =
    SOURCE_COLORS[item.source] || 'var(--amin-accent, #d4a017)';

  return (
    <motion.a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="home-news-card"
      custom={index}
      initial={tileMotion.initial}
      animate={tileMotion.animate(index)}
      whileHover={tileMotion.hover}
      whileTap={tileMotion.tap}
    >
      {item.image_url && !imgError ? (
        <div className="home-news-card-img">
          <img
            src={item.image_url}
            alt=""
            loading="lazy"
            onError={() => setImgError(true)}
          />
        </div>
      ) : (
        <div className="home-news-card-img home-news-card-img--placeholder">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
          >
            <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
            <path d="M18 14h-8" />
            <path d="M15 18h-5" />
            <path d="M10 6h8v4h-8V6Z" />
          </svg>
        </div>
      )}

      <div className="home-news-card-body">
        <div className="home-news-card-meta">
          <span
            className="home-news-card-source"
            style={
              {
                '--source-color': accentColor,
              } as React.CSSProperties
            }
          >
            {item.source}
          </span>
          <span className="home-news-card-time">
            {timeAgo(item.published_at)}
          </span>
        </div>

        <h3 className="home-news-card-title">{item.title}</h3>

        {item.summary && (
          <p className="home-news-card-excerpt">{item.summary}</p>
        )}
      </div>
    </motion.a>
  );
}
