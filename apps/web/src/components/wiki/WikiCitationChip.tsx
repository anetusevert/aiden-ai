'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/apiClient';
import { useNavigation } from '@/components/NavigationLoader';

interface WikiCitationChipProps {
  slug: string;
}

export function WikiCitationChip({ slug }: WikiCitationChipProps) {
  const { navigateTo } = useNavigation();
  const [title, setTitle] = useState<string | null>(null);
  const [summary, setSummary] = useState<string>('');
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    apiClient
      .getWikiPage(slug)
      .then(page => {
        setTitle(page.title);
        setSummary(page.summary);
      })
      .catch(() => setNotFound(true));
  }, [slug]);

  if (notFound) {
    return <span style={{ color: 'var(--text-muted)' }}>[[{slug}]]</span>;
  }

  return (
    <button
      className="wiki-citation-chip"
      onClick={() => navigateTo(`/wiki/${slug}`)}
      title={summary || slug}
    >
      <span style={{ fontSize: 12 }}>📄</span>
      <span>{title || slug}</span>
    </button>
  );
}

/**
 * Transform text containing [[slug]] patterns into React nodes
 * with WikiCitationChip components inline.
 */
export function renderWikiLinks(text: string): React.ReactNode[] {
  const parts = text.split(/(\[\[[a-z0-9-]+\]\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[\[([a-z0-9-]+)\]\]$/);
    if (match) {
      return <WikiCitationChip key={i} slug={match[1]} />;
    }
    return <span key={i}>{part}</span>;
  });
}
