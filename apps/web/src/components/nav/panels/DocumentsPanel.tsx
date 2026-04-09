'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useNavigation } from '@/components/NavigationLoader';
import { officeApi, type OfficeDocument } from '@/lib/officeApi';

const DOC_TYPE_LABELS: Record<string, string> = {
  docx: 'DOCX',
  xlsx: 'XLSX',
  pptx: 'PPTX',
  pdf: 'PDF',
};

const DOC_TYPE_ICON: Record<string, React.ReactNode> = {
  docx: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M7 3h8l4 4v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" />
      <path d="M15 3v5h5" />
    </svg>
  ),
  xlsx: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18" />
      <path d="M3 15h18" />
      <path d="M9 3v18" />
    </svg>
  ),
  pptx: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8" />
      <path d="M12 17v4" />
    </svg>
  ),
  pdf: (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M7 3h8l4 4v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" />
      <path d="M15 3v5h5" />
      <path d="M8 13h8" />
      <path d="M8 17h5" />
    </svg>
  ),
};

function defaultDocIcon() {
  return DOC_TYPE_ICON.docx;
}

export function DocumentsPanel() {
  const pathname = usePathname();
  const { navigateTo } = useNavigation();
  const [docs, setDocs] = useState<OfficeDocument[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    officeApi
      .listDocuments({ limit: 6 })
      .then(res => setDocs(res.items))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  return (
    <>
      <div className="r2-header">DOCUMENTS</div>

      <div className="r2-section">
        <button
          className="r2-new-doc-btn"
          onClick={() => navigateTo('/documents/new')}
          type="button"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Document
        </button>
      </div>

      {loaded && docs.length === 0 && (
        <div className="r2-empty">
          <p className="r2-empty-text">Create your first document with Amin</p>
        </div>
      )}

      {docs.length > 0 && (
        <div className="r2-link-list">
          {docs.map(doc => {
            const href = `/documents/${doc.id}`;
            return (
              <Link
                key={doc.id}
                href={href}
                className={`r2-link${isActive(href) ? ' r2-link-active' : ''}`}
                onClick={e => {
                  e.preventDefault();
                  navigateTo(href);
                }}
              >
                <span className="r2-link-icon">
                  {DOC_TYPE_ICON[doc.doc_type] ?? defaultDocIcon()}
                </span>
                <span className="r2-link-text">{doc.title}</span>
                <span className="r2-doc-badge">
                  {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type.toUpperCase()}
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
