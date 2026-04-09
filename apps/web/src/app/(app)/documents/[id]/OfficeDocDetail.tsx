'use client';

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { useAminContext } from '@/components/amin/AminProvider';
import { CollaboraEditor } from '@/components/office/CollaboraEditor';
import { officeApi, type OfficeDocument } from '@/lib/officeApi';
import { routeTransition } from '@/lib/motion';
import { reportScreenContext } from '@/lib/screenContext';

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderPreview(document: OfficeDocument) {
  const metadata = document.metadata_ ?? {};
  const previewText =
    typeof metadata.preview_text === 'string'
      ? metadata.preview_text
      : Array.isArray(metadata.preview_paragraphs)
        ? metadata.preview_paragraphs.join('\n\n')
        : null;
  const sheets = metadata.sheet_names;
  const slides = metadata.slide_titles;

  if (document.doc_type === 'pdf') {
    return (
      <iframe
        title={`${document.title} preview`}
        src={`${officeApi.getDownloadUrl(document.id)}#toolbar=0`}
        style={{
          width: '100%',
          minHeight: 560,
          border: '1px solid rgba(148, 163, 184, 0.2)',
          borderRadius: 12,
          background: '#fff',
        }}
      />
    );
  }

  if (typeof previewText === 'string' && previewText.trim()) {
    return <pre className="document-preview-text">{previewText}</pre>;
  }

  if (Array.isArray(sheets) && sheets.length > 0) {
    return (
      <div className="document-preview-list">
        {sheets.map(sheet => (
          <div key={String(sheet)} className="document-preview-chip">
            {String(sheet)}
          </div>
        ))}
      </div>
    );
  }

  if (Array.isArray(slides) && slides.length > 0) {
    return (
      <div className="document-preview-list">
        {slides.map((slide, index) => (
          <div
            key={`${index}-${String(slide)}`}
            className="document-preview-card"
          >
            <strong>Slide {index + 1}</strong>
            <span>{String(slide)}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="document-preview-empty">
      Amin will enrich the live preview as the document is edited and saved.
    </div>
  );
}

export function OfficeDocDetail({ docId }: { docId: string }) {
  const { navigateTo } = useNavigation();
  const { openPanel } = useAminContext();
  const [document, setDocument] = useState<OfficeDocument | null>(null);
  const [mode, setMode] = useState<'view' | 'edit'>('view');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState('');

  useEffect(() => {
    async function loadDocument() {
      try {
        setLoading(true);
        const data = await officeApi.getDocument(docId);
        setDocument(data);
        setDraftTitle(data.title);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to load document.'
        );
      } finally {
        setLoading(false);
      }
    }

    void loadDocument();
  }, [docId]);

  useEffect(() => {
    if (!document) return;
    reportScreenContext({
      route: `/documents/${document.id}`,
      page_title: `${document.title} | Documents`,
      document: {
        doc_id: document.id,
        title: document.title,
        doc_type: document.doc_type,
        current_view: mode === 'edit' ? 'editor' : 'viewer',
        current_page: null,
        current_slide: null,
        current_sheet: null,
        metadata: document.metadata_,
      },
      ui_state: {
        mode,
      },
    });
  }, [document, mode]);

  const pageMeta = useMemo(() => {
    if (!document) return [];
    const metadata = document.metadata_ ?? {};
    const baseMeta: Array<[string, string]> = [
      ['Type', document.doc_type.toUpperCase()],
      ['Size', formatBytes(document.size_bytes)],
      ['Updated', new Date(document.updated_at).toLocaleString()],
    ];
    if (typeof metadata.page_count === 'number') {
      baseMeta.push(['Pages', String(metadata.page_count)]);
    }
    return baseMeta;
  }, [document]);

  const canEdit = document?.doc_type !== 'pdf';

  async function handleSaveTitle() {
    if (!document || draftTitle.trim() === document.title) return;
    try {
      const updated = await officeApi.updateDocument(document.id, {
        title: draftTitle.trim(),
      });
      setDocument(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to rename document.'
      );
    }
  }

  async function handleDeleteDocument() {
    if (!document) return;
    const confirmed = window.confirm(`Delete "${document.title}"?`);
    if (!confirmed) return;

    try {
      await officeApi.deleteDocument(document.id);
      navigateTo('/documents');
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to delete document.'
      );
    }
  }

  function askAmin() {
    if (!document) return;
    openPanel();
    window.dispatchEvent(
      new CustomEvent('amin-prefill', {
        detail: {
          text: `Please help me improve this document: ${document.title}`,
        },
      })
    );
  }

  if (loading) {
    return (
      <div className="loading">
        <span className="spinner" />
        <span>Loading document...</span>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="alert alert-error">{error || 'Document not found.'}</div>
    );
  }

  return (
    <motion.div {...routeTransition} className="document-view-page">
      {error ? <div className="alert alert-error">{error}</div> : null}

      {mode === 'view' ? (
        <div className="document-view-shell">
          <div className="page-header">
            <div className="page-header-row">
              <div>
                <h1 className="page-title">{document.title}</h1>
                <p className="page-subtitle">
                  {canEdit
                    ? 'Live office document with Collabora editing and Amin context awareness.'
                    : 'Presentation PDF with browser-native preview and download support.'}
                </p>
              </div>
              <div className="document-actions">
                <button className="btn btn-outline" onClick={askAmin}>
                  Ask Amin
                </button>
                {canEdit ? (
                  <button
                    className="btn btn-outline"
                    onClick={() => setMode('edit')}
                  >
                    Open in Editor
                  </button>
                ) : null}
                <a
                  className="btn btn-primary"
                  href={officeApi.getDownloadUrl(document.id)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download
                </a>
              </div>
            </div>
          </div>

          <div className="document-detail-grid">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Metadata</h3>
              </div>
              <div className="card-body document-meta-list">
                {pageMeta.map(([label, value]) => (
                  <div key={label} className="document-meta-row">
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
              <div className="card-footer document-footer-actions">
                <button
                  className="btn btn-outline"
                  onClick={handleDeleteDocument}
                >
                  Delete
                </button>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Preview</h3>
              </div>
              <div className="card-body">{renderPreview(document)}</div>
            </div>
          </div>
        </div>
      ) : canEdit ? (
        <div className="document-editor-shell">
          <div className="document-editor-header">
            <input
              className="document-title-input"
              value={draftTitle}
              onChange={event => setDraftTitle(event.target.value)}
              onBlur={handleSaveTitle}
            />
            <div className="document-actions">
              <button className="btn btn-outline" onClick={askAmin}>
                Ask Amin
              </button>
              <button
                className="btn btn-outline"
                onClick={() =>
                  window.dispatchEvent(new CustomEvent('collabora-save'))
                }
              >
                Save
              </button>
              <button
                className="btn btn-primary"
                onClick={() => setMode('view')}
              >
                Close Editor
              </button>
            </div>
          </div>

          <CollaboraEditor
            docId={document.id}
            title={document.title}
            docType={document.doc_type}
            metadata={document.metadata_}
            onClose={() => setMode('view')}
            onSave={() => {
              void officeApi
                .getDocument(document.id)
                .then(setDocument)
                .catch(() => {});
            }}
          />
        </div>
      ) : (
        <div className="alert alert-error">
          PDF documents are view-only in this workspace.
        </div>
      )}
    </motion.div>
  );
}
