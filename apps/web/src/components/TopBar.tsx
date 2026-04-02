'use client';

import { usePathname } from 'next/navigation';
import { AccountMenu } from './AccountMenu';
import { useAuth } from '@/lib/AuthContext';

const ROUTE_LABELS: Record<string, string> = {
  '/documents': 'Documents',
  '/research': 'Research',
  '/contract-review': 'Contract Review',
  '/clause-redlines': 'Clause Redlines',
  '/conversations': 'Conversations',
  '/global-legal': 'Global Legal Library',
  '/members': 'Members',
  '/audit': 'Audit Log',
  '/account': 'Account',
  '/account/twin': 'My AI Profile',
  '/operator/organisations': 'Organisations',
  '/operator/users': 'All Users',
  '/operator/legal-corpus': 'Legal Corpus',
};

function getBreadcrumb(pathname: string): { parent?: string; current: string } {
  const exact = ROUTE_LABELS[pathname];
  if (exact) return { current: exact };

  for (const [route, label] of Object.entries(ROUTE_LABELS)) {
    if (pathname.startsWith(route + '/')) {
      const rest = pathname.slice(route.length + 1);
      const segment = rest.split('/')[0];
      const subLabel =
        segment.length > 12 ? segment.slice(0, 12) + '…' : segment;
      return { parent: label, current: subLabel };
    }
  }

  return { current: 'HeyAmin' };
}

interface TopBarProps {
  onToggleSidebar: () => void;
  sidebarCollapsed: boolean;
}

export function TopBar({ onToggleSidebar, sidebarCollapsed }: TopBarProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const breadcrumb = getBreadcrumb(pathname);

  if (!user) return null;

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="topbar-sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            style={{
              transform: sidebarCollapsed ? 'scaleX(-1)' : 'none',
              transition: 'transform 200ms ease',
            }}
          >
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <line x1="9" y1="3" x2="9" y2="21" />
            <path d="M14 9l-3 3 3 3" />
          </svg>
        </button>

        <nav className="topbar-breadcrumb" aria-label="Breadcrumb">
          {breadcrumb.parent && (
            <>
              <span className="topbar-breadcrumb-parent">
                {breadcrumb.parent}
              </span>
              <span className="topbar-breadcrumb-sep">
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="9,6 15,12 9,18" />
                </svg>
              </span>
            </>
          )}
          <span className="topbar-breadcrumb-current">
            {breadcrumb.current}
          </span>
        </nav>
      </div>

      <div className="topbar-right">
        <AccountMenu />
      </div>
    </header>
  );
}
