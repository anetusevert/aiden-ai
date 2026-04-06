'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { officeApi } from '@/lib/officeApi';
import { reportScreenContext } from '@/lib/screenContext';

type EditorStatus =
  | 'loading'
  | 'checking'
  | 'ready'
  | 'saving'
  | 'error'
  | 'unavailable';

const COLLABORA_URL =
  process.env.NEXT_PUBLIC_COLLABORA_URL || 'http://localhost:9980';
const COLLABORA_ENABLED = process.env.NEXT_PUBLIC_COLLABORA_ENABLED !== 'false';

async function checkCollaboraHealth(collaboraUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${collaboraUrl}/hosting/capabilities`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000),
      mode: 'no-cors', // Collabora doesn't set CORS headers on this endpoint
    });
    // no-cors requests always return opaque (status 0), so reaching here means server is up
    return res.type === 'opaque' || res.ok;
  } catch {
    return false;
  }
}

interface CollaboraEditorProps {
  docId: string;
  title?: string;
  docType?: string;
  metadata?: Record<string, unknown>;
  onClose?: () => void;
  onSave?: (docId: string) => void;
}

function normalizeMessage(data: unknown): {
  MessageId?: string;
  Values?: Record<string, unknown>;
} {
  if (typeof data === 'string') {
    try {
      return JSON.parse(data) as {
        MessageId?: string;
        Values?: Record<string, unknown>;
      };
    } catch {
      return {};
    }
  }
  if (typeof data === 'object' && data) {
    return data as { MessageId?: string; Values?: Record<string, unknown> };
  }
  return {};
}

export function useCollaboraCommands(
  iframeRef: React.RefObject<HTMLIFrameElement | null>
) {
  const postMessage = useCallback(
    (payload: Record<string, unknown>) => {
      iframeRef.current?.contentWindow?.postMessage(payload, '*');
    },
    [iframeRef]
  );

  return useMemo(
    () => ({
      save: () =>
        postMessage({
          MessageId: 'Action_Save',
          SendTime: Date.now(),
          Values: {
            DontTerminateEdit: true,
            DontSaveIfUnmodified: true,
          },
        }),
      gotoPage: (part: number | string) =>
        postMessage({
          MessageId: 'Action_ChangePartPage',
          Values: { PartHashId: part },
        }),
      gotoSlide: (part: number | string) =>
        postMessage({
          MessageId: 'Action_ChangePartPage',
          Values: { PartHashId: part },
        }),
      gotoSheet: (sheet: string) =>
        postMessage({
          MessageId: 'Action_ChangePartPage',
          Values: { PartHashId: sheet },
        }),
      executeUno: (command: string) =>
        postMessage({
          MessageId: 'Send_UNO_Command',
          Values: { Command: command },
        }),
      reload: () => window.dispatchEvent(new CustomEvent('collabora-reload')),
    }),
    [postMessage]
  );
}

// ─── Fallback UI ─────────────────────────────────────────────────────────────

function CollaboraUnavailable({
  docId,
  onRetry,
}: {
  docId: string;
  onRetry: () => void;
}) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    await new Promise(r => setTimeout(r, 300));
    onRetry();
    setRetrying(false);
  };

  const handleDownload = () => {
    window.open(officeApi.getDownloadUrl(docId), '_blank');
  };

  const handleAskAmin = () => {
    window.dispatchEvent(
      new CustomEvent('amin-prefill', {
        detail: { text: 'Help me draft content for this document.' },
      })
    );
  };

  return (
    <div className="collabora-unavailable">
      <div className="collabora-unavailable-card">
        <div className="collabora-unavailable-icon">
          <svg
            width="40"
            height="40"
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
        <h3 className="collabora-unavailable-title">
          Document Editor Unavailable
        </h3>
        <p className="collabora-unavailable-detail">
          Collabora Online is not running. Start it with:
        </p>
        <code className="collabora-unavailable-cmd">
          docker compose up collabora
        </code>

        <div className="collabora-unavailable-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleRetry}
            disabled={retrying}
          >
            {retrying ? (
              <>
                <span className="spinner spinner-sm" /> Checking...
              </>
            ) : (
              'Retry'
            )}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={handleDownload}
          >
            Download Template
          </button>
        </div>

        <button
          type="button"
          className="collabora-unavailable-amin-link"
          onClick={handleAskAmin}
        >
          You can still ask Amin to help draft content →
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function CollaboraEditor({
  docId,
  title,
  docType,
  metadata,
  onClose,
  onSave,
}: CollaboraEditorProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [editorUrl, setEditorUrl] = useState<string | null>(null);
  const [editorStatus, setEditorStatus] = useState<EditorStatus>('checking');
  const [currentPage, setCurrentPage] = useState<number | null>(null);
  const [currentSlide, setCurrentSlide] = useState<number | null>(null);
  const [currentSheet, setCurrentSheet] = useState<string | null>(null);
  const [isModified, setIsModified] = useState(false);
  const commands = useCollaboraCommands(iframeRef);

  const publishContext = useCallback(
    (
      overrides?: Partial<{
        page: number | null;
        slide: number | null;
        sheet: string | null;
      }>
    ) => {
      reportScreenContext({
        route: `/documents/${docId}`,
        page_title: title ? `${title} | Documents` : 'Documents',
        document: {
          doc_id: docId,
          title: title || 'Untitled document',
          doc_type: docType || 'docx',
          current_view: 'editor',
          current_page: overrides?.page ?? currentPage,
          current_slide: overrides?.slide ?? currentSlide,
          current_sheet: overrides?.sheet ?? currentSheet,
          metadata,
        },
        ui_state: {
          editor_status: editorStatus,
          modified: isModified,
        },
      });
    },
    [
      currentPage,
      currentSheet,
      currentSlide,
      docId,
      docType,
      editorStatus,
      isModified,
      metadata,
      title,
    ]
  );

  const loadEditor = useCallback(async () => {
    setEditorStatus('checking');

    // Fast-path: env var disables Collabora entirely
    if (!COLLABORA_ENABLED) {
      setEditorStatus('unavailable');
      return;
    }

    const healthy = await checkCollaboraHealth(COLLABORA_URL);
    if (!healthy) {
      setEditorStatus('unavailable');
      return;
    }

    try {
      setEditorStatus('loading');
      const data = await officeApi.generateWopiToken(docId);
      setEditorUrl(data.collabora_editor_url);
    } catch {
      setEditorStatus('error');
    }
  }, [docId]);

  useEffect(() => {
    void loadEditor();
  }, [loadEditor]);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.source !== iframeRef.current?.contentWindow) return;
      const payload = normalizeMessage(event.data);
      const messageId = payload.MessageId;
      const values = payload.Values ?? {};

      if (
        messageId === 'App_LoadingStatus' &&
        values.Status === 'Frame_Ready'
      ) {
        setEditorStatus('ready');
        publishContext();
        return;
      }

      if (messageId === 'App_PartHashChanged') {
        const part = values.PartHashId;
        if (typeof part === 'number') {
          setCurrentSlide(part);
          setCurrentPage(part);
          publishContext({ page: part, slide: part });
        } else if (typeof part === 'string') {
          setCurrentSheet(part);
          publishContext({ sheet: part });
        }
        return;
      }

      if (messageId === 'Doc_ModifiedStatus') {
        setIsModified(Boolean(values.Modified ?? values.modified));
        return;
      }

      if (messageId === 'Action_Save_Resp') {
        setEditorStatus('ready');
        setIsModified(false);
        onSave?.(docId);
        publishContext();
        window.dispatchEvent(
          new CustomEvent('collabora-saved', { detail: { docId } })
        );
      }
    };

    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [docId, onSave, publishContext]);

  useEffect(() => {
    const reloadHandler = async (event: Event) => {
      const customEvent = event as CustomEvent<{ docId?: string }>;
      if (customEvent.detail?.docId && customEvent.detail.docId !== docId)
        return;
      await loadEditor();
    };
    const navigateHandler = (event: Event) => {
      const customEvent = event as CustomEvent<{
        target_type?: string;
        target_value?: string | number;
      }>;
      const targetType = customEvent.detail?.target_type;
      const targetValue = customEvent.detail?.target_value;
      if (targetType === 'sheet' && typeof targetValue === 'string') {
        commands.gotoSheet(targetValue);
      } else if (
        (targetType === 'page' || targetType === 'slide') &&
        targetValue != null
      ) {
        commands.gotoPage(targetValue);
      }
    };
    const saveHandler = () => {
      setEditorStatus('saving');
      commands.save();
    };
    const unoHandler = (event: Event) => {
      const customEvent = event as CustomEvent<{ command?: string }>;
      if (customEvent.detail?.command)
        commands.executeUno(customEvent.detail.command);
    };

    window.addEventListener('collabora-reload', reloadHandler as EventListener);
    window.addEventListener(
      'collabora-navigate',
      navigateHandler as EventListener
    );
    window.addEventListener('collabora-save', saveHandler);
    window.addEventListener('collabora-uno', unoHandler as EventListener);
    return () => {
      window.removeEventListener(
        'collabora-reload',
        reloadHandler as EventListener
      );
      window.removeEventListener(
        'collabora-navigate',
        navigateHandler as EventListener
      );
      window.removeEventListener('collabora-save', saveHandler);
      window.removeEventListener('collabora-uno', unoHandler as EventListener);
    };
  }, [commands, docId, loadEditor]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (editorStatus === 'ready') commands.save();
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [commands, editorStatus]);

  if (editorStatus === 'unavailable') {
    return (
      <CollaboraUnavailable docId={docId} onRetry={() => void loadEditor()} />
    );
  }

  return (
    <div className="collabora-wrapper">
      <div className="collabora-topbar">
        <div>
          <strong>{title || 'Document Editor'}</strong>
          <span className="collabora-status">
            {editorStatus === 'saving'
              ? 'Saving...'
              : isModified
                ? 'Unsaved changes'
                : editorStatus === 'ready'
                  ? 'Live'
                  : 'Preparing'}
          </span>
        </div>
        <div className="collabora-topbar-actions">
          <button className="btn btn-outline" onClick={() => commands.save()}>
            Save
          </button>
          {onClose ? (
            <button className="btn btn-primary" onClick={onClose}>
              Close Editor
            </button>
          ) : null}
        </div>
      </div>

      {editorUrl ? (
        <iframe
          ref={iframeRef}
          className="collabora-iframe"
          src={editorUrl}
          title={title || 'Collabora editor'}
          allow="clipboard-read; clipboard-write"
        />
      ) : null}

      {editorStatus !== 'ready' ? (
        <div className="collabora-loading">
          <span className="spinner spinner-lg" />
          <p>Amin is preparing your document...</p>
        </div>
      ) : null}
    </div>
  );
}
