'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
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

export default function CasesPage() {
  const { navigateTo } = useNavigation();
  const searchParams = useSearchParams();
  const [cases, setCases] = useState<CaseBrief[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState(
    searchParams.get('status') ?? ''
  );
  const [priorityFilter, setPriorityFilter] = useState(
    searchParams.get('priority') ?? ''
  );
  const [paFilter, setPaFilter] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);

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

  const fetchCases = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (statusFilter) params.set('status', statusFilter);
    if (priorityFilter) params.set('priority', priorityFilter);
    if (paFilter) params.set('practice_area', paFilter);
    params.set('limit', '100');
    try {
      const res = await fetch(`/api/v1/cases?${params}`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data.items ?? []);
        setTotal(data.total ?? 0);
      }
    } catch {
      /* */
    }
    setLoading(false);
  }, [search, statusFilter, priorityFilter, paFilter]);

  useEffect(() => {
    const t = setTimeout(fetchCases, 300);
    return () => clearTimeout(t);
  }, [fetchCases]);

  const handleCaseClick = (c: CaseBrief) => {
    fetch(`/api/v1/cases/${c.id}/set-active`, {
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
        <button
          type="button"
          className="btn btn-gold"
          onClick={() => setShowNewModal(true)}
        >
          + New Case
        </button>
      </div>

      <div className="page-filters">
        <input
          type="text"
          className="page-search"
          placeholder="Search by title or case number..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="page-filter-chips">
          {['', 'active', 'on_hold', 'pending', 'closed'].map(s => (
            <button
              key={s || 'all'}
              type="button"
              className={`chip${statusFilter === s ? ' chip-active' : ''}`}
              onClick={() => setStatusFilter(s)}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
        <div className="page-filter-chips">
          {['', 'high', 'medium', 'low'].map(p => (
            <button
              key={p || 'all'}
              type="button"
              className={`chip${priorityFilter === p ? ' chip-active' : ''}`}
              onClick={() => setPriorityFilter(p)}
            >
              {p || 'Priority'}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading && <div className="page-loading">Loading cases...</div>}
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
        {!loading && cases.length === 0 && (
          <div className="page-empty">
            <h3>No cases found</h3>
            <p>Create your first case to get started</p>
            <button
              type="button"
              className="btn btn-gold"
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
  const [form, setForm] = useState<Record<string, string>>({
    client_id: preClientId ?? '',
    practice_area: 'litigation',
    jurisdiction: 'KSA',
    priority: 'medium',
  });
  const [clientSearch, setClientSearch] = useState('');
  const [clients, setClients] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);

  const updateField = (k: string, v: string) =>
    setForm(prev => ({ ...prev, [k]: v }));

  useEffect(() => {
    if (!clientSearch && !preClientId) return;
    const q = clientSearch || '';
    fetch(`/api/v1/clients?search=${q}&limit=10`, { credentials: 'include' })
      .then(r => (r.ok ? r.json() : { items: [] }))
      .then(d => setClients(d.items ?? []))
      .catch(() => {});
  }, [clientSearch, preClientId]);

  const handleCreate = async () => {
    if (!form.client_id || !form.title) return;
    setSaving(true);
    try {
      const res = await fetch('/api/v1/cases', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (res.ok) {
        const data = await res.json();
        onCreated(data.id);
      }
    } catch {
      /* */
    }
    setSaving(false);
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
          <div className="form-grid">
            <div className="form-field form-field-full">
              <label>Client *</label>
              <input
                type="text"
                placeholder="Search clients..."
                value={clientSearch}
                onChange={e => setClientSearch(e.target.value)}
              />
              {clients.length > 0 && !form.client_id && (
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
              className="btn btn-gold"
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
