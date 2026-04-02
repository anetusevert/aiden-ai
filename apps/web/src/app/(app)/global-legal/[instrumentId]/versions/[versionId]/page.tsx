'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  ViewerVersionDetail,
  ViewerChunksResponse,
  LegalChunkPreview,
  LegalChunkDetail,
} from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';

interface ViewerParams {
  params: {
    instrumentId: string;
    versionId: string;
  };
}

export default function GlobalLegalViewerPage({ params }: ViewerParams) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const { instrumentId, versionId } = params;
  const chunkIdParam = searchParams.get('chunkId');
  const chunkIndexParam = searchParams.get('chunkIndex');

  // Data state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [versionData, setVersionData] = useState<ViewerVersionDetail | null>(
    null
  );
  const [chunksData, setChunksData] = useState<ViewerChunksResponse | null>(
    null
  );

  // UI state
  const [selectedChunk, setSelectedChunk] = useState<LegalChunkDetail | null>(
    null
  );
  const [prevChunk, setPrevChunk] = useState<LegalChunkPreview | null>(null);
  const [nextChunk, setNextChunk] = useState<LegalChunkPreview | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loadingChunk, setLoadingChunk] = useState(false);

  // Refs
  const sidebarRef = useRef<HTMLDivElement>(null);
  const chunkRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Load version and chunks data
  useEffect(() => {
    if (!instrumentId || !versionId || authLoading || !isAuthenticated) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [versionRes, chunksRes] = await Promise.all([
          apiClient.getGlobalLegalVersionDetail(instrumentId, versionId),
          apiClient.getGlobalLegalVersionChunks(instrumentId, versionId),
        ]);

        setVersionData(versionRes);
        setChunksData(chunksRes);

        // Select initial chunk
        if (chunksRes.chunks.length > 0) {
          let targetChunkId: string | null = null;

          if (chunkIdParam) {
            const found = chunksRes.chunks.find(c => c.id === chunkIdParam);
            if (found) targetChunkId = found.id;
          } else if (chunkIndexParam) {
            const idx = parseInt(chunkIndexParam, 10);
            const found = chunksRes.chunks.find(c => c.chunk_index === idx);
            if (found) targetChunkId = found.id;
          }

          if (!targetChunkId) {
            targetChunkId = chunksRes.chunks[0].id;
          }

          // Load the full chunk
          await loadChunk(targetChunkId, instrumentId, versionId);
        }
      } catch (err) {
        if (err instanceof Error) {
          if (err.message.includes('403')) {
            setError(
              'Access denied: This instrument is not available in your workspace policy.'
            );
          } else if (err.message.includes('404')) {
            setError('Legal instrument or version not found.');
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
    instrumentId,
    versionId,
    authLoading,
    isAuthenticated,
    chunkIdParam,
    chunkIndexParam,
  ]);

  const loadChunk = async (
    chunkId: string,
    instId: string,
    versnId: string
  ) => {
    setLoadingChunk(true);
    try {
      const response = await apiClient.getGlobalLegalChunk(
        instId,
        versnId,
        chunkId
      );
      setSelectedChunk(response.chunk);
      setPrevChunk(response.prev_chunk);
      setNextChunk(response.next_chunk);

      // Update URL
      const url = new URL(window.location.href);
      url.searchParams.set('chunkId', chunkId);
      url.searchParams.delete('chunkIndex');
      window.history.replaceState({}, '', url.toString());
    } catch (err) {
      console.error('Failed to load chunk:', err);
    } finally {
      setLoadingChunk(false);
    }
  };

  const scrollToChunkInSidebar = useCallback((chunkId: string) => {
    const element = chunkRefs.current.get(chunkId);
    if (element && sidebarRef.current) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

  const handleChunkSelect = useCallback(
    async (chunk: LegalChunkPreview) => {
      await loadChunk(chunk.id, instrumentId, versionId);
      scrollToChunkInSidebar(chunk.id);
    },
    [instrumentId, versionId, scrollToChunkInSidebar]
  );

  const goToPrevChunk = useCallback(async () => {
    if (!prevChunk) return;
    await loadChunk(prevChunk.id, instrumentId, versionId);
    scrollToChunkInSidebar(prevChunk.id);
  }, [prevChunk, instrumentId, versionId, scrollToChunkInSidebar]);

  const goToNextChunk = useCallback(async () => {
    if (!nextChunk) return;
    await loadChunk(nextChunk.id, instrumentId, versionId);
    scrollToChunkInSidebar(nextChunk.id);
  }, [nextChunk, instrumentId, versionId, scrollToChunkInSidebar]);

  const filteredChunks =
    chunksData?.chunks.filter(chunk => {
      if (!searchQuery.trim()) return true;
      const lowerQuery = searchQuery.toLowerCase();
      return chunk.preview.toLowerCase().includes(lowerQuery);
    }) || [];

  useEffect(() => {
    if (selectedChunk) {
      scrollToChunkInSidebar(selectedChunk.id);
    }
  }, [selectedChunk, scrollToChunkInSidebar]);

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

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
          <Link href="/global-legal">Global Legal Library</Link>
          <span className="page-breadcrumb-separator">›</span>
          <span>Loading...</span>
        </div>
        <div className="page-header">
          <div className="flex items-center gap-3">
            <h1 className="page-title">Global Legal Viewer</h1>
            <span className="badge badge-info">Read-Only</span>
          </div>
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
          <Link href="/global-legal">Global Legal Library</Link>
          <span className="page-breadcrumb-separator">›</span>
          <span>Error</span>
        </div>
        <div className="page-header">
          <h1 className="page-title">Global Legal Viewer</h1>
        </div>
        <div className="alert alert-error">{error}</div>
        <div style={{ marginTop: 'var(--space-4)' }}>
          <Link href="/global-legal" className="btn btn-secondary">
            ← Back to Global Legal Library
          </Link>
        </div>
      </div>
    );
  }

  const currentChunkIndex =
    selectedChunk && chunksData
      ? chunksData.chunks.findIndex(c => c.id === selectedChunk.id)
      : -1;

  return (
    <motion.div {...fadeUp}>
      {/* Breadcrumb */}
      <div className="page-breadcrumb">
        <Link href="/global-legal">Global Legal Library</Link>
        <span className="page-breadcrumb-separator">›</span>
        <Link href={`/global-legal/${instrumentId}`}>
          {versionData?.instrument_title || 'Instrument'}
        </Link>
        <span className="page-breadcrumb-separator">›</span>
        <span>{versionData?.version_label || 'Viewer'}</span>
      </div>

      {/* Header */}
      <div className="page-header">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="page-title">{versionData?.instrument_title}</h1>
          <span className="badge badge-info">Global Law (Read-Only)</span>
          <span className="badge badge-muted">{versionData?.jurisdiction}</span>
        </div>
        <p className="page-subtitle">
          {versionData?.version_label}
          {' · '}
          {chunksData?.chunk_count || 0} chunks
          {versionData?.published_at &&
            ` · Published ${formatDate(versionData.published_at)}`}
        </p>
      </div>

      {/* Action Bar */}
      <div
        className="flex items-center gap-3 flex-wrap"
        style={{ marginBottom: 'var(--space-4)' }}
      >
        {versionData?.official_source_url && (
          <a
            href={versionData.official_source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            View Official Source ↗
          </a>
        )}
        <div
          className="alert alert-info"
          style={{
            margin: 0,
            padding: 'var(--space-2) var(--space-4)',
            fontSize: 'var(--text-sm)',
          }}
        >
          This is a global legal reference. Read-only.
        </div>
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
                  <div className="viewer-chunk-preview">{chunk.preview}</div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="viewer-main">
          {loadingChunk ? (
            <div className="workflow-empty">
              <span className="spinner spinner-lg" />
              <p
                className="workflow-empty-title"
                style={{ marginTop: 'var(--space-4)' }}
              >
                Loading chunk...
              </p>
            </div>
          ) : selectedChunk ? (
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
                    disabled={!prevChunk || loadingChunk}
                  >
                    ← Previous
                  </button>
                  <button
                    className="viewer-nav-btn"
                    onClick={goToNextChunk}
                    disabled={!nextChunk || loadingChunk}
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
                      ...{prevChunk.preview}
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
                      {nextChunk.preview}
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
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
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
