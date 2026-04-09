'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { resolveApiUrl } from '@/lib/api';
import { useAminContext } from '@/components/amin/AminProvider';
import { AminAvatar } from '@/components/amin/AminAvatar';
import type { AminAvatarState } from '@/components/amin/AminAvatar';
import {
  WORKFLOW_CATEGORIES,
  type WorkflowCategory,
} from '@/lib/workflowRegistry';
import { getWorkflowCategoryHref } from '@/lib/workflowPresentation';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CaseBrief {
  id: string;
  title: string;
  status: string;
  priority: string;
  practice_area: string;
  next_deadline: string | null;
  client_display_name: string;
  urgent: boolean;
}

interface DashboardData {
  active_cases: number;
  high_priority: number;
  due_today: CaseBrief[];
  due_this_week: CaseBrief[];
  recently_accessed: CaseBrief[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type TabId = 'clients' | 'cases' | 'workflows' | 'documents' | 'intelligence';

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  {
    id: 'clients',
    label: 'Clients',
    icon: (
      <svg
        width="18"
        height="18"
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
  },
  {
    id: 'cases',
    label: 'Cases',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      </svg>
    ),
  },
  {
    id: 'workflows',
    label: 'Workflows',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path d="M7 3h8l4 4v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" />
        <path d="M15 3v5h5" />
        <path d="M9 13h6" />
        <path d="M9 17h6" />
      </svg>
    ),
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    icon: (
      <svg
        width="18"
        height="18"
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
    ),
  },
];

