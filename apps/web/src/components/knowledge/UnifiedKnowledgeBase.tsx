'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import {
  apiClient,
  type ScrapingJobStatus,
  type ViewerInstrumentListItem,
  type WikiPageSummary,
} from '@/lib/apiClient';
import { describeCron } from '@/lib/cronUtils';
import { fadeUp } from '@/lib/motion';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ConfirmModal } from '@/components/ui/Modal';
import { Skeleton } from '@/components/ui/Skeleton';
import { ScrapingJobDetailModal } from '@/components/operator/scraping/ScrapingJobDetailModal';
import { ScrapingSourceModal } from '@/components/operator/scraping/ScrapingSourceModal';
import { CONNECTOR_DEFAULTS } from '@/components/operator/scraping/config';
import { useScrapingAdmin } from './useScrapingAdmin';
import styles from './UnifiedKnowledgeBase.module.css';

type SourceFilter = 'all' | 'corpus' | 'wiki';

interface UnifiedResult {
  id: string;
  sourceType: 'corpus' | 'wiki';
  title: string;
  jurisdiction: string | null;
  subtype: string | null;
  snippet: string | null;
  updatedAt: string | null;
  slug?: string;
  url?: string | null;
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  const diffSec = Math.round((Date.now() - then) / 1000);
  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  const abs = Math.abs(diffSec);
  if (abs < 60) return formatter.format(-diffSec, 'second');
  const diffMin = Math.round(diffSec / 60);
  if (Math.abs(diffMin) < 60) return formatter.format(-diffMin, 'minute');
  const diffHour = Math.round(diffMin / 60);
  if (Math.abs(diffHour) < 24) return formatter.format(-diffHour, 'hour');
  const diffDay = Math.round(diffHour / 24);
  return formatter.format(-diffDay, 'day');
}

function sourceHealth(
  source: { enabled: boolean; last_job_id: string | null },
  lastJobStatus?: ScrapingJobStatus
): { label: string; tone: 'healthy' | 'warning' | 'muted' } {
  if (!source.enabled) return { label: 'Disabled', tone: 'muted' };
  if (!source.last_job_id) return { label: 'Ready', tone: 'healthy' };
  if (lastJobStatus === 'failed')
    return { label: 'Needs review', tone: 'warning' };
  if (lastJobStatus === 'running' || lastJobStatus === 'pending')
    return { label: 'Running', tone: 'healthy' };
  return { label: 'Healthy', tone: 'healthy' };
}

