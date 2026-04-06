'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';

export function IntelligencePanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

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

        <Link
          href="/research"
          className={`r2-link${isActive('/research') ? ' r2-link-active' : ''}`}
          onClick={e => {
            e.preventDefault();
            navigateTo('/research');
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
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </span>
          <span className="r2-link-text">Legal Research</span>
        </Link>
      </div>
    </>
  );
}
