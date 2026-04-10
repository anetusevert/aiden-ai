'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';

export function KnowledgePanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const { user } = useAuth();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  if (user?.role !== 'ADMIN') {
    return (
      <>
        <div className="r2-header">KNOWLEDGE BASE</div>
        <div className="r2-empty">
          <p className="r2-empty-text">Admin access required</p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="r2-header">KNOWLEDGE BASE</div>

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

        <Link
          href="/documents"
          className={`r2-link${isActive('/documents') ? ' r2-link-active' : ''}`}
          onClick={e => {
            e.preventDefault();
            navigateTo('/documents');
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
              <path d="M7 3h8l4 4v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" />
              <path d="M15 3v5h5" />
            </svg>
          </span>
          <span className="r2-link-text">Documents</span>
        </Link>
      </div>
    </>
  );
}
