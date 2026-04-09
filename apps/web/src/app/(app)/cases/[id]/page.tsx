'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { resolveApiUrl } from '@/lib/api';
import { reportScreenContext } from '@/lib/screenContext';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';
import { officeApi } from '@/lib/officeApi';

type TabId = 'documents' | 'notes' | 'timeline' | 'workflows';

const PRIORITY_COLORS: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#64748b',
};

const EVENT_ICONS: Record<string, string> = {
  created: '➕',
  status_change: '🔄',
  document_added: '📄',
  workflow_run: '▶️',
  note_added: '💬',
  deadline_set: '📅',
  amin_action: '⚡',
  hearing: '⚖️',
  filing: '📋',
};

export default function CaseDetailPage() {
  const params = useParams<{ id: string }>();
  const { navigateTo } = useNavigation();
  const caseApiUrl = resolveApiUrl(`/api/v1/cases/${params.id}`);
  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>('documents');
  const [documents, setDocuments] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [newNote, setNewNote] = useState('');
  const [addingNote, setAddingNote] = useState(false);
  const [creatingDoc, setCreatingDoc] = useState(false);

  const handleCreateDoc = async () => {
    if (!caseData) return;
    setCreatingDoc(true);
    try {
      const doc = await officeApi.createDocument({
        title: `${caseData.title} — Document`,
        doc_type: 'docx',
        template: 'legal_memo',
      });
      await fetch(resolveApiUrl(`/api/v1/cases/${params.id}/documents`), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: doc.id, document_role: 'draft' }),
      });
      loadDocuments();
      navigateTo(`/documents/${doc.id}`);
    } catch {
      /* */
    }
    setCreatingDoc(false);
  };

  useEffect(() => {
    fetch(resolveApiUrl(`/api/v1/cases/${params.id}/set-active`), {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {});

    fetch(caseApiUrl, { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        setCaseData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [caseApiUrl, params.id]);

  useEffect(() => {
    if (!caseData) return;
    reportScreenContext({
      route: `/cases/${params.id}`,
      page_title: `Case: ${caseData.title}`,
      document: null,
      ui_state: {
        case_id: params.id,
        case_title: caseData.title,
        client_name: caseData.client?.display_name,
        practice_area: caseData.practice_area,
      },
    });
  }, [caseData, params.id]);

  const loadDocuments = useCallback(() => {
    fetch(resolveApiUrl(`/api/v1/cases/${params.id}/documents`), {
      credentials: 'include',
    })
      .then(r => (r.ok ? r.json() : []))
      .then(setDocuments)
      .catch(() => {});
  }, [params.id]);

  const loadNotes = useCallback(() => {
    fetch(resolveApiUrl(`/api/v1/cases/${params.id}/notes`), {
      credentials: 'include',
    })
      .then(r => (r.ok ? r.json() : []))
      .then(setNotes)
      .catch(() => {});
  }, [params.id]);

  const loadTimeline = useCallback(() => {
    fetch(resolveApiUrl(`/api/v1/cases/${params.id}/timeline`), {
      credentials: 'include',
    })
      .then(r => (r.ok ? r.json() : []))
      .then(setTimeline)
      .catch(() => {});
  }, [params.id]);

  useEffect(() => {
    if (activeTab === 'documents') loadDocuments();
    if (activeTab === 'notes') loadNotes();
    if (activeTab === 'timeline') loadTimeline();
  }, [activeTab, loadDocuments, loadNotes, loadTimeline]);

  const handleAddNote = async () => {
    if (!newNote.trim()) return;
    setAddingNote(true);
    try {
      await fetch(resolveApiUrl(`/api/v1/cases/${params.id}/notes`), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newNote, is_amin_generated: false }),
      });
      setNewNote('');
      loadNotes();
    } catch {
      /* */
    }
    setAddingNote(false);
  };

  const handleDetachDoc = async (docId: string) => {
    await fetch(
      resolveApiUrl(`/api/v1/cases/${params.id}/documents/${docId}`),
      {
        method: 'DELETE',
        credentials: 'include',
      }
    );
    loadDocuments();
  };

  if (loading)
    return (
      <div
        className="page-container"
        style={{
          height: '100%',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div className="case-topbar">
          <div className="skeleton-group" style={{ gap: 8 }}>
            <div
              className="skeleton-line skeleton-line-xl"
              style={{ width: '35%' }}
            />
            <div className="skeleton-line" style={{ width: '15%' }} />
          </div>
        </div>
        <div
          style={{
            flex: 1,
            display: 'flex',
            gap: 'var(--space-4)',
            padding: 'var(--space-4)',
          }}
        >
          <div
            style={{
              width: '30%',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-4)',
            }}
          >
            <div className="skeleton-card" style={{ height: 100 }} />
            <div className="skeleton-card" style={{ height: 220 }} />
            <div className="skeleton-card" style={{ height: 100 }} />
          </div>
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--space-3)',
            }}
          >
            <div
              className="skeleton-line"
              style={{ width: '50%', height: 36 }}
            />
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton-row">
                <div className="skeleton-group">
                  <div
                    className="skeleton-line"
                    style={{ width: `${65 - i * 10}%` }}
                  />
                  <div
                    className="skeleton-line skeleton-line-sm"
                    style={{ width: '20%' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  if (!caseData)
    return (
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
        <h3>Case not found</h3>
      </div>
    );

  const isOverdue =
    caseData.next_deadline && new Date(caseData.next_deadline) < new Date();
  const isDueSoon =
    caseData.next_deadline &&
    !isOverdue &&
    new Date(caseData.next_deadline) <= new Date(Date.now() + 7 * 86400000);

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: 'documents', label: 'Documents', count: caseData.document_count },
    { id: 'notes', label: 'Notes', count: caseData.note_count },
    { id: 'timeline', label: 'Timeline' },
    { id: 'workflows', label: 'Workflows' },
  ];

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
      {/* Top bar */}
      <div className="case-topbar">
        <div className="case-topbar-left">
          <span className="case-topbar-pa">
            {caseData.practice_area?.replace(/_/g, ' ')}
          </span>
          <h1 className="case-topbar-title">{caseData.title}</h1>
          <span
            className={`badge badge-status badge-status-${caseData.status}`}
          >
            {caseData.status}
          </span>
        </div>
        <div className="case-topbar-center">
          {caseData.client && (
            <button
              type="button"
              className="case-topbar-client"
              onClick={() => navigateTo(`/clients/${caseData.client.id}`)}
            >
              {caseData.client.display_name}
            </button>
          )}
        </div>
        <div className="case-topbar-right">
          <button
            type="button"
            className="btn btn-sm btn-outline"
            onClick={() => navigateTo(`/cases/${params.id}/edit`)}
          >
            Edit
          </button>
        </div>
      </div>

      {caseData.next_deadline && (
        <div
          className={`case-deadline-bar ${isOverdue ? 'case-deadline-overdue' : isDueSoon ? 'case-deadline-soon' : ''}`}
        >
          📅 {caseData.next_deadline_description ?? 'Deadline'}:{' '}
          {caseData.next_deadline}
        </div>
      )}

      <div
        className="case-detail-body"
        style={{
          flex: 1,
          display: 'flex',
          gap: 'var(--space-4)',
          overflow: 'hidden',
          padding: 'var(--space-4)',
        }}
      >
        {/* Left column - metadata */}
        <div
          className="case-detail-left"
          style={{ width: '30%', overflow: 'auto' }}
        >
          {caseData.client && (
            <div
              className="detail-card"
              onClick={() => navigateTo(`/clients/${caseData.client.id}`)}
              style={{ cursor: 'pointer' }}
            >
              <h3 className="detail-card-title">Client</h3>
              <div className="detail-field">
                <span>{caseData.client.display_name}</span>
              </div>
              <div className="detail-field">
                <span className="detail-label">
                  {caseData.client.client_type}
                </span>
              </div>
            </div>
          )}

          <div className="detail-card">
            <h3 className="detail-card-title">Details</h3>
            <div className="detail-field">
              <span className="detail-label">Practice Area</span>
              <span>{caseData.practice_area?.replace(/_/g, ' ')}</span>
            </div>
            <div className="detail-field">
              <span className="detail-label">Jurisdiction</span>
              <span>{caseData.jurisdiction}</span>
            </div>
            <div className="detail-field">
              <span className="detail-label">Priority</span>
              <span style={{ color: PRIORITY_COLORS[caseData.priority] }}>
                {caseData.priority}
              </span>
            </div>
            {caseData.case_number && (
              <div className="detail-field">
                <span className="detail-label">Case Number</span>
                <span>{caseData.case_number}</span>
              </div>
            )}
            {caseData.internal_ref && (
              <div className="detail-field">
                <span className="detail-label">Internal Ref</span>
                <span>{caseData.internal_ref}</span>
              </div>
            )}
            {caseData.court_name && (
              <div className="detail-field">
                <span className="detail-label">Court</span>
                <span>{caseData.court_name}</span>
              </div>
            )}
            {caseData.court_circuit && (
              <div className="detail-field">
                <span className="detail-label">Circuit</span>
                <span>{caseData.court_circuit}</span>
              </div>
            )}
            {caseData.opposing_party && (
              <div className="detail-field">
                <span className="detail-label">Opposing Party</span>
                <span>{caseData.opposing_party}</span>
              </div>
            )}
            {caseData.opposing_counsel && (
              <div className="detail-field">
                <span className="detail-label">Opposing Counsel</span>
                <span>{caseData.opposing_counsel}</span>
              </div>
            )}
            <div className="detail-field">
              <span className="detail-label">Opened</span>
              <span>{caseData.opened_at}</span>
            </div>
            {caseData.closed_at && (
              <div className="detail-field">
                <span className="detail-label">Closed</span>
                <span>{caseData.closed_at}</span>
              </div>
            )}
          </div>

          {caseData.amin_briefing && (
            <div className="detail-card">
              <h3 className="detail-card-title">⚡ Amin&apos;s Case Brief</h3>
              <p className="detail-briefing">{caseData.amin_briefing}</p>
            </div>
          )}

          <div className="case-quick-actions">
            <button
              type="button"
              className="btn btn-sm btn-primary btn-full"
              onClick={() => navigateTo(`/workflows?case=${params.id}`)}
            >
              ▶ Start Workflow
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline btn-full"
              onClick={() => navigateTo(`/research?case=${params.id}`)}
            >
              + New Research
            </button>
          </div>
        </div>

        {/* Right column - tabbed content */}
        <div
          className="case-detail-right"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div className="case-tabs">
            {tabs.map(tab => (
              <button
                key={tab.id}
                type="button"
                className={`case-tab${activeTab === tab.id ? ' case-tab-active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
                {tab.count !== undefined && tab.count > 0 && (
                  <span className="case-tab-count">{tab.count}</span>
                )}
              </button>
            ))}
          </div>

          <div
            className="case-tab-content"
            style={{ flex: 1, overflow: 'auto' }}
          >
            {activeTab === 'documents' && (
              <div>
                <div
                  style={{
                    display: 'flex',
                    gap: 'var(--space-2)',
                    marginBottom: 'var(--space-4)',
                  }}
                >
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={handleCreateDoc}
                    disabled={creatingDoc}
                  >
                    {creatingDoc ? 'Creating...' : '+ New Document'}
                  </button>
                </div>
                {documents.length === 0 && (
                  <div className="tab-empty">
                    <div
                      className="page-empty-icon"
                      style={{ margin: '0 auto var(--space-3)' }}
                    >
                      <svg
                        width="24"
                        height="24"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M7 3h8l4 4v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" />
                        <path d="M15 3v5h5" />
                      </svg>
                    </div>
                    No documents attached yet.
                  </div>
                )}
                {documents.map(d => (
                  <div key={d.id} className="doc-row">
                    <span className="doc-row-title">{d.document_title}</span>
                    <span className="badge badge-sm">{d.document_role}</span>
                    <span className="doc-row-date">
                      {new Date(d.attached_at).toLocaleDateString()}
                    </span>
                    <button
                      type="button"
                      className="btn btn-xs btn-outline"
                      onClick={() => navigateTo(`/documents/${d.document_id}`)}
                    >
                      Open
                    </button>
                    <button
                      type="button"
                      className="btn btn-xs btn-danger"
                      onClick={() => handleDetachDoc(d.document_id)}
                    >
                      Detach
                    </button>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'notes' && (
              <div>
                <div className="note-input-row">
                  <textarea
                    className="note-textarea"
                    placeholder="Add a note..."
                    value={newNote}
                    onChange={e => setNewNote(e.target.value)}
                    rows={2}
                  />
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    disabled={!newNote.trim() || addingNote}
                    onClick={handleAddNote}
                  >
                    {addingNote ? 'Saving...' : 'Add Note'}
                  </button>
                </div>
                {notes.length === 0 && (
                  <div className="tab-empty">No notes yet.</div>
                )}
                {notes.map(n => (
                  <div
                    key={n.id}
                    className={`note-card ${n.is_amin_generated ? 'note-card-amin' : ''}`}
                  >
                    <div className="note-card-header">
                      <span className="note-card-author">
                        {n.is_amin_generated
                          ? '⚡ Amin'
                          : (n.created_by_name ?? 'User')}
                      </span>
                      <span className="note-card-date">
                        {new Date(n.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="note-card-content">{n.content}</div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'timeline' && (
              <div className="timeline">
                {timeline.length === 0 && (
                  <div className="tab-empty">No events yet.</div>
                )}
                {timeline.map(e => (
                  <div
                    key={e.id}
                    className={`timeline-event timeline-event-${e.event_type}`}
                  >
                    <span className="timeline-event-icon">
                      {EVENT_ICONS[e.event_type] ?? '•'}
                    </span>
                    <div className="timeline-event-body">
                      <span className="timeline-event-title">{e.title}</span>
                      {e.description && (
                        <span className="timeline-event-desc">
                          {e.description}
                        </span>
                      )}
                      <span className="timeline-event-date">
                        {new Date(e.event_date).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'workflows' && (
              <div>
                <p className="tab-info">
                  Workflows relevant to{' '}
                  {caseData.practice_area?.replace(/_/g, ' ')} cases.
                </p>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() =>
                    navigateTo(
                      `/workflows/${caseData.practice_area ?? 'litigation'}?case=${params.id}`
                    )
                  }
                >
                  Browse {caseData.practice_area?.replace(/_/g, ' ')} Workflows
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
