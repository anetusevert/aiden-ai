'use client';

import { useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { useSidebarWorkflows } from '@/hooks/useSidebarWorkflows';
import { getWorkflowHref } from '@/lib/workflowPresentation';
import { useAuth } from '@/lib/AuthContext';
import type { SoulDetail } from '@/lib/apiClient';
import type { WorkflowDefinition } from '@/lib/workflowRegistry';
import type { ScoredWorkflow } from '@/hooks/useSidebarWorkflows';

interface HomePanelProps {
  soul: SoulDetail | null;
}

function ForYouDot({ reason }: { reason: ScoredWorkflow['reason'] }) {
  if (reason === 'default') return null;
  const colors: Record<string, string> = {
    twin_match: '#d4a017',
    frequent: '#6366f1',
    recent: '#64748b',
  };
  return (
    <span className="r2-foryou-dot" style={{ background: colors[reason] }} />
  );
}

function timeAgo(ts: number) {
  const mins = Math.floor((Date.now() - ts) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function HomePanel({ soul }: HomePanelProps) {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const { appLanguage } = useAuth();
  const { forYou, continueItems, trackAccess } = useSidebarWorkflows(soul);

  const displayName = useCallback(
    (wf: WorkflowDefinition) => {
      if (appLanguage === 'ar') return wf.name_ar;
      return wf.name;
    },
    [appLanguage]
  );

  const handleClick = useCallback(
    (e: React.MouseEvent, wf: WorkflowDefinition) => {
      e.preventDefault();
      trackAccess(wf.id);
      navigateTo(getWorkflowHref(wf));
    },
    [trackAccess, navigateTo]
  );

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  return (
    <>
      {/* FOR YOU */}
      {forYou.length > 0 && (
        <div className="r2-section">
          <div className="r2-section-label r2-section-label-gold">
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="currentColor"
              stroke="none"
            >
              <path d="M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 4.3 2.4-7.4L2 9.4h7.6z" />
            </svg>
            FOR YOU
          </div>
          <div className="r2-link-list">
            {forYou.slice(0, 4).map(scored => {
              const href = getWorkflowHref(scored.workflow);
              return (
                <Link
                  key={scored.workflow.id}
                  href={href}
                  className={`r2-link${isActive(href) ? ' r2-link-active' : ''}`}
                  onClick={e => handleClick(e, scored.workflow)}
                >
                  <span className="r2-link-text">
                    {displayName(scored.workflow)}
                  </span>
                  <ForYouDot reason={scored.reason} />
                </Link>
              );
            })}
          </div>
          {forYou.length > 4 && (
            <Link
              href="/home"
              className="r2-see-all"
              onClick={e => {
                e.preventDefault();
                navigateTo('/home');
              }}
            >
              See all
            </Link>
          )}
        </div>
      )}

      {/* CONTINUE */}
      {continueItems.length > 0 && (
        <div className="r2-section">
          <div className="r2-section-label">
            <svg
              width="10"
              height="10"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            CONTINUE
          </div>
          <div className="r2-link-list">
            {continueItems.slice(0, 4).map(item => {
              const href = getWorkflowHref(item.workflow);
              return (
                <Link
                  key={item.workflow.id}
                  href={href}
                  className={`r2-link r2-link-stacked${isActive(href) ? ' r2-link-active' : ''}`}
                  onClick={e => handleClick(e, item.workflow)}
                >
                  <span className="r2-link-text">
                    {displayName(item.workflow)}
                  </span>
                  <span className="r2-link-meta">
                    {timeAgo(item.lastAccessedAt)}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
