'use client';

import { useMemo } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { AccountMenu } from './AccountMenu';
import { useAuth } from '@/lib/AuthContext';
import {
  getCategoryMeta,
  getWorkflowById,
  type WorkflowCategory,
} from '@/lib/workflowRegistry';

function getBreadcrumb(
  pathname: string,
  routeLabels: Record<string, string>,
  fallback: string,
  workflowId: string | null
): { parent?: string; current: string } {
  if (pathname === '/home') {
    return { current: 'Home' };
  }

  if (pathname === '/news') {
    return { parent: 'Reference', current: 'Legal Intelligence' };
  }

  if (pathname.startsWith('/workflows/')) {
    const segments = pathname.split('/').filter(Boolean);
    const category = segments[1] as WorkflowCategory | undefined;
    const workflow = segments[2] ? getWorkflowById(segments[2]) : undefined;
    const categoryLabel = category
      ? getCategoryMeta(category)?.name
      : undefined;

    if (workflow) {
      return {
        parent: categoryLabel || 'Workflows',
        current: workflow.name,
      };
    }

    if (categoryLabel) {
      return {
        parent: 'Workflows',
        current: categoryLabel,
      };
    }
  }

  if (workflowId) {
    const workflow = getWorkflowById(workflowId);
    const routeLabel = routeLabels[pathname];
    if (workflow && routeLabel) {
      return {
        parent: workflow.name,
        current: routeLabel,
      };
    }
  }

  const exact = routeLabels[pathname];
  if (exact) return { current: exact };

  for (const [route, label] of Object.entries(routeLabels)) {
    if (pathname.startsWith(route + '/')) {
      const rest = pathname.slice(route.length + 1);
      const segment = rest.split('/')[0];
      const subLabel =
        segment.length > 12 ? segment.slice(0, 12) + '…' : segment;
      return { parent: label, current: subLabel };
    }
  }

  return { current: fallback };
}

export function TopBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const t = useTranslations('breadcrumbs');
  const tCommon = useTranslations('common');
  const { user } = useAuth();

  const routeLabels = useMemo(
    () => ({
      '/home': 'Home',
      '/news': 'Legal Intelligence',
      '/documents': t('documents'),
      '/research': t('research'),
      '/contract-review': t('contractReview'),
      '/clause-redlines': t('clauseRedlines'),
      '/conversations': t('conversations'),
      '/global-legal': t('globalLegal'),
      '/members': t('members'),
      '/audit': t('audit'),
      '/account/amin': t('accountAmin'),
      '/account/twin': t('accountTwin'),
      '/account': t('account'),
      '/operator/organisations': t('operatorOrganisations'),
      '/operator/users': t('operatorUsers'),
      '/operator/legal-corpus': t('operatorLegalCorpus'),
      '/operator/knowledge-base': t('operatorKnowledgeBase'),
    }),
    [t]
  );

  const breadcrumb = getBreadcrumb(
    pathname,
    routeLabels,
    t('heyamin'),
    searchParams.get('workflow')
  );

  if (!user) return null;

  return (
    <header className="topbar">
      <div className="topbar-left">
        <nav
          className="topbar-breadcrumb"
          aria-label={tCommon('breadcrumbNav')}
        >
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
