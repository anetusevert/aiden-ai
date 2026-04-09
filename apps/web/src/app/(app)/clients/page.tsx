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
  tileMotion,
  glassReveal,
  glassBackdrop,
} from '@/lib/motion';

interface ClientItem {
  id: string;
  display_name: string;
  client_type: string;
  email: string | null;
  phone: string | null;
  cr_number: string | null;
  national_id: string | null;
  org_type: string | null;
  case_count: number;
}

const TYPE_COLORS: Record<string, string> = {
  individual: 'rgba(255,255,255,0.9)',
  company: 'rgba(255,255,255,0.85)',
  organisation: 'rgba(255,255,255,0.8)',
};

const TYPE_LABELS: Record<string, string> = {
  '': 'All',
  individual: 'Individual',
  company: 'Company',
  organisation: 'Organisation',
};

function getStatusMessage(action: string, status: number): string {
  switch (status) {
    case 401:
      return `Could not ${action}. Your session has expired or the API did not accept your login cookie.`;
    case 403:
      return `Could not ${action}. Your account does not have permission for this action.`;
    case 404:
      return `Could not ${action}. The client API route is not reachable from this app.`;
    case 422:
      return `Could not ${action}. Please check the form values and try again.`;
    default:
      return `Could not ${action}. Request failed with status ${status}.`;
  }
}

async function getRequestErrorMessage(
  action: string,
  response: Response
): Promise<string> {
  const baseMessage = getStatusMessage(action, response.status);
  let detail: string | null = null;

  try {
    const data = await response.json();
    const responseDetail = data?.detail;

    if (typeof responseDetail === 'string' && responseDetail.trim()) {
      detail = responseDetail.trim();
    } else if (
      responseDetail &&
      typeof responseDetail === 'object' &&
      'message' in responseDetail &&
      typeof responseDetail.message === 'string' &&
      responseDetail.message.trim()
    ) {
      detail = responseDetail.message.trim();
    }
  } catch {
    try {
      const text = await response.text();
      if (text.trim()) {
        detail = text.trim();
      }
    } catch {
      /* */
    }
  }

  if (!detail) {
    return baseMessage;
  }

  if (baseMessage.toLowerCase().includes(detail.toLowerCase())) {
    return baseMessage;
  }

  return `${baseMessage} ${detail}`;
}

