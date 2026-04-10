'use client';

import { useState, useEffect, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { resolveApiUrl } from '@/lib/api';
import { reportScreenContext } from '@/lib/screenContext';
import {
  fadeUp,
  staggerContainer,
  staggerItem,
  glassReveal,
  glassBackdrop,
} from '@/lib/motion';

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

export default function CasesPage() {
  const { navigateTo } = useNavigation();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [cases, setCases] = useState<CaseBrief[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState(
    () => searchParams.get('search') ?? ''
  );
  const [showNewModal, setShowNewModal] = useState(false);

  const statusFilter = searchParams.get('status') ?? '';
  const priorityFilter = searchParams.get('priority') ?? '';
  const paFilter = searchParams.get('practice_area') ?? '';

  useEffect(() => {
    reportScreenContext({
      route: '/cases',
      page_title: 'Cases',
      document: null,
      ui_state: {},
    });
  }, []);

  useEffect(() => {
    if (searchParams.get('new') === 'true') setShowNewModal(true);
  }, [searchParams]);

  useEffect(() => {
    setSearchInput(searchParams.get('search') ?? '');
  }, [searchParams]);

  const patchQuery = useCallback(
    (patch: Record<string, string>) => {
      const sp = new URLSearchParams(searchParams.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v) sp.set(k, v);
        else sp.delete(k);
      }
      const q = sp.toString();
      router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams]
  );

  const pushSearchToUrl = (value: string) => {
    patchQuery({ search: value });
  };

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    const params = new URLSearchParams();
    const s = searchParams.get('search');
    if (s) params.set('search', s);
    const st = searchParams.get('status');
    if (st) params.set('status', st);
    const pr = searchParams.get('priority');
    if (pr) params.set('priority', pr);
    const pa = searchParams.get('practice_area');
    if (pa) params.set('practice_area', pa);
    params.set('limit', '100');
    try {
      const res = await fetch(resolveApiUrl(`/api/v1/cases?${params}`), {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data.items ?? []);
        setTotal(data.total ?? 0);
      } else {
        setFetchError(`Failed to load cases (${res.status}).`);
      }
    } catch (err) {
      const isCors =
        err instanceof TypeError && /fetch|network/i.test(String(err));
      setFetchError(
        isCors
          ? 'API request blocked (CORS). The server deployment may still be in progress — try again in a minute.'
          : 'Could not connect to the server. Please check your connection.'
      );
    }
    setLoading(false);
  }, [searchParams]);

  useEffect(() => {
    const t = setTimeout(fetchCases, 300);
    return () => clearTimeout(t);
  }, [fetchCases]);

  const handleCaseClick = (c: CaseBrief) => {
    fetch(resolveApiUrl(`/api/v1/cases/${c.id}/set-active`), {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {});
    navigateTo(`/cases/${c.id}`);
  };

  return (
    <motion.div
      className="page-container"
      {...fadeUp}
      style={{
        height: '100%',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div className="page-header">
        <div className="page-header-left">
          <h1 className="page-title">Cases</h1>
          <div className="page-stat-chips">
            <span className="stat-chip">Total: {total}</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowNewModal(true)}
          >
            + New Case
          </button>
        </div>
      </div>

      <div className="page-filters">
        <input
          type="text"
          className="page-search"
          placeholder="Search by title or case number..."
          value={searchInput}
          onChange={e => {
            const v = e.target.value;
            setSearchInput(v);
            pushSearchToUrl(v);
          }}
        />
        <div className="page-filter-chips">
          {['', 'active', 'on_hold', 'pending', 'closed'].map(s => (
            <button
              key={s || 'all'}
              type="button"
              className={`chip${statusFilter === s ? ' chip-active' : ''}`}
              onClick={() => patchQuery({ status: s })}
            >
              {s ? (STATUS_LABELS[s] ?? s) : 'All'}
            </button>
          ))}
        </div>
        <div className="page-filter-chips">
          {['', 'high', 'medium', 'low'].map(p => (
            <button
              key={p || 'all'}
              type="button"
              className={`chip${priorityFilter === p ? ' chip-active' : ''}`}
              onClick={() => patchQuery({ priority: p })}
            >
              {p ? p.charAt(0).toUpperCase() + p.slice(1) : 'Priority'}
            </button>
          ))}
        </div>
        <div className="page-filter-chips">
          {Object.keys(PA_ABBREV).map(pa => (
            <button
              key={pa}
              type="button"
              className={`chip${paFilter === pa ? ' chip-active' : ''}`}
              title={pa.replace(/_/g, ' ')}
              onClick={() =>
                patchQuery({ practice_area: paFilter === pa ? '' : pa })
              }
            >
              {PA_ABBREV[pa]}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading && (
          <div>
            <div className="cases-table-header">
              <span className="cases-col-priority" />
              <span className="cases-col-title">Case + Client</span>
              <span className="cases-col-pa">Practice Area</span>
              <span className="cases-col-status">Status</span>
              <span className="cases-col-deadline">Deadline</span>
            </div>
            {[...Array(6)].map((_, i) => (
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
        <div className="cases-table-header">
          <span className="cases-col-priority">Priority</span>
          <span className="cases-col-title">Case + Client</span>
          <span className="cases-col-pa">Practice Area</span>
          <span className="cases-col-status">Status</span>
          <span className="cases-col-deadline">Deadline</span>
        </div>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {cases.map(c => {
            const isOverdue =
              c.next_deadline && new Date(c.next_deadline) < new Date();
            return (
              <motion.div
                key={c.id}
                variants={staggerItem}
                className="cases-table-row"
                onClick={() => handleCaseClick(c)}
              >
                <span className="cases-col-priority">
                  <span
                    className="priority-dot"
                    style={{ backgroundColor: PRIORITY_COLORS[c.priority] }}
                  />
                </span>
                <div className="cases-col-title">
                  <span className="cases-row-title">{c.title}</span>
                  <span className="cases-row-client">
                    {c.client_display_name}
                  </span>
                </div>
                <span className="cases-col-pa">
                  {c.practice_area.replace(/_/g, ' ')}
                </span>
                <span className="cases-col-status">
                  <span
                    className={`badge badge-status badge-status-${c.status}`}
                  >
                    {c.status}
                  </span>
                </span>
                <span
                  className={`cases-col-deadline ${isOverdue ? 'deadline-overdue' : ''}`}
                >
                  {c.next_deadline ?? '—'}
                  {isOverdue && ' ⚠'}
                </span>
              </motion.div>
            );
          })}
        </motion.div>
        {!loading && fetchError && (
          <div className="page-empty">
            <div className="page-empty-icon">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h3>{fetchError}</h3>
            <button
              type="button"
              className="btn btn-outline"
              style={{ marginTop: 'var(--space-3)' }}
              onClick={fetchCases}
            >
              Retry
            </button>
          </div>
        )}
        {!loading && !fetchError && cases.length === 0 && (
          <div className="page-empty">
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
            <h3>No cases found</h3>
            <p>Create your first case to get started</p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowNewModal(true)}
            >
              + New Case
            </button>
          </div>
        )}
      </div>

      <AnimatePresence>
        {showNewModal && (
          <NewCaseModal
            onClose={() => setShowNewModal(false)}
            onCreated={id => {
              setShowNewModal(false);
              navigateTo(`/cases/${id}`);
            }}
            preClientId={searchParams.get('client_id') ?? undefined}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function NewCaseModal({
  onClose,
  onCreated,
  preClientId,
}: {
  onClose: () => void;
  onCreated: (id: string) => void;
  preClientId?: string;
}) {
  const { navigateTo } = useNavigation();
  const [form, setForm] = useState<Record<string, string>>({
    client_id: preClientId ?? '',
    practice_area: 'litigation',
    jurisdiction: 'KSA',
    priority: 'medium',
  });
  const [clientSearch, setClientSearch] = useState('');
  const [clients, setClients] = useState<any[]>([]);
  const [clientsLoaded, setClientsLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateField = (k: string, v: string) =>
    setForm(prev => ({ ...prev, [k]: v }));

  useEffect(() => {
    const timer = setTimeout(() => {
      const q = clientSearch || '';
      fetch(resolveApiUrl(`/api/v1/clients?search=${q}&limit=10`), {
        credentials: 'include',
      })
        .then(r => {
          if (!r.ok) throw new Error(`Failed to load clients (${r.status})`);
          return r.json();
        })
        .then(d => {
          setClients(d.items ?? []);
          setClientsLoaded(true);
        })
        .catch(() => {
          setClientsLoaded(true);
        });
    }, 200);
    return () => clearTimeout(timer);
  }, [clientSearch]);

  const clearSelectedClient = () => {
    updateField('client_id', '');
    setClientSearch('');
  };

  const handleCreate = async () => {
    if (!form.client_id || !form.title) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(resolveApiUrl('/api/v1/cases'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        const data = await res.json();
        onCreated(data.id);
        return;
      }
      let message = `Could not create case (${res.status}).`;
      try {
        const body = await res.json();
        const detail = body?.detail;
        if (typeof detail === 'string') message = detail;
        else if (typeof detail === 'object' && detail?.message)
          message = detail.message;
      } catch {
        /* non-JSON body */
      }
      setError(message);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Network error. Please check your connection and try again.'
      );
    } finally {
      setSaving(false);
    }
  };

  const practiceAreas = [
    'litigation',
    'corporate',
    'compliance',
    'employment',
    'dispute_resolution',
    'enforcement',
    'research',
    'firm_management',
  ];
  const jurisdictions = ['KSA', 'UAE', 'DIFC', 'ADGM', 'Qatar', 'GCC'];

  return (
    <motion.div className="modal-backdrop" {...glassBackdrop} onClick={onClose}>
      <motion.div
        className="modal-content modal-lg"
        {...glassReveal}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2>New Case</h2>
          <button type="button" className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="modal-body">
          {error ? (
            <div style={{ padding: '0 0 var(--space-3)' }}>
              <div className="alert alert-error">{error}</div>
            </div>
          ) : null}

          <div className="form-grid">
            <div className="form-field form-field-full">
              <label>Client *</label>
              {form.client_id ? (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <input
                    type="text"
                    value={clientSearch}
                    readOnly
                    style={{ flex: 1, opacity: 0.8 }}
                  />
                  <button
                    type="button"
                    className="btn btn-outline"
                    style={{ fontSize: 12, height: 32, padding: '0 10px' }}
                    onClick={clearSelectedClient}
                  >
                    Change
                  </button>
                </div>
              ) : (
                <>
                  <input
                    type="text"
                    placeholder="Search clients..."
                    value={clientSearch}
                    onChange={e => setClientSearch(e.target.value)}
                    autoFocus
                  />
                  {clients.length > 0 && (
                    <div className="client-suggestions">
                      {clients.map(c => (
                        <button
                          key={c.id}
                          type="button"
                          className="client-suggestion"
                          onClick={() => {
                            updateField('client_id', c.id);
                            setClientSearch(c.display_name);
                          }}
                        >
                          {c.display_name} ({c.client_type})
                        </button>
                      ))}
                    </div>
                  )}
                  {clientsLoaded && clients.length === 0 && (
                    <div
                      style={{
                        padding: 'var(--space-3)',
                        color: 'var(--text-muted)',
                        fontSize: '0.8125rem',
                        textAlign: 'center',
                      }}
                    >
                      {clientSearch
                        ? 'No clients match your search.'
                        : 'No clients yet.'}{' '}
                      <button
                        type="button"
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-link, #60a5fa)',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          padding: 0,
                          font: 'inherit',
                        }}
                        onClick={() => navigateTo('/clients?new=true')}
                      >
                        Create a client first
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
            <div className="form-field form-field-full">
              <label>Title *</label>
              <input
                type="text"
                value={form.title ?? ''}
                onChange={e => updateField('title', e.target.value)}
                placeholder="Contract Dispute vs Al-Rajhi Bank"
              />
            </div>
            <div className="form-field">
              <label>Practice Area</label>
              <select
                value={form.practice_area}
                onChange={e => updateField('practice_area', e.target.value)}
              >
                {practiceAreas.map(pa => (
                  <option key={pa} value={pa}>
                    {pa.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label>Jurisdiction</label>
              <select
                value={form.jurisdiction}
                onChange={e => updateField('jurisdiction', e.target.value)}
              >
                {jurisdictions.map(j => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>
            <div className="form-field">
              <label>Priority</label>
              <select
                value={form.priority}
                onChange={e => updateField('priority', e.target.value)}
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div className="form-field">
              <label>Case Number</label>
              <input
                type="text"
                value={form.case_number ?? ''}
                onChange={e => updateField('case_number', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label>Next Deadline</label>
              <input
                type="date"
                value={form.next_deadline ?? ''}
                onChange={e => updateField('next_deadline', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label>Deadline Description</label>
              <input
                type="text"
                value={form.next_deadline_description ?? ''}
                onChange={e =>
                  updateField('next_deadline_description', e.target.value)
                }
              />
            </div>
            <div className="form-field form-field-full">
              <label>Description</label>
              <textarea
                value={form.description ?? ''}
                onChange={e => updateField('description', e.target.value)}
                rows={3}
              />
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!form.client_id || !form.title || saving}
              onClick={handleCreate}
            >
              {saving ? 'Creating...' : 'Create Case'}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
