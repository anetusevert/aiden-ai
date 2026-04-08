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
  'JD Supra': 'rgba(255,255,255,0.9)',
  'JD Supra Commercial': 'rgba(255,255,255,0.88)',
  Jurist: 'rgba(255,255,255,0.86)',
  SCOTUSblog: 'rgba(255,255,255,0.84)',
  'Volokh Conspiracy': 'rgba(255,255,255,0.82)',
  'Law.com': 'rgba(255,255,255,0.8)',
  'ABA Journal': 'rgba(255,255,255,0.78)',
};

export function HomeNewsCard({ item, index }: HomeNewsCardProps) {
  const [imgError, setImgError] = useState(false);
  const sourceName = item.source_name ?? item.source ?? '';
  const accentColor = SOURCE_COLORS[sourceName] || 'rgba(255,255,255,0.9)';

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
          {/* External news images are passthrough URLs; keep img to avoid remote loader config. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
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
            {sourceName}
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
