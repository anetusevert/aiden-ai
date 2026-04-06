'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { apiClient, type WikiHealthResponse } from '@/lib/apiClient';

export function IntelligencePanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const [wikiHealth, setWikiHealth] = useState<WikiHealthResponse | null>(null);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  useEffect(() => {
    apiClient.getWikiHealth().then(setWikiHealth).catch(() => {});
  }, []);

  const wikiIssues = wikiHealth
    ? wikiHealth.contradiction_count + wikiHealth.stale_count
    : 0;

  return (
    <>
      <div className="r2-header">LEGAL INTELLIGENCE</div>

      <div className="r2-link-list">
        <Link
          href="/news"
          className={`r2-link${isActive('/news') ? ' r2-link-active' : ''}`}
          onClick={e => {
            e.preventDefault();
            navigateTo('/news');
          }}
        >
          <span className="r2-link-icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M5 6.5A2.5 2.5 0 0 1 7.5 4H20v13.5A2.5 2.5 0 0 1 17.5 20H7a3 3 0 0 1-3-3V6.5Z" />
              <path d="M8 8h8" />
              <path d="M8 12h8" />
              <path d="M8 16h5" />
            </svg>
          </span>
          <span className="r2-link-text">Legal Intelligence</span>
        </Link>

        <Link
          href="/global-legal"
          className={`r2-link${isActive('/global-legal') ? ' r2-link-active' : ''}`}
          onClick={e => {
            e.preventDefault();
            navigateTo('/global-legal');
          }}
        >
          <span className="r2-link-icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </span>
          <span className="r2-link-text">Global Legal Library</span>
        </Link>

        <div className="r2-divider" />

        <Link
          href="/wiki"
          className={`r2-link${isActive('/wiki') && !isActive('/wiki/log') ? ' r2-link-active' : ''}`}
          onClick={e => {
            e.preventDefault();
            navigateTo('/wiki');
          }}
        >
          <span className="r2-link-icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              <path d="M8 7h8" />
              <path d="M8 11h6" />
            </svg>
          </span>
          <span className="r2-link-text">Knowledge Wiki</span>
          {wikiIssues > 0 && (
            <span
              style={{
                marginLeft: 'auto',
                fontSize: 10,
                color: '#f59e0b',
                background: 'rgba(245,158,11,0.12)',
                border: '1px solid rgba(245,158,11,0.25)',
                borderRadius: 8,
                padding: '1px 6px',
              }}
            >
              {wikiIssues} issues
            </span>
          )}
        </Link>

        <Link
          href="/wiki/log"
          className={`r2-link${isActive('/wiki/log') ? ' r2-link-active' : ''}`}
          onClick={e => {
            e.preventDefault();
            navigateTo('/wiki/log');
          }}
        >
          <span className="r2-link-icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <polyline points="22,12 18,12 15,21 9,3 6,12 2,12" />
            </svg>
          </span>
          <span className="r2-link-text">Wiki Log</span>
        </Link>
      </div>
    </>
  );
}
