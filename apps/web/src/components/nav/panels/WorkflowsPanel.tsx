'use client';

import { useCallback, useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';
import {
  WORKFLOW_CATEGORIES,
  getGroupedWorkflows,
  type WorkflowCategory,
  type WorkflowCategoryMeta,
} from '@/lib/workflowRegistry';
import { getWorkflowCategoryHref } from '@/lib/workflowPresentation';

const CATEGORY_ICONS: Record<WorkflowCategory, React.ReactNode> = {
  litigation: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  ),
  corporate: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
    </svg>
  ),
  compliance: (
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
  ),
  employment: (
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
  ),
  arbitration: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </svg>
  ),
  enforcement: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12,6 12,12 16,14" />
    </svg>
  ),
  research: (
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
  ),
  management: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M12 20V10" />
      <path d="M18 20V4" />
      <path d="M6 20v-4" />
    </svg>
  ),
};

export function WorkflowsPanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const { appLanguage } = useAuth();

  const grouped = useMemo(() => getGroupedWorkflows(), []);

  const categoryName = useCallback(
    (cat: WorkflowCategoryMeta) => {
      if (appLanguage === 'ar') return cat.name_ar;
      return cat.name;
    },
    [appLanguage]
  );

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  return (
    <>
      <div className="r2-header">WORKFLOWS</div>
      <div className="r2-link-list">
        {WORKFLOW_CATEGORIES.map(cat => {
          const href = getWorkflowCategoryHref(cat.id);
          const count = grouped[cat.id]?.length ?? 0;
          return (
            <Link
              key={cat.id}
              href={href}
              className={`r2-link${isActive(href) ? ' r2-link-active' : ''}`}
              onClick={e => {
                e.preventDefault();
                navigateTo(href);
              }}
            >
              <span className="r2-link-icon">{CATEGORY_ICONS[cat.id]}</span>
              <span className="r2-link-text">{categoryName(cat)}</span>
              <span className="r2-count-badge">{count}</span>
            </Link>
          );
        })}
      </div>
    </>
  );
}
