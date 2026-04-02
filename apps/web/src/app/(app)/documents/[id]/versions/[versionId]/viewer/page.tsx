'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  DocumentChunkResponse,
  DocumentChunksResponse,
  DocumentTextResponse,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';

interface ViewerParams {
  params: {
    id: string;
    versionId: string;
  };
}

export default function DocumentViewerPage({ params }: ViewerParams) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const { id: documentId, versionId } = params;

  const chunkIdParam = searchParams.get('chunkId');
  const chunkIndexParam = searchParams.get('chunkIndex');

  // Data state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [textData, setTextData] = useState<DocumentTextResponse | null>(null);
  const [chunksData, setChunksData] = useState<DocumentChunksResponse | null>(
    null
  );

  // UI state
  const [selectedChunk, setSelectedChunk] =
    useState<DocumentChunkResponse | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Refs
  const sidebarRef = useRef<HTMLDivElement>(null);
  const chunkRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!documentId || !versionId || authLoading || !isAuthenticated) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [textRes, chunksRes] = await Promise.all([
          apiClient
            .getDocumentVersionText(documentId, versionId, true)
            .catch(() => null),
          apiClient.getDocumentVersionChunks(documentId, versionId),
        ]);

        setTextData(textRes);
        setChunksData(chunksRes);

        if (chunksRes && chunksRes.chunks.length > 0) {
          let targetChunk: DocumentChunkResponse | null = null;

          if (chunkIdParam) {
            targetChunk =
              chunksRes.chunks.find(c => c.id === chunkIdParam) || null;
          } else if (chunkIndexParam) {
            const idx = parseInt(chunkIndexParam, 10);
            targetChunk =
              chunksRes.chunks.find(c => c.chunk_index === idx) || null;
          }

          setSelectedChunk(targetChunk || chunksRes.chunks[0]);
        }
      } catch (err) {
        if (err instanceof Error) {
          if (err.message.includes('404')) {
            setError('Document version not found or text not extracted.');
          } else if (err.message.includes('403')) {
            setError('You do not have permission to view this document.');
          } else {
            setError(err.message);
          }
        } else {
          setError('Failed to load document');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [
    documentId,
    versionId,
    authLoading,
    isAuthenticated,
    chunkIdParam,
    chunkIndexParam,
  ]);

  const scrollToChunkInSidebar = useCallback((chunkId: string) => {
    const element = chunkRefs.current.get(chunkId);
    if (element && sidebarRef.current) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  const handleChunkSelect = useCallback(
    (chunk: DocumentChunkResponse) => {
      setSelectedChunk(chunk);
      scrollToChunkInSidebar(chunk.id);

      const url = new URL(window.location.href);
      url.searchParams.set('chunkId', chunk.id);
      url.searchParams.delete('chunkIndex');
      window.history.replaceState({}, '', url.toString());
    },
    [scrollToChunkInSidebar]
  );

  const goToPrevChunk = useCallback(() => {
    if (!selectedChunk || !chunksData) return;
    const currentIndex = chunksData.chunks.findIndex(
      c => c.id === selectedChunk.id
    );
    if (currentIndex > 0) {
      handleChunkSelect(chunksData.chunks[currentIndex - 1]);
    }
  }, [selectedChunk, chunksData, handleChunkSelect]);

  const goToNextChunk = useCallback(() => {
    if (!selectedChunk || !chunksData) return;
    const currentIndex = chunksData.chunks.findIndex(
      c => c.id === selectedChunk.id
    );
    if (currentIndex < chunksData.chunks.length - 1) {
      handleChunkSelect(chunksData.chunks[currentIndex + 1]);
    }
  }, [selectedChunk, chunksData, handleChunkSelect]);

  const filteredChunks =
    chunksData?.chunks.filter(chunk => {
      if (!searchQuery.trim()) return true;
      const lowerQuery = searchQuery.toLowerCase();
      return chunk.text.toLowerCase().includes(lowerQuery);
    }) || [];

  const getPrevChunk = (): DocumentChunkResponse | null => {
    if (!selectedChunk || !chunksData) return null;
    const currentIndex = chunksData.chunks.findIndex(
      c => c.id === selectedChunk.id
    );
    return currentIndex > 0 ? chunksData.chunks[currentIndex - 1] : null;
  };

  const getNextChunk = (): DocumentChunkResponse | null => {
    if (!selectedChunk || !chunksData) return null;
    const currentIndex = chunksData.chunks.findIndex(
      c => c.id === selectedChunk.id
    );
    return currentIndex < chunksData.chunks.length - 1
      ? chunksData.chunks[currentIndex + 1]
      : null;
  };

  useEffect(() => {
    if (selectedChunk) {
      scrollToChunkInSidebar(selectedChunk.id);
    }
  }, [selectedChunk, scrollToChunkInSidebar]);

  if (authLoading) {
    return (
      <div className="loading">
        <span className="spinner" />
        <span style={{ marginLeft: 'var(--space-3)' }}>Loading...</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        <div className="page-breadcrumb">
          <Link href={`/documents/${documentId}`}>Document</Link>
          <span className="page-breadcrumb-separator">›</span>
          <span>Viewer</span>
        </div>
        <div className="page-header">
          <h1 className="page-title">Document Viewer</h1>
        </div>
        <div className="viewer-container">
          <div className="viewer-sidebar">
            <div className="viewer-sidebar-header">
              <span className="viewer-sidebar-title">Chunks</span>
            </div>
            <div style={{ padding: 'var(--space-4)' }}>
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="skeleton-row">
                  <div
                    className="skeleton skeleton-text"
                    style={{ width: '80%' }}
                  />
                </div>
              ))}
            </div>
          </div>
          <div className="viewer-main">
            <div className="workflow-empty">
              <span className="spinner spinner-lg" />
              <p
                className="workflow-empty-title"
                style={{ marginTop: 'var(--space-4)' }}
              >
                Loading document content...
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="page-breadcrumb">
          <Link href={`/documents/${documentId}`}>Document</Link>
          <span className="page-breadcrumb-separator">›</span>
          <span>Viewer</span>
        </div>
        <div className="page-header">
          <h1 className="page-title">Document Viewer</h1>
        </div>
        <div className="alert alert-error">{error}</div>
      </div>
    );
  }

  const prevChunk = getPrevChunk();
  const nextChunk = getNextChunk();
  const currentChunkIndex = selectedChunk
    ? (chunksData?.chunks.findIndex(c => c.id === selectedChunk.id) ?? -1)
    : -1;

  return (
    <motion.div {...fadeUp}>
      {/* Breadcrumb */}
      <div className="page-breadcrumb">
        <Link href="/documents">Documents</Link>
        <span className="page-breadcrumb-separator">›</span>
        <Link href={`/documents/${documentId}`}>Document</Link>
        <span className="page-breadcrumb-separator">›</span>
        <span>Viewer</span>
      </div>

      {/* Header */}
      <div className="page-header">
        <h1 className="page-title">Document Viewer</h1>
        <p className="page-subtitle">
          {textData && (
            <>
              {textData.text_length.toLocaleString()} characters
              {textData.page_count && ` · ${textData.page_count} pages`}
              {' · '}
              {chunksData?.chunk_count || 0} chunks
            </>
          )}
        </p>
      </div>

      {/* Viewer Layout */}
      <div className="viewer-container">
        {/* Sidebar - Chunk List */}
        <div className="viewer-sidebar">
          <div className="viewer-sidebar-header">
            <span className="viewer-sidebar-title">Chunks</span>
            <span className="badge badge-muted">{filteredChunks.length}</span>
          </div>

          {/* Search */}
          <div
            style={{
              padding: 'var(--space-3)',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <input
              type="text"
              className="form-input"
              placeholder="Search chunks..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{ fontSize: 'var(--text-sm)' }}
            />
          </div>

          {/* Chunk List */}
          <div className="viewer-chunk-list" ref={sidebarRef}>
            {filteredChunks.length === 0 ? (
              <div
                className="empty-state"
                style={{ padding: 'var(--space-6)' }}
              >
                <p className="empty-state-description">
                  {searchQuery
                    ? 'No chunks match your search'
                    : 'No chunks available'}
                </p>
              </div>
            ) : (
              filteredChunks.map(chunk => (
                <div
                  key={chunk.id}
                  ref={el => {
                    if (el) chunkRefs.current.set(chunk.id, el);
                  }}
                  className={`viewer-chunk-item ${selectedChunk?.id === chunk.id ? 'selected' : ''}`}
                  onClick={() => handleChunkSelect(chunk)}
                >
                  <div className="viewer-chunk-item-header">
                    <span className="viewer-chunk-number">
                      Chunk {chunk.chunk_index}
                    </span>
                    {chunk.page_start && (
                      <span className="text-xs text-muted">
                        p.{chunk.page_start}
                      </span>
                    )}
                  </div>
                  <div className="viewer-chunk-preview">
                    {chunk.text.slice(0, 120)}
                    {chunk.text.length > 120 ? '...' : ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="viewer-main">
          {selectedChunk ? (
            <>
              {/* Header */}
              <div className="viewer-main-header">
                <div className="flex items-center gap-3">
                  <h3
                    style={{
                      margin: 0,
                      fontSize: 'var(--text-base)',
                      fontWeight: 'var(--font-semibold)',
                    }}
                  >
                    Chunk {selectedChunk.chunk_index}
                  </h3>
                  <span className="text-sm text-muted">
                    {currentChunkIndex + 1} of {chunksData?.chunk_count || 0}
                  </span>
                </div>
                <div className="viewer-navigation">
                  <button
                    className="viewer-nav-btn"
                    onClick={goToPrevChunk}
                    disabled={!prevChunk}
                  >
                    ← Previous
                  </button>
                  <button
                    className="viewer-nav-btn"
                    onClick={goToNextChunk}
                    disabled={!nextChunk}
                  >
                    Next →
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="viewer-main-content">
                {/* Metadata */}
                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="badge badge-muted">
                    Chars {selectedChunk.char_start.toLocaleString()}–
                    {selectedChunk.char_end.toLocaleString()}
                  </span>
                  {selectedChunk.page_start && (
                    <span className="badge badge-muted">
                      Page {selectedChunk.page_start}
                      {selectedChunk.page_end &&
                      selectedChunk.page_end !== selectedChunk.page_start
                        ? `–${selectedChunk.page_end}`
                        : ''}
                    </span>
                  )}
                  <span className="badge badge-info">
                    {selectedChunk.text.length.toLocaleString()} characters
                  </span>
                </div>

                {/* Previous Context */}
                {prevChunk && (
                  <div className="viewer-context-chunk viewer-context-prev">
                    <div className="viewer-context-label">
                      Previous (Chunk {prevChunk.chunk_index})
                    </div>
                    <div className="viewer-context-text">
                      ...{prevChunk.text.slice(-250)}
                    </div>
                  </div>
                )}

                {/* Selected Chunk */}
                <div className="viewer-selected-chunk">
                  <div className="viewer-selected-label">Selected Chunk</div>
                  <div className="viewer-chunk-text">{selectedChunk.text}</div>
                </div>

                {/* Next Context */}
                {nextChunk && (
                  <div className="viewer-context-chunk viewer-context-next">
                    <div className="viewer-context-label">
                      Next (Chunk {nextChunk.chunk_index})
                    </div>
                    <div className="viewer-context-text">
                      {nextChunk.text.slice(0, 250)}...
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="workflow-empty">
              <div className="workflow-empty-icon">
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14,2 14,8 20,8" />
                </svg>
              </div>
              <p className="workflow-empty-title">Select a Chunk</p>
              <p className="workflow-empty-desc">
                Choose a chunk from the sidebar to view its content.
              </p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