const CATEGORY_ICONS: Record<WorkflowCategory, React.ReactNode> = {
  litigation: (
    <svg
      width="18"
      height="18"
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
      width="18"
      height="18"
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
      width="18"
      height="18"
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
      width="18"
      height="18"
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
      width="18"
      height="18"
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
      width="18"
      height="18"
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
      width="18"
      height="18"
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
      width="18"
      height="18"
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

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#6b7280',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function avatarStateFromVoice(
  voiceMode: string,
  aminStatus: string
): AminAvatarState {
  if (voiceMode === 'active') {
    if (aminStatus === 'listening') return 'listening';
    if (aminStatus === 'thinking') return 'thinking';
    if (aminStatus === 'speaking') return 'speaking';
    return 'listening';
  }
  return 'idle';
}

// ---------------------------------------------------------------------------
// Tab content components
// ---------------------------------------------------------------------------

function ClientsTab() {
  const router = useRouter();
  return (
    <motion.div
      className="hp-tab-items"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      <button className="hp-quick-link" onClick={() => router.push('/clients')}>
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
        </svg>
        <span>View All Clients</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
      <button
        className="hp-quick-link"
        onClick={() => router.push('/clients?action=new')}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
        >
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        <span>New Client</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
    </motion.div>
  );
}

function CasesTab({
  cases,
  onCaseClick,
}: {
  cases: CaseBrief[];
  onCaseClick: (c: CaseBrief) => void;
}) {
  const router = useRouter();
  return (
    <motion.div
      className="hp-tab-items"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      {cases.slice(0, 5).map(c => (
        <button
          key={c.id}
          className="hp-quick-link hp-quick-link--case"
          onClick={() => onCaseClick(c)}
        >
          <span
            className="hp-case-priority"
            style={{ background: PRIORITY_COLORS[c.priority] || '#6b7280' }}
          />
          <div className="hp-quick-link-body">
            <span className="hp-quick-link-title">{c.title}</span>
            <span className="hp-quick-link-sub">{c.client_display_name}</span>
          </div>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            className="hp-quick-link-arrow"
          >
            <polyline points="9,18 15,12 9,6" />
          </svg>
        </button>
      ))}
      <button className="hp-quick-link" onClick={() => router.push('/cases')}>
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
        <span>View All Cases</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
    </motion.div>
  );
}

function WorkflowsTab() {
  const router = useRouter();
  return (
    <motion.div
      className="hp-tab-items hp-tab-items--grid"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      {WORKFLOW_CATEGORIES.map(cat => (
        <button
          key={cat.id}
          className="hp-wf-tile"
          onClick={() => router.push(getWorkflowCategoryHref(cat.id))}
        >
          <span className="hp-wf-tile-icon">{CATEGORY_ICONS[cat.id]}</span>
          <span className="hp-wf-tile-name">{cat.name}</span>
        </button>
      ))}
    </motion.div>
  );
}

function DocumentsTab() {
  const router = useRouter();
  return (
    <motion.div
      className="hp-tab-items"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      <button
        className="hp-quick-link"
        onClick={() => router.push('/documents')}
      >
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
        <span>Document Vault</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
      <button
        className="hp-quick-link"
        onClick={() => router.push('/global-legal')}
      >
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
        <span>Legal Library</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
    </motion.div>
  );
}

function IntelligenceTab() {
  const router = useRouter();
  return (
    <motion.div
      className="hp-tab-items"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
    >
      <button className="hp-quick-link" onClick={() => router.push('/news')}>
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
        </svg>
        <span>Legal News</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
      <button className="hp-quick-link" onClick={() => router.push('/wiki')}>
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
        <span>Legal Wiki</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
      <button
        className="hp-quick-link"
        onClick={() => router.push('/global-legal')}
      >
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
        <span>Global Legal</span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="hp-quick-link-arrow"
        >
          <polyline points="9,18 15,12 9,6" />
        </svg>
      </button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function HomePage() {
  const { user } = useAuth();
  const router = useRouter();
  const { voiceMode, setVoiceMode, aminStatus, openPanel } = useAminContext();

  const [activeTab, setActiveTab] = useState<TabId>('cases');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  const greeting = useMemo(() => getGreeting(), []);
  const firstName = user?.full_name?.split(' ')[0] || '';

  const avatarState = useMemo(
    () => avatarStateFromVoice(voiceMode, aminStatus),
    [voiceMode, aminStatus]
  );

  useEffect(() => {
    fetch(resolveApiUrl('/api/v1/cases/dashboard'), { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data) setDashboard(data);
      })
      .catch(() => {});
  }, []);

  const handleActivateToggle = useCallback(() => {
    setVoiceMode(voiceMode === 'active' ? 'off' : 'active');
  }, [voiceMode, setVoiceMode]);

  const handleCaseClick = useCallback(
    (c: CaseBrief) => {
      fetch(resolveApiUrl(`/api/v1/cases/${c.id}/set-active`), {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {});
      router.push(`/cases/${c.id}`);
    },
    [router]
  );

  const recentCases = dashboard?.recently_accessed ?? [];

  return (
    <div className="hp-root">
      {/* Ambient backdrop */}
      <div className="hp-backdrop" aria-hidden />

      {/* ── AMIN HERO ── */}
      <motion.section
        className="hp-hero"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        <button
          type="button"
          className="hp-avatar-wrap"
          onClick={openPanel}
          aria-label="Open Amin"
        >
          <AminAvatar size={120} state={avatarState} />
        </button>

        <motion.h1
          className="hp-greeting"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        >
          {greeting}
          {firstName ? `, ${firstName}` : ''}
        </motion.h1>

        <motion.p
          className="hp-tagline"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          Your legal intelligence, ready.
        </motion.p>

        <motion.button
          type="button"
          className={`hp-activate-btn${voiceMode === 'active' ? ' hp-activate-btn--active' : ''}`}
          onClick={handleActivateToggle}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4, duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
        >
          {voiceMode === 'active' ? (
            <>
              <span className="hp-activate-dot hp-activate-dot--live" />
              Amin is listening
            </>
          ) : (
            <>
              <span className="hp-activate-dot" />
              Activate Amin
            </>
          )}
        </motion.button>
      </motion.section>

      {/* ── NAVIGATION TABS ── */}
      <motion.nav
        className="hp-tabs"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        {TABS.map(tab => (
          <button
            key={tab.id}
            type="button"
            className={`hp-tab${activeTab === tab.id ? ' hp-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </motion.nav>

      {/* ── TAB CONTENT ── */}
      <motion.div
        className="hp-tab-content"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.55, duration: 0.3 }}
      >
        <AnimatePresence mode="wait">
          {activeTab === 'clients' && <ClientsTab key="clients" />}
          {activeTab === 'cases' && (
            <CasesTab
              key="cases"
              cases={dashboard?.recently_accessed ?? []}
              onCaseClick={handleCaseClick}
            />
          )}
          {activeTab === 'workflows' && <WorkflowsTab key="workflows" />}
          {activeTab === 'documents' && <DocumentsTab key="documents" />}
          {activeTab === 'intelligence' && (
            <IntelligenceTab key="intelligence" />
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── RECENT CASES STRIP ── */}
      {recentCases.length > 0 && (
        <motion.section
          className="hp-cases-strip"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <h2 className="hp-strip-label">Recent Cases</h2>
          <div className="hp-strip-scroll">
            {recentCases.map((c, i) => (
              <motion.button
                key={c.id}
                type="button"
                className="hp-case-card"
                onClick={() => handleCaseClick(c)}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: 0.65 + i * 0.06,
                  duration: 0.35,
                  ease: [0.22, 1, 0.36, 1],
                }}
                whileHover={{ y: -3, transition: { duration: 0.2 } }}
              >
                <span
                  className="hp-case-card-priority"
                  style={{
                    background: PRIORITY_COLORS[c.priority] || '#6b7280',
                  }}
                />
                <span className="hp-case-card-title">{c.title}</span>
                <span className="hp-case-card-client">
                  {c.client_display_name}
                </span>
                {c.next_deadline && (
                  <span className="hp-case-card-deadline">
                    {new Date(c.next_deadline).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                )}
              </motion.button>
            ))}
          </div>
        </motion.section>
      )}
    </div>
  );
}
