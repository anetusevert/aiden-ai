'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  officeApi,
  type OfficeDocType,
  type OfficeDocument,
} from '@/lib/officeApi';
import {
  staggerContainer,
  staggerItem,
  routeTransition,
  glassReveal,
} from '@/lib/motion';
import { useNavigation } from '@/components/NavigationLoader';

const FILTERS: Array<{ key: 'all' | OfficeDocType; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'docx', label: 'Word' },
  { key: 'xlsx', label: 'Excel' },
  { key: 'pptx', label: 'PowerPoint' },
];

const TEMPLATE_OPTIONS: Record<OfficeDocType, string[]> = {
  docx: ['blank', 'legal_memo', 'contract', 'nda', 'court_brief'],
  xlsx: ['blank', 'budget', 'tracker', 'legal_matrix'],
  pptx: ['blank', 'pitch', 'status_update', 'legal_overview'],
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function iconForDocType(docType: OfficeDocType) {
  if (docType === 'docx') return 'DOCX';
  if (docType === 'xlsx') return 'XLSX';
  return 'PPTX';
}

export default function DocumentsPage() {
  const { navigateTo } = useNavigation();
  const [documents, setDocuments] = useState<OfficeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | OfficeDocType>('all');
  const [search, setSearch] = useState('');
  const [showCreatePanel, setShowCreatePanel] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newDocType, setNewDocType] = useState<OfficeDocType>('docx');
  const [newTemplate, setNewTemplate] = useState('blank');
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    async function loadDocuments() {
      try {
        setLoading(true);
        const data = await officeApi.listDocuments({
          doc_type: filter === 'all' ? undefined : filter,
          search: search || undefined,
        });
        setDocuments(data.items);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to load documents.'
        );
      } finally {
        setLoading(false);
      }
    }

    void loadDocuments();
  }, [filter, search]);

  useEffect(() => {
    setNewTemplate(TEMPLATE_OPTIONS[newDocType][0]);
  }, [newDocType]);

  const emptyTitle = useMemo(() => {
    if (newDocType === 'docx') return 'New Legal Memo';
    if (newDocType === 'xlsx') return 'New Legal Tracker';
    return 'New Legal Overview';
  }, [newDocType]);

  async function handleCreateDocument() {
    try {
      setCreating(true);
      const document = await officeApi.createDocument({
        title: newTitle.trim() || emptyTitle,
        doc_type: newDocType,
        template: newTemplate,
      });
      setShowCreatePanel(false);
      navigateTo(`/documents/${document.id}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create document.'
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <motion.div {...routeTransition} className="documents-page">
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h1 className="page-title">Documents</h1>
            <p className="page-subtitle">
              Create and manage live Word, Excel, and PowerPoint documents with
              Amin.
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreatePanel(true)}
          >
            New Document
          </button>
        </div>
      </div>

      <div className="documents-toolbar">
        <div className="doc-filter-tabs">
          {FILTERS.map(item => (
            <button
              key={item.key}
              className={`doc-filter-tab ${filter === item.key ? 'is-active' : ''}`}
              onClick={() => setFilter(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <input
          className="form-input documents-search"
          placeholder="Search documents"
          value={search}
          onChange={event => setSearch(event.target.value)}
        />
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {loading ? (
        <div className="loading">
          <span className="spinner" />
          <span>Loading documents...</span>
        </div>
      ) : (
        <motion.div
          className="documents-grid"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          {documents.map(document => (
            <motion.button
              key={document.id}
              type="button"
              className="doc-card"
              variants={staggerItem}
              onClick={() => navigateTo(`/documents/${document.id}`)}
            >
              <div className="doc-card-icon">
                {iconForDocType(document.doc_type)}
              </div>
              <div className="doc-card-title">{document.title}</div>
              <div className="doc-card-meta">
                <span>{formatDate(document.updated_at)}</span>
                <span>{formatBytes(document.size_bytes)}</span>
              </div>
            </motion.button>
          ))}
          {documents.length === 0 ? (
            <div className="card">
              <div className="card-body">
                No office documents yet. Create one to start editing with Amin
                and Collabora.
              </div>
            </div>
          ) : null}
        </motion.div>
      )}

      {showCreatePanel ? (
        <motion.div className="create-doc-panel" {...glassReveal}>
          <div className="create-doc-panel-header">
            <h3>Create document</h3>
            <button
              className="amin-panel-close"
              onClick={() => setShowCreatePanel(false)}
            >
              Close
            </button>
          </div>

          <div className="create-doc-type-grid">
            {(Object.keys(TEMPLATE_OPTIONS) as OfficeDocType[]).map(type => (
              <button
                key={type}
                className={`create-doc-type-btn ${newDocType === type ? 'is-active' : ''}`}
                onClick={() => setNewDocType(type)}
              >
                {iconForDocType(type)}
              </button>
            ))}
          </div>

          <div className="form-group">
            <label className="form-label">Title</label>
            <input
              className="form-input"
              value={newTitle}
              onChange={event => setNewTitle(event.target.value)}
              placeholder={emptyTitle}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Template</label>
            <select
              className="form-select"
              value={newTemplate}
              onChange={event => setNewTemplate(event.target.value)}
            >
              {TEMPLATE_OPTIONS[newDocType].map(template => (
                <option key={template} value={template}>
                  {template}
                </option>
              ))}
            </select>
          </div>

          <div className="create-doc-panel-actions">
            <button
              className="btn btn-outline"
              onClick={() => setShowCreatePanel(false)}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleCreateDocument}
              disabled={creating}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </motion.div>
      ) : null}
    </motion.div>
  );
}
