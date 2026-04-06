'use client';

import { useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';
import { useSidebarWorkflows } from '@/hooks/useSidebarWorkflows';
import { useNewsPolling } from '@/hooks/useNewsPolling';
import {
  WORKFLOW_CATEGORIES,
  type WorkflowDefinition,
  type WorkflowCategory,
  type WorkflowCategoryMeta,
} from '@/lib/workflowRegistry';
import {
  staggerContainer,
  staggerItem,
  tileMotion,
  fadeUp,
  letterReveal,
} from '@/lib/motion';
import {
  getWorkflowCategoryHref,
  getWorkflowHref,
} from '@/lib/workflowPresentation';

// ---------------------------------------------------------------------------
// Greeting helper
// ---------------------------------------------------------------------------

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function getFormattedDate(): string {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}

// ---------------------------------------------------------------------------
// Category icons (matching Sidebar)
// ---------------------------------------------------------------------------

const CATEGORY_ICONS: Record<WorkflowCategory, React.ReactNode> = {
  litigation: (
    <svg
      width="22"
      height="22"
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
      width="22"
      height="22"
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
      width="22"
      height="22"
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
      width="22"
      height="22"
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
      width="22"
      height="22"
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
      width="22"
      height="22"
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
      width="22"
      height="22"
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
      width="22"
      height="22"
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

const CATEGORY_COLORS: Record<WorkflowCategory, string> = {
  litigation: '#638cff',
  corporate: '#34d399',
  compliance: '#a78bfa',
  employment: '#fbbf24',
  arbitration: '#f472b6',
  enforcement: '#f97316',
  research: '#63b4ff',
  management: '#94a3b8',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ForYouBadge({ reason }: { reason: string }) {
  if (reason === 'default') return null;
  const labels: Record<string, string> = {
    twin_match: 'Twin Match',
    frequent: 'Frequent',
    recent: 'Recent',
  };
  return (
    <span className={`home-foryou-badge home-foryou-badge--${reason}`}>
      {labels[reason] || ''}
    </span>
  );
}

function WorkflowItemIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <polyline points="4,17 10,11 4,5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function timeAgo(ts: number): string {
  const mins = Math.floor((Date.now() - ts) / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function getNewsUpdatedLabel(dateStr: string | null): string {
  if (!dateStr) return 'Live updates available';
  return `Updated ${new Date(dateStr).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  })}`;
}

export default function HomePage() {
  const { user, appLanguage } = useAuth();
  const { navigateTo } = useNavigation();
  const tNav = useTranslations('nav');
  const tWf = useTranslations('workflows');
  const tSb = useTranslations('sidebar');

  const { forYou, continueItems, allGroups, trackAccess } =
    useSidebarWorkflows(null);

  const {
    items: newsItems,
    isLoading: newsLoading,
  } = useNewsPolling();

  const greeting = useMemo(() => getGreeting(), []);
  const dateStr = useMemo(() => getFormattedDate(), []);
  const firstName = user?.full_name?.split(' ')[0] || '';

  const workflowDisplayName = useCallback(
    (wf: WorkflowDefinition) => {
      if (appLanguage === 'ar') return wf.name_ar;
      if (appLanguage === 'en') return wf.name;
      return tWf(wf.id);
    },
    [appLanguage, tWf]
  );

  const categoryDisplayName = useCallback(
    (cat: WorkflowCategoryMeta) => {
      if (appLanguage === 'ar') return cat.name_ar;
      if (appLanguage === 'en') return cat.name;
      return cat.name;
    },
    [appLanguage]
  );

  const handleWorkflowClick = useCallback(
    (wf: WorkflowDefinition) => {
      trackAccess(wf.id);
      navigateTo(getWorkflowHref(wf));
    },
    [trackAccess, navigateTo]
  );

  const categoryWorkflowCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const group of allGroups) {
      counts[group.category.id] = group.workflows.length;
    }
    return counts;
  }, [allGroups]);

  return (
    <div className="home-page">
      <div className="home-page-backdrop" aria-hidden />

      <div className="home-page-content">
        {/* ── GREETING ── */}
        <motion.header className="home-greeting" {...fadeUp}>
          <div className="home-greeting-row">
            <div>
              <p className="home-greeting-date">{dateStr}</p>
              <h1 className="home-greeting-headline">
                {greeting}
                {firstName && (
                  <>
                    ,{' '}
                    <span className="home-greeting-name">
                      {firstName.split('').map((char, i) => (
                        <motion.span
                          key={i}
                          custom={i}
                          variants={letterReveal}
                          initial="hidden"
                          animate="visible"
                          style={{ display: 'inline-block' }}
                        >
                          {char}
                        </motion.span>
                      ))}
                    </span>
                  </>
                )}
              </h1>
            </div>

            <button
              type="button"
              className="home-news-entry-button"
              onClick={() => navigateTo('/news')}
            >
              <span className="home-news-entry-button-kicker">
                Legal Intelligence
              </span>
              <span className="home-news-entry-button-title">
                Open live news room
              </span>
              <span className="home-news-entry-button-meta">
                {newsLoading
                  ? 'Refreshing feed...'
                  : `${newsItems.length} stories · ${getNewsUpdatedLabel(null)}`}
              </span>
            </button>
          </div>
        </motion.header>

        {/* ── FOR YOU ── */}
        {forYou.length > 0 && (
          <section className="home-section">
            <motion.h2
              className="home-section-label"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
            >
              {tSb('forYou')}
            </motion.h2>
            <motion.div
              className="home-foryou-row"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {forYou.map(scored => (
                <motion.button
                  key={scored.workflow.id}
                  className="home-foryou-tile"
                  variants={staggerItem}
                  whileHover={tileMotion.hover}
                  whileTap={tileMotion.tap}
                  onClick={() => handleWorkflowClick(scored.workflow)}
                >
                  <span className="home-foryou-tile-icon">
                    <WorkflowItemIcon />
                  </span>
                  <span className="home-foryou-tile-name">
                    {workflowDisplayName(scored.workflow)}
                  </span>
                  <ForYouBadge reason={scored.reason} />
                </motion.button>
              ))}
            </motion.div>
          </section>
        )}

        {/* ── CONTINUE ── */}
        {continueItems.length > 0 && (
          <section className="home-section">
            <motion.h2
              className="home-section-label"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.25 }}
            >
              {tSb('continue')}
            </motion.h2>
            <motion.div
              className="home-continue-row"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {continueItems.map(item => (
                <motion.button
                  key={item.workflow.id}
                  className="home-continue-pill"
                  variants={staggerItem}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => handleWorkflowClick(item.workflow)}
                >
                  <span className="home-continue-pill-name">
                    {workflowDisplayName(item.workflow)}
                  </span>
                  <span className="home-continue-pill-time">
                    {timeAgo(item.lastAccessedAt)}
                  </span>
                </motion.button>
              ))}
            </motion.div>
          </section>
        )}

        {/* ── WORKFLOWS ── */}
        <section className="home-section">
          <motion.h2
            className="home-section-label"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {tSb('allWorkflows')}
          </motion.h2>
          <motion.div
            className="home-workflows-grid"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {WORKFLOW_CATEGORIES.map(cat => {
              const color = CATEGORY_COLORS[cat.id];
              const count = categoryWorkflowCounts[cat.id] || 0;

              return (
                <motion.button
                  key={cat.id}
                  className="home-workflow-tile"
                  variants={staggerItem}
                  whileHover={tileMotion.hover}
                  whileTap={tileMotion.tap}
                  style={{ '--tile-accent': color } as React.CSSProperties}
                  onClick={() => navigateTo(getWorkflowCategoryHref(cat.id))}
                >
                  <span className="home-workflow-tile-icon">
                    {CATEGORY_ICONS[cat.id]}
                  </span>
                  <span className="home-workflow-tile-name">
                    {categoryDisplayName(cat)}
                  </span>
                  <span className="home-workflow-tile-count">
                    {count} workflow{count !== 1 ? 's' : ''}
                  </span>
                </motion.button>
              );
            })}
          </motion.div>
        </section>

        {/* ── REFERENCES ── */}
        <section className="home-section">
          <motion.h2
            className="home-section-label"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 }}
          >
            {tSb('reference')}
          </motion.h2>
          <motion.button
            className="home-reference-card"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.4, ease: [0.2, 0.8, 0.2, 1] }}
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
            onClick={() => navigateTo('/global-legal')}
          >
            <span className="home-reference-card-icon">
              <svg
                width="26"
                height="26"
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
            <div className="home-reference-card-text">
              <span className="home-reference-card-title">
                {tNav('globalLegalLibrary')}
              </span>
              <span className="home-reference-card-sub">
                Browse statutes, regulations, and legal instruments
              </span>
            </div>
            <span className="home-reference-card-arrow">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <polyline points="9,18 15,12 9,6" />
              </svg>
            </span>
          </motion.button>

          <motion.button
            className="home-reference-card"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              delay: 0.45,
              duration: 0.4,
              ease: [0.2, 0.8, 0.2, 1],
            }}
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
            onClick={() => navigateTo('/documents')}
          >
            <span className="home-reference-card-icon">
              <svg
                width="26"
                height="26"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10,9 9,9 8,9" />
              </svg>
            </span>
            <div className="home-reference-card-text">
              <span className="home-reference-card-title">Document Vault</span>
              <span className="home-reference-card-sub">
                Securely manage and index your legal documents
              </span>
            </div>
            <span className="home-reference-card-arrow">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <polyline points="9,18 15,12 9,6" />
              </svg>
            </span>
          </motion.button>

          <motion.button
            className="home-reference-card home-reference-card--news"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4, ease: [0.2, 0.8, 0.2, 1] }}
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
            onClick={() => navigateTo('/news')}
          >
            <span className="home-reference-card-icon">
              <svg
                width="26"
                height="26"
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
            <div className="home-reference-card-text">
              <span className="home-reference-card-title">
                Legal Intelligence
              </span>
              <span className="home-reference-card-sub">
                {newsLoading
                  ? 'Refreshing current legal developments'
                  : `${newsItems.length} source-linked stories · ${getNewsUpdatedLabel(
                      null
                    )}`}
              </span>
            </div>
            <span className="home-reference-card-arrow">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <polyline points="9,18 15,12 9,6" />
              </svg>
            </span>
          </motion.button>
        </section>
      </div>
    </div>
  );
}
