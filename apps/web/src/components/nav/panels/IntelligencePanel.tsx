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
      </div>
    </>
  );
}
