'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';

export function AdminPanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const { user } = useAuth();

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

      {/* Administration */}
      <div className="r2-section">
        <div className="r2-section-label">ADMINISTRATION</div>
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
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </span>
            <span className="r2-link-text">Members</span>
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
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
                <line x1="12" y1="18" x2="12" y2="12" />
                <line x1="9" y1="15" x2="15" y2="15" />
              </svg>
            </span>
            <span className="r2-link-text">Audit Log</span>
          </Link>

          <Link
            href="/news/settings"
            className={`r2-link${isActive('/news/settings') ? ' r2-link-active' : ''}`}
            onClick={e => {
              e.preventDefault();
              navigateTo('/news/settings');
            }}
          >
            <span className="r2-link-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M4 11a9 9 0 0 1 9 9" />
                <path d="M4 4a16 16 0 0 1 16 16" />
                <circle cx="5" cy="19" r="1" />
              </svg>
            </span>
            <span className="r2-link-text">News Sources</span>
          </Link>
        </div>
      </div>

      {/* Platform Operator — only for platform admins */}
      {user.is_platform_admin && (
        <div className="r2-section">
          <div className="r2-section-label">PLATFORM OPERATOR</div>
          <div className="r2-link-list">
            <Link
              href="/operator/organisations"
              className={`r2-link${isActive('/operator/organisations') ? ' r2-link-active' : ''}`}
              onClick={e => {
                e.preventDefault();
                navigateTo('/operator/organisations');
              }}
            >
              <span className="r2-link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9,22 9,12 15,12 15,22" />
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
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </span>
              <span className="r2-link-text">All Users</span>
            </Link>

            <Link
              href="/operator/legal-corpus"
              className={`r2-link${isActive('/operator/legal-corpus') ? ' r2-link-active' : ''}`}
              onClick={e => {
                e.preventDefault();
                navigateTo('/operator/legal-corpus');
              }}
            >
              <span className="r2-link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  <path d="M8 7h8" />
                  <path d="M8 11h8" />
                  <path d="M8 15h5" />
                </svg>
              </span>
              <span className="r2-link-text">Legal Corpus</span>
            </Link>

            <Link
              href="/operator/knowledge-base"
              className={`r2-link${isActive('/operator/knowledge-base') ? ' r2-link-active' : ''}`}
              onClick={e => {
                e.preventDefault();
                navigateTo('/operator/knowledge-base');
              }}
            >
              <span className="r2-link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <ellipse cx="12" cy="5" rx="9" ry="3" />
                  <path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3" />
                  <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
                </svg>
              </span>
              <span className="r2-link-text">Knowledge Base</span>
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
