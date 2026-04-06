'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useNavigation } from '@/components/NavigationLoader';

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

const PRIORITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#64748b',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Active',
  on_hold: 'On Hold',
  pending: 'Pending',
  closed: 'Closed',
};

const PA_ABBREV: Record<string, string> = {
  litigation: 'Lit',
  corporate: 'Corp',
  compliance: 'Comp',
  employment: 'Emp',
  dispute_resolution: 'Disp',
  enforcement: 'Enf',
  research: 'Res',
  firm_management: 'Mgmt',
};

export function CasesPanel() {
  const { navigateTo } = useNavigation();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [paFilter, setPaFilter] = useState('');
  const [cases, setCases] = useState<CaseBrief[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);
      if (paFilter) params.set('practice_area', paFilter);
      params.set('limit', '20');
      const res = await fetch(`/api/v1/cases?${params}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data.items ?? []);
      }
    } catch {
      /* */
    }
    setLoading(false);
  }, [search, statusFilter, paFilter]);

  useEffect(() => {
    const timer = setTimeout(fetchCases, 300);
    return () => clearTimeout(timer);
  }, [fetchCases]);

  const handleCaseClick = (caseItem: CaseBrief) => {
    fetch(`/api/v1/cases/${caseItem.id}/set-active`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {});
    navigateTo(`/cases/${caseItem.id}`);
  };

  const statuses = ['', 'active', 'on_hold', 'pending', 'closed'];
  const practiceAreas = Object.keys(PA_ABBREV);

  return (
    <>
      <div className="r2-header">CASES</div>

      <div className="r2-search">
        <input
          type="text"
          placeholder="Search cases..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="r2-search-input"
        />
      </div>

      <div className="r2-filter-chips">
        {statuses.map(s => (
          <button
            key={s || 'all'}
            type="button"
            className={`r2-chip${statusFilter === s ? ' r2-chip-active' : ''}`}
            onClick={() => setStatusFilter(s)}
          >
            {s ? (STATUS_LABELS[s] ?? s) : 'All'}
          </button>
        ))}
      </div>

      <div className="r2-filter-chips r2-filter-chips-scroll">
        {practiceAreas.map(pa => (
          <button
            key={pa}
            type="button"
            className={`r2-chip r2-chip-sm${paFilter === pa ? ' r2-chip-active' : ''}`}
            onClick={() => setPaFilter(paFilter === pa ? '' : pa)}
            title={pa.replace(/_/g, ' ')}
          >
            {PA_ABBREV[pa]}
          </button>
        ))}
      </div>

      <div className="r2-link-list r2-scrollable">
        {loading &&
          [...Array(4)].map((_, i) => (
            <div
              key={i}
              className="skeleton-row"
              style={{ padding: '8px 16px', animationDelay: `${i * 60}ms` }}
            >
              <div className="skeleton-dot" />
              <div className="skeleton-group">
                <div
                  className="skeleton-line"
                  style={{ width: `${70 - i * 10}%` }}
                />
                <div
                  className="skeleton-line skeleton-line-sm"
                  style={{ width: '30%' }}
                />
              </div>
            </div>
          ))}
        {!loading && cases.length === 0 && (
          <div className="r2-empty">No cases found</div>
        )}
        {cases.map(c => (
          <button
            key={c.id}
            type="button"
            className="r2-case-row"
            onClick={() => handleCaseClick(c)}
          >
            <span
              className="r2-case-priority"
              style={{
                backgroundColor: PRIORITY_COLORS[c.priority] ?? '#64748b',
              }}
            />
            <div className="r2-case-info">
              <span className="r2-case-title">{c.title}</span>
              <span className="r2-case-meta">
                {c.client_display_name}
                {c.next_deadline && (
                  <span
                    className={
                      c.urgent ? 'r2-case-deadline-urgent' : 'r2-case-deadline'
                    }
                  >
                    {' · '}
                    {c.next_deadline}
                  </span>
                )}
              </span>
            </div>
            <span className={`r2-status-badge r2-status-${c.status}`}>
              {STATUS_LABELS[c.status] ?? c.status}
            </span>
          </button>
        ))}
      </div>

      <div className="r2-panel-footer">
        <button
          type="button"
          className="r2-action-btn"
          onClick={() => navigateTo('/cases?new=true')}
        >
          + New Case
        </button>
      </div>
    </>
  );
}