function jobStatusLabel(status: ScrapingJobStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function getJobBadgeVariant(status: ScrapingJobStatus) {
  if (status === 'completed') return 'success';
  if (status === 'failed') return 'error';
  if (status === 'running') return 'info';
  return 'warning';
}

export default function UnifiedKnowledgeBase() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const isPlatformAdmin = user?.is_platform_admin === true;

  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all');
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [instruments, setInstruments] = useState<ViewerInstrumentListItem[]>(
    []
  );
  const [instrumentsLoading, setInstrumentsLoading] = useState(true);
  const [wikiPages, setWikiPages] = useState<WikiPageSummary[]>([]);
  const [wikiLoading, setWikiLoading] = useState(true);
  const [wikiTotal, setWikiTotal] = useState(0);
  const [instrumentsTotal, setInstrumentsTotal] = useState(0);

  const scraping = useScrapingAdmin(isPlatformAdmin);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(t);
  }, [searchQuery]);

  // Load KB content
  const loadContent = useCallback(async () => {
    const query = debouncedQuery.trim();
    setInstrumentsLoading(true);
    setWikiLoading(true);

    const [instResult, wikiResult] = await Promise.allSettled([
      apiClient.listGlobalLegalInstruments({
        limit: 50,
        ...(query ? {} : {}),
      }),
      apiClient.getWikiPages({
        ...(query ? { search: query } : {}),
        limit: 50,
      }),
    ]);

    if (instResult.status === 'fulfilled') {
      setInstruments(instResult.value.items);
      setInstrumentsTotal(instResult.value.total);
    }
    if (wikiResult.status === 'fulfilled') {
      setWikiPages(wikiResult.value.items);
      setWikiTotal(wikiResult.value.total);
    }

    setInstrumentsLoading(false);
    setWikiLoading(false);
  }, [debouncedQuery]);

  useEffect(() => {
    void loadContent();
  }, [loadContent]);

  // Unified results
  const results: UnifiedResult[] = useMemo(() => {
    const query = debouncedQuery.toLowerCase().trim();
    const items: UnifiedResult[] = [];

    if (sourceFilter !== 'wiki') {
      for (const inst of instruments) {
        if (
          query &&
          !inst.title.toLowerCase().includes(query) &&
          !(inst.title_ar ?? '').toLowerCase().includes(query) &&
          !inst.jurisdiction.toLowerCase().includes(query)
        )
          continue;
        items.push({
          id: `corpus-${inst.id}`,
          sourceType: 'corpus',
          title: inst.title,
          jurisdiction: inst.jurisdiction,
          subtype: inst.instrument_type,
          snippet: inst.title_ar,
          updatedAt: inst.published_at ?? inst.latest_version_date,
          url: inst.official_source_url,
        });
      }
    }

    if (sourceFilter !== 'corpus') {
      for (const page of wikiPages) {
        items.push({
          id: `wiki-${page.id}`,
          sourceType: 'wiki',
          title: page.title,
          jurisdiction: page.jurisdiction,
          subtype: page.category,
          snippet: page.summary,
          updatedAt: page.updated_at,
          slug: page.slug,
        });
      }
    }

    return items;
  }, [instruments, wikiPages, sourceFilter, debouncedQuery]);

  const isLoading = instrumentsLoading || wikiLoading;

  /* ── Guard: non-admin ────────────────────────────── */

  if (!isPlatformAdmin) {
    return (
      <motion.div className={`page-container ${styles.page}`} {...fadeUp}>
        <div className={styles.deniedState}>
          <h1>Knowledge Base</h1>
          <p>This view is reserved for platform administrators.</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div className={`page-container ${styles.page}`} {...fadeUp}>
      {/* ── Header ─────────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Knowledge Base</h1>
          {!scraping.statsLoading && scraping.stats ? (
            <div className={styles.statPills}>
              <span className={styles.pill}>
                {scraping.stats.total_instruments.toLocaleString()} instruments
              </span>
              <span className={styles.pill}>{wikiTotal} wiki articles</span>
              <span className={styles.pill}>
                {scraping.stats.active_sources}/{scraping.stats.total_sources}{' '}
                sources active
              </span>
              {scraping.stats.running_jobs > 0 ? (
                <span className={styles.pill}>
                  {scraping.stats.running_jobs} queued
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.toggleSidebar}
            onClick={() => setSidebarOpen(o => !o)}
          >
            {sidebarOpen ? 'Hide admin' : 'Show admin'}
          </button>
        </div>
      </header>

      {/* ── Search + filters ───────────────────────── */}
      <div className={styles.searchRow}>
        <div className={styles.searchInputWrap}>
          <span className={styles.searchIcon}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </span>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search instruments, articles, jurisdictions..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <div className={styles.filterChips}>
          {(['all', 'corpus', 'wiki'] as const).map(f => (
            <button
              key={f}
              type="button"
              className={`${styles.chip} ${sourceFilter === f ? styles.chipActive : ''}`}
              onClick={() => setSourceFilter(f)}
            >
              {f === 'all' ? 'All' : f === 'corpus' ? 'Legal Corpus' : 'Wiki'}
            </button>
          ))}
        </div>
      </div>

      {/* ── Content columns ────────────────────────── */}
      <div
        className={`${styles.columns} ${!sidebarOpen ? styles.columnsCollapsed : ''}`}
      >
        {/* ── Results panel ─────────────────────────── */}
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2>
              {debouncedQuery
                ? `Results for "${debouncedQuery}"`
                : 'All Knowledge'}
            </h2>
            <Badge variant="muted">
              {results.length}
              {results.length !== instrumentsTotal + wikiTotal
                ? ` of ${instrumentsTotal + wikiTotal}`
                : ''}
            </Badge>
          </div>

          {isLoading ? (
            <div className={styles.panelBody}>
              <div className={styles.skeletonStack}>
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} variant="text" width="100%" />
                ))}
              </div>
            </div>
          ) : results.length === 0 ? (
            <div className={styles.emptyState}>
              <svg
                width="48"
                height="48"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.4"
                aria-hidden
              >
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
              <h3>No results found</h3>
              <p>
                {debouncedQuery
                  ? `No instruments or articles match "${debouncedQuery}".`
                  : 'The knowledge base is empty. Add scraping sources to begin building the legal corpus.'}
              </p>
            </div>
          ) : (
            <div className={styles.resultsScroll}>
              {results.map(item => (
                <div
                  key={item.id}
                  className={styles.resultRow}
                  onClick={() => {
                    if (item.sourceType === 'wiki' && item.slug) {
                      router.push(`/wiki/${item.slug}`);
                    } else if (item.url) {
                      window.open(item.url, '_blank');
                    }
                  }}
                >
                  <span className={styles.resultIcon}>
                    {item.sourceType === 'corpus' ? (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                      </svg>
                    ) : (
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <path d="M8 13h8" />
                        <path d="M8 17h5" />
                      </svg>
                    )}
                  </span>
                  <div className={styles.resultContent}>
                    <p className={styles.resultTitle}>
                      {item.title}
                      <span
                        className={`${styles.sourceTag} ${item.sourceType === 'corpus' ? styles.tagCorpus : styles.tagWiki}`}
                      >
                        {item.sourceType === 'corpus' ? 'Corpus' : 'Wiki'}
                      </span>
                    </p>
                    <div className={styles.resultMeta}>
                      {item.jurisdiction ? (
                        <Badge variant="viewer" size="sm">
                          {item.jurisdiction}
                        </Badge>
                      ) : null}
                      {item.subtype ? (
                        <Badge variant="muted" size="sm">
                          {item.subtype}
                        </Badge>
                      ) : null}
                      {item.updatedAt ? (
                        <Badge variant="muted" size="sm">
                          {formatRelativeTime(item.updatedAt)}
                        </Badge>
                      ) : null}
                    </div>
                    {item.snippet ? (
                      <p className={styles.resultSnippet}>{item.snippet}</p>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ── Admin sidebar ────────────────────────── */}
        {sidebarOpen ? (
          <aside className={styles.panel}>
            <div className={styles.panelHeader}>
              <h2>Admin</h2>
              <div style={{ display: 'flex', gap: '6px' }}>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={async () => {
                    try {
                      const res = await apiClient.resetStuckScrapingJobs();
                      scraping.loadJobs();
                      scraping.loadStats();
                      alert(res.message);
                    } catch {
                      alert('Failed to reset stuck jobs');
                    }
                  }}
                >
                  Reset stuck
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => {
                    scraping.resetCreateForm();
                    scraping.setCreateOpen(true);
                  }}
                >
                  Add source
                </Button>
              </div>
            </div>
            <div className={styles.sidebarScroll}>
              {/* Stats */}
              <div className={styles.sidebarSection}>
                <h3>Overview</h3>
                {scraping.statsLoading ? (
                  <div className={styles.skeletonStack}>
                    <Skeleton variant="text" width="100%" />
                    <Skeleton variant="text" width="100%" />
                  </div>
                ) : scraping.stats ? (
                  <div className={styles.statGrid}>
                    <div className={styles.statCard}>
                      <span className={styles.statValue}>
                        {scraping.stats.total_instruments.toLocaleString()}
                      </span>
                      <span className={styles.statLabel}>Instruments</span>
                    </div>
                    <div className={styles.statCard}>
                      <span className={styles.statValue}>{wikiTotal}</span>
                      <span className={styles.statLabel}>Wiki pages</span>
                    </div>
                    <div className={styles.statCard}>
                      <span className={styles.statValue}>
                        {scraping.stats.items_harvested_24h.toLocaleString()}
                      </span>
                      <span className={styles.statLabel}>Harvested 24h</span>
                    </div>
                    <div className={styles.statCard}>
                      <span className={styles.statValue}>
                        {scraping.stats.active_sources}
                      </span>
                      <span className={styles.statLabel}>Active sources</span>
                    </div>
                  </div>
                ) : null}
              </div>

              {/* Scraping sources */}
              <div className={styles.sidebarSection}>
                <h3>Scraping Sources</h3>
                {scraping.sourcesLoading ? (
                  <div className={styles.skeletonStack}>
                    {Array.from({ length: 3 }).map((_, i) => (
                      <Skeleton key={i} variant="text" width="100%" />
                    ))}
                  </div>
                ) : scraping.sourcesError ? (
                  <div className={styles.inlineError}>
                    <span>{scraping.sourcesError}</span>
                  </div>
                ) : scraping.sources.length === 0 ? (
                  <div className={styles.emptySmall}>
                    <p>No sources configured yet.</p>
                  </div>
                ) : (
                  <div className={styles.sourceList}>
                    {scraping.sources.map(source => {
                      const lastJob = source.last_job_id
                        ? scraping.jobsById.get(source.last_job_id)
                        : undefined;
                      const health = sourceHealth(
                        source,
                        lastJob?.status as ScrapingJobStatus | undefined
                      );
                      const isBusy =
                        scraping.triggerBusyId === source.id ||
                        scraping.sourceBusyIds.includes(source.id);
                      const isRunning =
                        lastJob &&
                        (lastJob.status === 'pending' ||
                          lastJob.status === 'running');

                      return (
                        <div key={source.id} className={styles.sourceRow}>
                          <div className={styles.sourceInfo}>
                            <div className={styles.sourceName}>
                              {source.display_name}
                            </div>
                            <div className={styles.sourceJurisdiction}>
                              {source.jurisdiction}
                              {source.schedule_cron
                                ? ` · ${describeCron(source.schedule_cron)}`
                                : ''}
                            </div>
                          </div>
                          <span
                            className={`${styles.healthBadge} ${
                              health.tone === 'healthy'
                                ? styles.healthHealthy
                                : health.tone === 'warning'
                                  ? styles.healthWarning
                                  : styles.healthMuted
                            }`}
                          >
                            {isRunning ? (
                              <span className={styles.runningDot} aria-hidden />
                            ) : null}
                            {health.label}
                          </span>
                          <div className={styles.sourceActions}>
                            <Button
                              size="sm"
                              type="button"
                              loading={scraping.triggerBusyId === source.id}
                              disabled={isBusy || !source.enabled}
                              onClick={() => scraping.handleTrigger(source)}
                            >
                              Run
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              type="button"
                              disabled={isBusy}
                              onClick={() => scraping.openEditModal(source)}
                            >
                              Edit
                            </Button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {Object.keys(scraping.actionErrors).length > 0 ? (
                  <div style={{ marginTop: '0.5rem' }}>
                    {Object.entries(scraping.actionErrors).map(([id, msg]) => (
                      <div key={id} className={styles.inlineError}>
                        <span>
                          {scraping.sourceNameById.get(id) ?? 'Source'}: {msg}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>

              {/* Recent jobs */}
              <div className={styles.sidebarSection}>
                <h3>Recent Activity</h3>
                {scraping.jobsLoading ? (
                  <div className={styles.skeletonStack}>
                    {Array.from({ length: 3 }).map((_, i) => (
                      <Skeleton key={i} variant="text" width="100%" />
                    ))}
                  </div>
                ) : scraping.jobsError ? (
                  <div className={styles.inlineError}>
                    <span>{scraping.jobsError}</span>
                  </div>
                ) : scraping.recentJobs.length === 0 ? (
                  <div className={styles.emptySmall}>
                    <p>No runs yet.</p>
                  </div>
                ) : (
                  <div className={styles.jobList}>
                    {scraping.recentJobs.map(job => (
                      <div
                        key={job.id}
                        className={`${styles.jobRow} ${scraping.highlightJobId === job.id ? styles.jobHighlight : ''}`}
                        onClick={() => scraping.setJobDetailId(job.id)}
                      >
                        <span className={styles.jobName}>
                          {scraping.sourceNameById.get(job.source_id) ??
                            job.connector_name}
                        </span>
                        <Badge
                          variant={getJobBadgeVariant(
                            job.status as ScrapingJobStatus
                          )}
                          size="sm"
                        >
                          {jobStatusLabel(job.status as ScrapingJobStatus)}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Coverage */}
              {scraping.stats &&
              Object.keys(scraping.stats.instruments_by_jurisdiction).length >
                0 ? (
                <div className={styles.sidebarSection}>
                  <h3>Coverage</h3>
                  <div className={styles.jurisdictionList}>
                    {Object.entries(scraping.stats.instruments_by_jurisdiction)
                      .sort(([, a], [, b]) => b - a)
                      .map(([jur, count]) => {
                        const pct =
                          scraping.stats!.total_instruments > 0
                            ? (count / scraping.stats!.total_instruments) * 100
                            : 0;
                        return (
                          <div key={jur} className={styles.jurisdictionRow}>
                            <span className={styles.jurisdictionLabel}>
                              {jur}
                            </span>
                            <div className={styles.jurisdictionTrack}>
                              <div
                                className={styles.jurisdictionFill}
                                style={{
                                  width: `${Math.max(pct, 2)}%`,
                                }}
                              />
                            </div>
                            <span className={styles.jurisdictionValue}>
                              {count.toLocaleString()}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              ) : null}
            </div>
          </aside>
        ) : null}
      </div>

      {/* ── Modals ─────────────────────────────────── */}

      <ScrapingSourceModal
        mode="create"
        isOpen={scraping.createOpen}
        onClose={() => scraping.setCreateOpen(false)}
        onSubmit={scraping.handleCreateSubmit}
        submitting={scraping.createSubmitting}
        error={scraping.createError}
        connectorName={scraping.createForm.connectorName}
        onConnectorNameChange={value => {
          const defaults = CONNECTOR_DEFAULTS[value];
          scraping.setCreateForm(c => ({
            ...c,
            connectorName: value,
            displayName: defaults?.display_name ?? c.displayName,
            jurisdiction: defaults?.jurisdiction ?? c.jurisdiction,
            sourceUrl: defaults?.source_url ?? c.sourceUrl,
          }));
        }}
        displayName={scraping.createForm.displayName}
        onDisplayNameChange={v =>
          scraping.setCreateForm(c => ({ ...c, displayName: v }))
        }
        jurisdiction={scraping.createForm.jurisdiction}
        onJurisdictionChange={v =>
          scraping.setCreateForm(c => ({ ...c, jurisdiction: v }))
        }
        sourceUrl={scraping.createForm.sourceUrl}
        onSourceUrlChange={v =>
          scraping.setCreateForm(c => ({ ...c, sourceUrl: v }))
        }
        schedule={scraping.createForm.schedule}
        onScheduleChange={v =>
          scraping.setCreateForm(c => ({ ...c, schedule: v }))
        }
        customCron={scraping.createForm.customCron}
        onCustomCronChange={v =>
          scraping.setCreateForm(c => ({ ...c, customCron: v }))
        }
        harvestLimit={scraping.createForm.harvestLimit}
        onHarvestLimitChange={v =>
          scraping.setCreateForm(c => ({ ...c, harvestLimit: v }))
        }
        enabled={scraping.createForm.enabled}
        onEnabledChange={v =>
          scraping.setCreateForm(c => ({ ...c, enabled: v }))
        }
      />

      <ScrapingSourceModal
        mode="edit"
        isOpen={scraping.editOpen}
        onClose={() => {
          scraping.setEditOpen(false);
          scraping.setEditingSource(null);
        }}
        onSubmit={scraping.handleEditSubmit}
        submitting={scraping.editSubmitting}
        error={scraping.editError}
        source={scraping.editingSource}
        connectorName={scraping.editForm.connectorName}
        onConnectorNameChange={() => {}}
        displayName={scraping.editForm.displayName}
        onDisplayNameChange={v =>
          scraping.setEditForm(c => ({ ...c, displayName: v }))
        }
        jurisdiction={scraping.editForm.jurisdiction}
        sourceUrl={scraping.editForm.sourceUrl}
        schedule={scraping.editForm.schedule}
        onScheduleChange={v =>
          scraping.setEditForm(c => ({ ...c, schedule: v }))
        }
        customCron={scraping.editForm.customCron}
        onCustomCronChange={v =>
          scraping.setEditForm(c => ({ ...c, customCron: v }))
        }
        harvestLimit={scraping.editForm.harvestLimit}
        onHarvestLimitChange={v =>
          scraping.setEditForm(c => ({ ...c, harvestLimit: v }))
        }
        enabled={scraping.editForm.enabled}
        onEnabledChange={v => scraping.setEditForm(c => ({ ...c, enabled: v }))}
      />

      <ConfirmModal
        isOpen={!!scraping.confirmDeleteId}
        onClose={() => scraping.setConfirmDeleteId(null)}
        onConfirm={scraping.handleDelete}
        title="Delete source"
        message="Delete this source and all of its historical jobs? This cannot be undone."
        confirmText="Delete source"
        variant="danger"
        loading={scraping.deleteSubmitting}
      />

      <ScrapingJobDetailModal
        isOpen={!!scraping.jobDetailId}
        onClose={() => scraping.setJobDetailId(null)}
        jobDetail={scraping.jobDetail}
        loading={scraping.jobDetailLoading}
        error={scraping.jobDetailError}
        sourceLabel={
          (scraping.jobDetail?.source_id
            ? scraping.sourceNameById.get(scraping.jobDetail.source_id)
            : scraping.jobDetailId
              ? scraping.sourceNameById.get(
                  scraping.jobs.find(j => j.id === scraping.jobDetailId)
                    ?.source_id ?? ''
                )
              : null) ?? null
        }
      />
    </motion.div>
  );
}