export default function ClientsPage() {
  const { navigateTo } = useNavigation();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searchInput, setSearchInput] = useState(
    () => searchParams.get('search') ?? ''
  );
  const [showNewModal, setShowNewModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    reportScreenContext({
      route: '/clients',
      page_title: 'Clients',
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

  const pushSearchToUrl = (value: string) => {
    const sp = new URLSearchParams(searchParams.toString());
    if (value) sp.set('search', value);
    else sp.delete('search');
    const q = sp.toString();
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
  };

  const fetchClients = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    const s = searchParams.get('search');
    if (s) params.set('search', s);
    const ct = searchParams.get('client_type');
    if (ct) params.set('client_type', ct);
    params.set('limit', '50');
    try {
      const res = await fetch(resolveApiUrl(`/api/v1/clients?${params}`), {
        credentials: 'include',
      });

      if (!res.ok) {
        throw new Error(await getRequestErrorMessage('load clients', res));
      }

      const data = await res.json();
      setClients(data.items ?? []);
      setTotal(data.total ?? 0);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load clients.');
    }
    setLoading(false);
  }, [searchParams]);

  useEffect(() => {
    const timer = setTimeout(fetchClients, 300);
    return () => clearTimeout(timer);
  }, [fetchClients]);

  const types = ['', 'individual', 'company', 'organisation'];
  const typeFilter = searchParams.get('client_type') ?? '';

  const setTypeFilter = (t: string) => {
    const sp = new URLSearchParams(searchParams.toString());
    if (t) sp.set('client_type', t);
    else sp.delete('client_type');
    const q = sp.toString();
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
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
        <h1 className="page-title">Clients</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setShowNewModal(true)}
          >
            + New Client
          </button>
        </div>
      </div>

      <div className="page-filters">
        <input
          type="text"
          className="page-search"
          placeholder="Search clients..."
          value={searchInput}
          onChange={e => {
            const v = e.target.value;
            setSearchInput(v);
            pushSearchToUrl(v);
          }}
        />
        <div className="page-filter-chips">
          {types.map(t => (
            <button
              key={t || 'all'}
              type="button"
              className={`chip${typeFilter === t ? ' chip-active' : ''}`}
              onClick={() => setTypeFilter(t)}
            >
              {TYPE_LABELS[t]}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div style={{ padding: '0 var(--space-4)' }}>
          <div className="alert alert-error">{error}</div>
        </div>
      ) : null}

      <div style={{ flex: 1, overflow: 'auto', padding: 'var(--space-4)' }}>
        {loading && (
          <div className="client-grid">
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="skeleton-card"
                style={{ height: 180, animationDelay: `${i * 80}ms` }}
              />
            ))}
          </div>
        )}
        <motion.div
          className="client-grid"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {clients.map((c, i) => (
            <motion.div
              key={c.id}
              className="client-card"
              variants={staggerItem}
              whileHover={tileMotion.hover}
              whileTap={tileMotion.tap}
              onClick={() => navigateTo(`/clients/${c.id}`)}
            >
              <div className="client-card-top">
                <div
                  className="client-card-type-icon"
                  style={{ color: TYPE_COLORS[c.client_type] }}
                >
                  {c.client_type === 'company'
                    ? '🏢'
                    : c.client_type === 'organisation'
                      ? '🌐'
                      : '👤'}
                </div>
                <span className="client-card-type-badge">{c.client_type}</span>
              </div>
              <div className="client-card-name">{c.display_name}</div>
              <div className="client-card-secondary">
                {c.client_type === 'company' &&
                  c.cr_number &&
                  `CR: ${c.cr_number}`}
                {c.client_type === 'individual' &&
                  c.national_id &&
                  `ID: ${c.national_id}`}
                {c.client_type === 'organisation' && c.org_type && c.org_type}
              </div>
              {(c.email || c.phone) && (
                <div className="client-card-contact">
                  {c.email && <span>{c.email}</span>}
                  {c.phone && <span>{c.phone}</span>}
                </div>
              )}
              <div className="client-card-footer">
                <span className="client-card-cases">{c.case_count} cases</span>
              </div>
            </motion.div>
          ))}
        </motion.div>
        {!loading && clients.length === 0 && (
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
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <h3>No clients yet</h3>
            <p>Create your first client to get started</p>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => setShowNewModal(true)}
            >
              + New Client
            </button>
          </div>
        )}
      </div>

      <AnimatePresence>
        {showNewModal && (
          <NewClientModal
            onClose={() => setShowNewModal(false)}
            onCreated={id => {
              setShowNewModal(false);
              navigateTo(`/clients/${id}`);
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function NewClientModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [type, setType] = useState('');
  const [form, setForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setUploadProgress(10);
    const interval = setInterval(
      () => setUploadProgress(p => Math.min(p + 15, 85)),
      400
    );
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(
        resolveApiUrl('/api/v1/clients/extract-from-document'),
        {
          method: 'POST',
          credentials: 'include',
          body: fd,
        }
      );
      clearInterval(interval);
      setUploadProgress(100);

      if (!res.ok) {
        setUploading(false);
        setUploadProgress(0);
        setError(await getRequestErrorMessage('extract client details', res));
        return;
      }

      const data = await res.json();
      const newForm: Record<string, string> = {};
      for (const [k, v] of Object.entries(data)) {
        if (v && typeof v === 'string') newForm[k] = v;
      }
      if (data.client_type) setType(data.client_type);
      setForm(newForm);
      setTimeout(() => {
        setUploading(false);
        setStep(1);
      }, 500);
    } catch (err) {
      clearInterval(interval);
      setUploading(false);
      setUploadProgress(0);
      setError(
        err instanceof Error
          ? err.message
          : 'Could not extract client details from the document.'
      );
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const updateField = (key: string, val: string) =>
    setForm(prev => ({ ...prev, [key]: val }));

  const handleCreate = async () => {
    if (!type) {
      setError('Choose a client type before creating the client.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const body = {
        client_type: type,
        display_name: form.display_name || '',
        ...form,
      };
      const res = await fetch(resolveApiUrl('/api/v1/clients'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(await getRequestErrorMessage('create the client', res));
      }

      const data = await res.json();
      onCreated(data.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Could not create the client.'
      );
    }
    setSaving(false);
  };

  return (
    <motion.div className="modal-backdrop" {...glassBackdrop} onClick={onClose}>
      <motion.div
        className="modal-content modal-lg"
        {...glassReveal}
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-header">
          <h2>New Client</h2>
          <button type="button" className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        {error ? (
          <div style={{ padding: '0 var(--space-4)' }}>
            <div className="alert alert-error">{error}</div>
          </div>
        ) : null}

        {step === 0 && (
          <div className="modal-body">
            {!uploading && (
              <div
                className={`upload-zone${dragOver ? ' upload-zone-active' : ''}`}
                onDragOver={e => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => {
                  const input = document.createElement('input');
                  input.type = 'file';
                  input.accept = '.pdf,.docx,.doc,.png,.jpg,.jpeg';
                  input.onchange = e => {
                    const f = (e.target as HTMLInputElement).files?.[0];
                    if (f) handleFileUpload(f);
                  };
                  input.click();
                }}
              >
                <div className="upload-zone-icon">
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <div className="upload-zone-title">
                  Upload a client document
                </div>
                <div className="upload-zone-subtitle">
                  CR certificate, Wakala, national ID, or any document — Amin
                  will extract client details
                </div>
              </div>
            )}
            {uploading && (
              <div className="upload-zone upload-zone-processing">
                <div className="upload-progress">
                  <div className="upload-progress-bar">
                    <div
                      className="upload-progress-fill"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <div className="upload-progress-text">
                    Amin is extracting client information...
                  </div>
                </div>
              </div>
            )}

            <div
              style={{
                textAlign: 'center',
                padding: 'var(--space-3) 0',
                color: 'var(--text-muted)',
                fontSize: '0.75rem',
              }}
            >
              or choose type manually
            </div>

            <div className="type-cards">
              {[
                {
                  key: 'individual' as const,
                  icon: '👤',
                  desc: 'Natural person, national ID',
                },
                {
                  key: 'company' as const,
                  icon: '🏢',
                  desc: 'Commercial entity, CR number',
                },
                {
                  key: 'organisation' as const,
                  icon: '🌐',
                  desc: 'Government, NGO, international',
                },
              ].map(t => (
                <button
                  key={t.key}
                  type="button"
                  className={`type-card${type === t.key ? ' type-card-active' : ''}`}
                  onClick={() => {
                    setType(t.key);
                    setStep(1);
                  }}
                >
                  <span className="type-card-icon">{t.icon}</span>
                  <span className="type-card-label">{t.key}</span>
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      color: 'var(--text-muted)',
                      textAlign: 'center',
                    }}
                  >
                    {t.desc}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="modal-body">
            <p className="modal-subtitle">Client details — {type}</p>
            <div className="form-grid">
              <div className="form-field">
                <label>Display Name *</label>
                <input
                  type="text"
                  value={form.display_name ?? ''}
                  onChange={e => updateField('display_name', e.target.value)}
                />
              </div>
              <div className="form-field">
                <label>Arabic Name</label>
                <input
                  type="text"
                  value={form.display_name_ar ?? ''}
                  onChange={e => updateField('display_name_ar', e.target.value)}
                />
              </div>
              <div className="form-field">
                <label>Email</label>
                <input
                  type="email"
                  value={form.email ?? ''}
                  onChange={e => updateField('email', e.target.value)}
                />
              </div>
              <div className="form-field">
                <label>Phone</label>
                <input
                  type="text"
                  value={form.phone ?? ''}
                  onChange={e => updateField('phone', e.target.value)}
                />
              </div>
              <div className="form-field form-field-full">
                <label>Address</label>
                <input
                  type="text"
                  value={form.address ?? ''}
                  onChange={e => updateField('address', e.target.value)}
                />
              </div>
              {type === 'individual' && (
                <>
                  <div className="form-field">
                    <label>National ID</label>
                    <input
                      type="text"
                      value={form.national_id ?? ''}
                      onChange={e => updateField('national_id', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Nationality</label>
                    <input
                      type="text"
                      value={form.nationality ?? ''}
                      onChange={e => updateField('nationality', e.target.value)}
                    />
                  </div>
                </>
              )}
              {type === 'company' && (
                <>
                  <div className="form-field">
                    <label>Trade Name</label>
                    <input
                      type="text"
                      value={form.trade_name ?? ''}
                      onChange={e => updateField('trade_name', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>CR Number</label>
                    <input
                      type="text"
                      value={form.cr_number ?? ''}
                      onChange={e => updateField('cr_number', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>VAT Number</label>
                    <input
                      type="text"
                      value={form.vat_number ?? ''}
                      onChange={e => updateField('vat_number', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Sector</label>
                    <input
                      type="text"
                      value={form.sector ?? ''}
                      onChange={e => updateField('sector', e.target.value)}
                    />
                  </div>
                </>
              )}
              {type === 'organisation' && (
                <div className="form-field">
                  <label>Organisation Type</label>
                  <select
                    value={form.org_type ?? ''}
                    onChange={e => updateField('org_type', e.target.value)}
                  >
                    <option value="">Select...</option>
                    <option value="government">Government</option>
                    <option value="ngo">NGO</option>
                    <option value="international">International</option>
                    <option value="semi-govt">Semi-Government</option>
                  </select>
                </div>
              )}
              <div className="form-field form-field-full">
                <label>Notes</label>
                <textarea
                  value={form.notes ?? ''}
                  onChange={e => updateField('notes', e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setStep(0)}
              >
                ← Back
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!form.display_name || saving}
                onClick={handleCreate}
              >
                {saving ? 'Creating...' : 'Create Client'}
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
