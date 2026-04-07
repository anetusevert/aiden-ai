'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';
import { reportScreenContext } from '@/lib/screenContext';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

interface CaseBrief {
  id: string;
  title: string;
  status: string;
  priority: string;
  practice_area: string;
  next_deadline: string | null;
  next_deadline_description: string | null;
  client_display_name: string;
  urgent: boolean;
}

interface PracticeAreaCount {
  area: string;
  count: number;
}

interface DashboardData {
  active_cases: number;
  high_priority: number;
  due_today: CaseBrief[];
  due_this_week: CaseBrief[];
  recently_accessed: CaseBrief[];
  practice_area_distribution: PracticeAreaCount[];
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function getFormattedDate(): string {
  return new Date().toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function toHijriApprox(): string {
  try {
    return new Intl.DateTimeFormat('en-SA-u-ca-islamic-umalqura', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }).format(new Date());
  } catch {
    return '';
  }
}

const PRIORITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#94a3b8',
  low: '#64748b',
};

export default function DashboardPage() {
  const { navigateTo } = useNavigation();
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<
    'deadline' | 'priority' | 'practice_area' | 'client'
  >('deadline');

  const firstName = user?.full_name?.split(' ')[0] ?? 'Counsellor';

  useEffect(() => {
    reportScreenContext({
      route: '/dashboard',
      page_title: 'Dashboard',
      document: null,
      ui_state: {},
    });
  }, []);

  useEffect(() => {
    fetch('/api/v1/cases/dashboard', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        setDashboard(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleCaseClick = useCallback(
    (c: CaseBrief) => {
      fetch(`/api/v1/cases/${c.id}/set-active`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {});
      navigateTo(`/cases/${c.id}`);
    },
    [navigateTo]
  );

  const allActiveCases = [
    ...(dashboard?.due_today ?? []),
    ...(dashboard?.due_this_week ?? []),
    ...(dashboard?.recently_accessed ?? []),
  ];

  const uniqueCases = allActiveCases.filter(
    (c, i, arr) => arr.findIndex(x => x.id === c.id) === i
  );

  const hijri = toHijriApprox();

  return (
    <motion.div
      className="dashboard-page"
      {...fadeUp}
      style={{
        height: '100%',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div className="dashboard-greeting-bar">
        <div className="dashboard-greeting-left">
          {getGreeting()}, {firstName}.
        </div>
        <div className="dashboard-greeting-right">
          {getFormattedDate()}
          {hijri && <span className="dashboard-hijri"> · {hijri}</span>}
        </div>
      </div>

      <div
        className="dashboard-body"
        style={{
          flex: 1,
          display: 'flex',
          gap: 'var(--space-6)',
          overflow: 'hidden',
          padding: 'var(--space-4)',
        }}
      >
        {/* Left column - 30% */}
        <div
          className="dashboard-left"
          style={{
            width: '30%',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-4)',
            overflow: 'auto',
          }}
        >
          <div
            className="dashboard-stat-card"
            onClick={() => navigateTo('/cases?status=active')}
          >
            <div className="dashboard-stat-icon">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="2" y="7" width="20" height="14" rx="2" />
                <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
              </svg>
            </div>
            <div className="dashboard-stat-number">
              {dashboard?.active_cases ?? 0}
            </div>
            <div className="dashboard-stat-label">Active Cases</div>
          </div>

          <div
            className="dashboard-stat-card dashboard-stat-card-danger"
            onClick={() => navigateTo('/cases?priority=high')}
          >
            <div className="dashboard-stat-icon">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div className="dashboard-stat-number">
              {dashboard?.high_priority ?? 0}
            </div>
            <div className="dashboard-stat-label">High Priority</div>
          </div>

          <div className="dashboard-stat-card">
            <div className="dashboard-stat-icon">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
            </div>
            <div className="dashboard-stat-number">
              {(dashboard?.due_today?.length ?? 0) +
                (dashboard?.due_this_week?.length ?? 0)}
            </div>
            <div className="dashboard-stat-label">Due This Week</div>
          </div>

          <div className="dashboard-briefing-card">
            <div className="dashboard-briefing-title">Amin&apos;s Briefing</div>
            <div className="dashboard-briefing-body">
              {dashboard ? (
                dashboard.active_cases > 0 ? (
                  `You have ${dashboard.active_cases} active case${dashboard.active_cases !== 1 ? 's' : ''}. ${dashboard.high_priority} require${dashboard.high_priority !== 1 ? '' : 's'} urgent attention. ${(dashboard.due_today?.length ?? 0) + (dashboard.due_this_week?.length ?? 0)} deadline${(dashboard.due_today?.length ?? 0) + (dashboard.due_this_week?.length ?? 0) !== 1 ? 's' : ''} approaching this week.`
                ) : (
                  'No active cases. Create your first case to get started.'
                )
              ) : (
                <span className="dashboard-briefing-skeleton">
                  Loading briefing...
                </span>
              )}
            </div>
          </div>

          <div className="dashboard-quick-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigateTo('/cases?new=true')}
            >
              + New Case
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => navigateTo('/clients?new=true')}
            >
              + New Client
            </button>
          </div>
        </div>

        {/* Right column - 70% */}
        <div
          className="dashboard-right"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div className="dashboard-table-header">
            <div className="dashboard-table-title">
              ACTIVE CASES
              {dashboard && (
                <span className="dashboard-table-count">
                  {dashboard.active_cases}
                </span>
              )}
            </div>
            <select
              className="dashboard-sort-select"
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
            >
              <option value="deadline">Sort by Deadline</option>
              <option value="priority">Sort by Priority</option>
              <option value="practice_area">Sort by Practice Area</option>
              <option value="client">Sort by Client</option>
            </select>
          </div>

          <div
            className="dashboard-case-table"
            style={{ flex: 1, overflow: 'auto' }}
          >
            {loading && (
              <div>
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="skeleton-row"
                    style={{ animationDelay: `${i * 60}ms` }}
                  >
                    <div className="skeleton-dot" />
                    <div className="skeleton-group">
                      <div
                        className="skeleton-line"
                        style={{ width: `${70 - i * 8}%` }}
                      />
                      <div
                        className="skeleton-line skeleton-line-sm"
                        style={{ width: '25%' }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!loading && uniqueCases.length === 0 && (
              <div className="dashboard-empty">
                <div className="page-empty-icon">
                  <svg
                    width="28"
                    height="28"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <rect x="2" y="7" width="20" height="14" rx="2" />
                    <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                  </svg>
                </div>
                <h3>No active cases</h3>
                <p>Create your first case to get started</p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => navigateTo('/cases?new=true')}
                >
                  New Case
                </button>
              </div>
            )}
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {uniqueCases.map(c => {
                const isOverdue =
                  c.next_deadline && new Date(c.next_deadline) < new Date();
                return (
                  <motion.div
                    key={c.id}
                    variants={staggerItem}
                    className="dashboard-case-row"
                    onClick={() => handleCaseClick(c)}
                  >
                    <span
                      className="dashboard-case-priority-dot"
                      style={{ backgroundColor: PRIORITY_COLORS[c.priority] }}
                    />
                    <div className="dashboard-case-info">
                      <span className="dashboard-case-title">{c.title}</span>
                      <span className="dashboard-case-client">
                        {c.client_display_name}
                      </span>
                    </div>
                    <span className="dashboard-case-pa">
                      {c.practice_area.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`dashboard-case-status dashboard-case-status-${c.status}`}
                    >
                      {c.status}
                    </span>
                    {c.next_deadline && (
                      <span
                        className={`dashboard-case-deadline ${isOverdue ? 'dashboard-case-deadline-overdue' : ''}`}
                      >
                        {c.next_deadline}
                      </span>
                    )}
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
