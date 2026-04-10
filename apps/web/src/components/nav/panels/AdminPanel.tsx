'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';

export function AdminPanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const { user } = useAuth();
  const isPlatformAdmin = user?.is_platform_admin === true;

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  if (user?.role !== 'ADMIN') {
    return (
      <>
        <div className="r2-header">ADMIN</div>
        <div className="r2-empty">
          <p className="r2-empty-text">Admin access required</p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="r2-header">ADMIN</div>

      <div className="r2-section">
        <div className="r2-section-label">KNOWLEDGE BASE</div>
        <div className="r2-link-list">
          <Link
            href="/knowledge-base"
            className={`r2-link${isActive('/knowledge-base') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/knowledge-base');
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
                <ellipse cx="12" cy="5" rx="9" ry="3" />
                <path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3" />
                <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
              </svg>
            </span>
            <span className="r2-link-text">Knowledge Base</span>
          </Link>
        </div>
      </div>

      <div className="r2-section">
        <div className="r2-section-label">ORGANISATION</div>
        <div className="r2-link-list">
          <Link
            href="/members"
            className={`r2-link${isActive('/members') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/members');
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
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </span>
            <span className="r2-link-text">Members & Orgs</span>
          </Link>

          {isPlatformAdmin ? (
            <>
              <Link
                href="/operator/organisations"
                className={`r2-link${isActive('/operator/organisations') ? ' r2-link-active' : ''}`}
                onClick={e => {
                  e.preventDefault();
                  navigateTo('/operator/organisations');
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
                    <path d="M3 21h18" />
                    <path d="M5 21V7l8-4v18" />
                    <path d="M19 21V11l-6-4" />
                    <path d="M9 9v.01" />
                    <path d="M9 12v.01" />
                    <path d="M9 15v.01" />
                    <path d="M9 18v.01" />
                  </svg>
                </span>
                <span className="r2-link-text">Organisations</span>
              </Link>

              <Link
                href="/operator/users"
                className={`r2-link${isActive('/operator/users') ? ' r2-link-active' : ''}`}
                onClick={e => {
                  e.preventDefault();
                  navigateTo('/operator/users');
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
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </span>
                <span className="r2-link-text">All Users</span>
              </Link>
            </>
          ) : null}
        </div>
      </div>

      <div className="r2-section">
        <div className="r2-section-label">NEWS</div>
        <div className="r2-link-list">
          <Link
            href="/news/settings"
            className={`r2-link${isActive('/news/settings') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/news/settings');
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
                <path d="M4 11a9 9 0 0 1 9 9" />
                <path d="M4 4a16 16 0 0 1 16 16" />
                <circle cx="5" cy="19" r="1" />
              </svg>
            </span>
            <span className="r2-link-text">News Sources</span>
          </Link>
        </div>
      </div>

      <div className="r2-section">
        <div className="r2-section-label">SYSTEM</div>
        <div className="r2-link-list">
          <Link
            href="/settings/demo-data"
            className={`r2-link${isActive('/settings/demo-data') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/settings/demo-data');
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
                <path d="M4 19h16" />
                <path d="M5 17V7l7-4 7 4v10" />
                <path d="M9 11h6" />
                <path d="M9 15h4" />
              </svg>
            </span>
            <span className="r2-link-text">Demo Data</span>
          </Link>

          <Link
            href="/settings"
            className={`r2-link${isActive('/settings') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/settings');
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
                <path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z" />
                <circle cx="12" cy="15" r="2" />
              </svg>
            </span>
            <span className="r2-link-text">API Keys & LLM</span>
          </Link>

          <Link
            href="/audit"
            className={`r2-link${isActive('/audit') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/audit');
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
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
            </span>
            <span className="r2-link-text">Audit Logs</span>
          </Link>
        </div>
      </div>
    </>
  );
}
