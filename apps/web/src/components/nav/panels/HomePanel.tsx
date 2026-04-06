'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useNavigation } from '@/components/NavigationLoader';
import { useAuth } from '@/lib/AuthContext';
import type { SoulDetail } from '@/lib/apiClient';

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

interface HomePanelProps {
  soul: SoulDetail | null;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function HomePanel({ soul }: HomePanelProps) {
  const { navigateTo } = useNavigation();
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  useEffect(() => {
    fetch('/api/v1/cases/dashboard', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data) setDashboard(data);
      })
      .catch(() => {});
  }, []);

  const firstName = user?.full_name?.split(' ')[0] ?? 'Counsellor';

  const handleCaseClick = (c: CaseBrief) => {
    fetch(`/api/v1/cases/${c.id}/set-active`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {});
    navigateTo(`/cases/${c.id}`);
  };

  const dueSoonCases = [
    ...(dashboard?.due_today ?? []),
    ...(dashboard?.due_this_week ?? []),
  ].slice(0, 4);

  return (
    <>
      <div className="r2-home-greeting">
        {getGreeting()}, {firstName}
      </div>

      {dashboard && (
        <div className="r2-stat-row">
          <span className="r2-stat-chip">
            {dashboard.active_cases} Active Cases
          </span>
          <span className="r2-stat-chip r2-stat-chip-warn">
            {dashboard.high_priority} High Priority
          </span>
          <span className="r2-stat-chip">
            {dueSoonCases.length} Due This Week
          </span>
        </div>
      )}

      {dueSoonCases.length > 0 && (
        <div className="r2-section">
          <div className="r2-section-label r2-section-label-warn">DUE SOON</div>
          <div className="r2-link-list">
            {dueSoonCases.map(c => (
              <button
                key={c.id}
                type="button"
                className="r2-link r2-link-stacked"
                onClick={() => handleCaseClick(c)}
              >
                <span
                  className={`r2-due-dot ${c.urgent ? 'r2-due-dot-red' : 'r2-due-dot-amber'}`}
                />
                <span className="r2-link-text">{c.title}</span>
                <span className="r2-link-meta">{c.next_deadline}</span>
              </button>
            ))}
          </div>
          {dueSoonCases.length === 0 && (
            <div className="r2-empty">No upcoming deadlines</div>
          )}
        </div>
      )}

      {dashboard?.recently_accessed &&
        dashboard.recently_accessed.length > 0 && (
          <div className="r2-section">
            <div className="r2-section-label">CONTINUE</div>
            <div className="r2-link-list">
              {dashboard.recently_accessed.slice(0, 3).map(c => (
                <button
                  key={c.id}
                  type="button"
                  className="r2-link r2-link-stacked"
                  onClick={() => handleCaseClick(c)}
                >
                  <span className="r2-link-text">{c.title}</span>
                  <span className="r2-link-meta">{c.client_display_name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

      <div className="r2-section">
        <div className="r2-quick-actions">
          <button
            type="button"
            className="r2-action-btn"
            onClick={() => navigateTo('/clients?new=true')}
          >
            + New Client
          </button>
          <button
            type="button"
            className="r2-action-btn r2-action-btn-primary"
            onClick={() => navigateTo('/cases?new=true')}
          >
            + New Case
          </button>
        </div>
      </div>
    </>
  );
}
