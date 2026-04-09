'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';

function HarvesterIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <path d="M12 2v6" />
      <path d="M12 22v-4" />
      <path d="M4.93 4.93l4.24 4.24" />
      <path d="M14.83 14.83l4.24 4.24" />
      <path d="M2 12h6" />
      <path d="M16 12h6" />
      <path d="M4.93 19.07l4.24-4.24" />
      <path d="M14.83 9.17l4.24-4.24" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function BuildingIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <path d="M3 21h18" />
      <path d="M5 21V7l8-4v18" />
      <path d="M19 21V11l-6-4" />
      <path d="M9 9v.01" />
      <path d="M9 12v.01" />
      <path d="M9 15v.01" />
      <path d="M9 18v.01" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function BookIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <path d="M8 7h8" />
      <path d="M8 11h6" />
    </svg>
  );
}

export default function OperatorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user } = useAuth();
  const { navigateTo } = useNavigation();
  const tNav = useTranslations('nav');
  const isPlatformAdmin = user?.is_platform_admin === true;
  const isWorkspaceAdmin = user?.role === 'ADMIN';
  const isKnowledgeBaseRoute = pathname.startsWith('/operator/knowledge-base');

  if (!isPlatformAdmin && !(isWorkspaceAdmin && isKnowledgeBaseRoute)) {
    return <>{children}</>;
  }

  const links: {
    href: string;
    label: string;
    icon: React.ReactNode;
  }[] = isPlatformAdmin
    ? [
        {
          href: '/operator/organisations',
          label: tNav('organisations'),
          icon: <BuildingIcon />,
        },
        {
          href: '/operator/users',
          label: tNav('allUsers'),
          icon: <UsersIcon />,
        },
        {
          href: '/operator/legal-corpus',
          label: tNav('legalCorpus'),
          icon: <BookIcon />,
        },
        {
          href: '/operator/knowledge-base',
          label: tNav('knowledgeBase'),
          icon: <HarvesterIcon />,
        },
      ]
    : [
        {
          href: '/operator/knowledge-base',
          label: tNav('knowledgeBase'),
          icon: <HarvesterIcon />,
        },
      ];

  return (
    <>
      <nav className="operator-subnav" aria-label="Platform operator">
        <div className="operator-subnav-inner">
          {links.map(item => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`operator-subnav-link ${active ? 'operator-subnav-link-active' : ''}`}
                onClick={e => {
                  e.preventDefault();
                  navigateTo(item.href);
                }}
              >
                <span className="operator-subnav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
      {children}
      <style jsx>{`
        .operator-subnav {
          background: var(--bg-elevated, var(--card-bg, #1a1d24));
          border-bottom: 1px solid
            var(--border-color, rgba(255, 255, 255, 0.08));
          padding: 0 var(--space-6);
        }
        .operator-subnav-inner {
          max-width: 1400px;
          margin: 0 auto;
          display: flex;
          flex-wrap: wrap;
          gap: var(--space-1);
          padding: var(--space-3) 0;
        }
        .operator-subnav-link {
          display: inline-flex;
          align-items: center;
          gap: var(--space-2);
          padding: var(--space-2) var(--space-4);
          border-radius: var(--radius-md, 6px);
          font-size: var(--text-sm, 0.875rem);
          font-weight: var(--font-medium, 500);
          color: var(--text-muted, #9ca3af);
          text-decoration: none;
          transition:
            color 0.15s ease,
            background 0.15s ease;
        }
        .operator-subnav-link:hover {
          color: var(--foreground, #f3f4f6);
          background: var(--secondary-light, rgba(255, 255, 255, 0.04));
        }
        .operator-subnav-link-active {
          color: rgba(255, 255, 255, 0.95);
          background: rgba(255, 255, 255, 0.08);
        }
        .operator-subnav-icon {
          display: flex;
          opacity: 0.9;
        }
      `}</style>
    </>
  );
}
