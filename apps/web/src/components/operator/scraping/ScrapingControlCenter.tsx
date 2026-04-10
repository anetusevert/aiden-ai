'use client';

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import {
  apiClient,
  ApiClientError,
  ScrapingJobDetailResponse,
  ScrapingJobResponse,
  ScrapingJobStatus,
  ScrapingSourceCreate,
  ScrapingSourceResponse,
  ScrapingSourceUpdate,
  ScrapingStatsResponse,
} from '@/lib/apiClient';
import { describeCron, formatDuration } from '@/lib/cronUtils';
import { fadeUp } from '@/lib/motion';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ConfirmModal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Skeleton } from '@/components/ui/Skeleton';
import { ScrapingJobDetailModal } from './ScrapingJobDetailModal';
import { ScrapingSourceModal } from './ScrapingSourceModal';
import {
  CONNECTOR_DEFAULTS,
  initialScheduleSelect,
  schedulePayloadFromForm,
} from './config';
import styles from './ScrapingControlCenter.module.css';

type SourceFormState = {
  connectorName: string;
  displayName: string;
  jurisdiction: string;
  sourceUrl: string;
  schedule: string;
  customCron: string;
  harvestLimit: number;
  enabled: boolean;
};

const DEFAULT_SOURCE_FORM: SourceFormState = {
  connectorName: 'ksa_boe',
  displayName: CONNECTOR_DEFAULTS.ksa_boe.display_name,
  jurisdiction: CONNECTOR_DEFAULTS.ksa_boe.jurisdiction,
  sourceUrl: CONNECTOR_DEFAULTS.ksa_boe.source_url,
  schedule: '',
  customCron: '',
  harvestLimit: 500,
  enabled: true,
};

function formatRelativeTime(iso: string | null): string {
  if (!iso) return 'Never';
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

function formatTimestamp(iso: string | null): string {
  if (!iso) return 'Never';
  return new Date(iso).toLocaleString();
}

function jobDurationSeconds(job: {
  started_at: string | null;
  finished_at: string | null;
}): number | null {
  if (!job.started_at || !job.finished_at) return null;
  const started = new Date(job.started_at).getTime();
  const finished = new Date(job.finished_at).getTime();
  const seconds = (finished - started) / 1000;
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : null;
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

function sourceHealth(
  source: ScrapingSourceResponse,
  lastJob?: ScrapingJobResponse
): { label: string; tone: 'healthy' | 'warning' | 'muted' } {
  if (!source.enabled) return { label: 'Disabled', tone: 'muted' };
  if (!lastJob) return { label: 'Ready', tone: 'healthy' };
  if (lastJob.status === 'failed')
    return { label: 'Needs review', tone: 'warning' };
  if (lastJob.status === 'running' || lastJob.status === 'pending')
    return { label: 'Running', tone: 'healthy' };
  return { label: 'Healthy', tone: 'healthy' };
}

function EmptyDocumentIcon() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      aria-hidden
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <path d="M8 13h8" />
      <path d="M8 17h5" />
    </svg>
  );
}

export default function ScrapingControlCenter() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const isPlatformAdmin = user?.is_platform_admin === true;

  const [stats, setStats] = useState<ScrapingStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [sources, setSources] = useState<ScrapingSourceResponse[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<ScrapingJobResponse[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const [selectedSourceId, setSelectedSourceId] = useState<string>('all');

  const [createOpen, setCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createForm, setCreateForm] =
    useState<SourceFormState>(DEFAULT_SOURCE_FORM);

  const [editOpen, setEditOpen] = useState(false);
  const [editingSource, setEditingSource] =
    useState<ScrapingSourceResponse | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editForm, setEditForm] =
    useState<SourceFormState>(DEFAULT_SOURCE_FORM);

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  const [triggerBusyId, setTriggerBusyId] = useState<string | null>(null);
  const [sourceBusyIds, setSourceBusyIds] = useState<string[]>([]);
  const [actionErrors, setActionErrors] = useState<Record<string, string>>({});

  const [jobDetailId, setJobDetailId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<ScrapingJobDetailResponse | null>(
    null
  );
  const [jobDetailLoading, setJobDetailLoading] = useState(false);
  const [jobDetailError, setJobDetailError] = useState<string | null>(null);

  const [highlightJobId, setHighlightJobId] = useState<string | null>(null);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  /* ── Derived values ──────────────────────────────────── */

  const sourceNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const source of sources) map.set(source.id, source.display_name);
    return map;
  }, [sources]);

  const jobsById = useMemo(() => {
    const map = new Map<string, ScrapingJobResponse>();
    for (const job of jobs) map.set(job.id, job);
    return map;
  }, [jobs]);

  const selectedSource =
    selectedSourceId === 'all'
      ? null
      : (sources.find(source => source.id === selectedSourceId) ?? null);

  const filteredJobs = useMemo(() => {
    if (selectedSourceId === 'all') return jobs;
    return jobs.filter(job => job.source_id === selectedSourceId);
  }, [jobs, selectedSourceId]);

  const activeJobs = useMemo(
    () =>
      filteredJobs.filter(
        job => job.status === 'pending' || job.status === 'running'
      ),
    [filteredJobs]
  );

  const hasActiveJobs = useMemo(
    () =>
      jobs.some(job => job.status === 'pending' || job.status === 'running'),
    [jobs]
  );

  const sourceOptions = useMemo(
    () => [
      { value: 'all', label: 'All sources' },
      ...sources.map(source => ({
        value: source.id,
        label: source.display_name,
      })),
    ],
    [sources]
  );

  /* ── Effects ─────────────────────────────────────────── */

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const loadStats = useCallback(async () => {
    if (!isPlatformAdmin) return;
    try {
      const response = await apiClient.getScrapingStats();
      setStats(response);
    } finally {
      setStatsLoading(false);
    }
  }, [isPlatformAdmin]);

  const loadSources = useCallback(async () => {
    if (!isPlatformAdmin) return;
    setSourcesError(null);
    try {
      const response = await apiClient.getScrapingSources();
      setSources(response);
      setSelectedSourceId(current =>
        current === 'all' || response.some(source => source.id === current)
          ? current
          : 'all'
      );
    } catch (error) {
      setSourcesError(
        error instanceof Error
          ? error.message
          : 'Failed to load scraping sources'
      );
    } finally {
      setSourcesLoading(false);
    }
  }, [isPlatformAdmin]);

  const loadJobs = useCallback(async () => {
    if (!isPlatformAdmin) return;
    setJobsError(null);
    try {
      const response = await apiClient.getScrapingJobs({ limit: 50 });
      setJobs(response);
    } catch (error) {
      setJobsError(
        error instanceof Error ? error.message : 'Failed to load scraping jobs'
      );
    } finally {
      setJobsLoading(false);
    }
  }, [isPlatformAdmin]);

  useEffect(() => {
    if (!isPlatformAdmin) return;
    setStatsLoading(true);
    setSourcesLoading(true);
    setJobsLoading(true);
    void Promise.all([loadStats(), loadSources(), loadJobs()]);
  }, [isPlatformAdmin, loadJobs, loadSources, loadStats]);

  useEffect(() => {
    if (!isPlatformAdmin || !hasActiveJobs) return;
    const intervalId = window.setInterval(() => {
      void loadJobs();
      void loadSources();
      void loadStats();
    }, 5000);
    return () => clearInterval(intervalId);
  }, [hasActiveJobs, isPlatformAdmin, loadJobs, loadSources, loadStats]);

  useEffect(() => {
    if (!jobDetailId) {
      setJobDetail(null);
      setJobDetailError(null);
      return;
    }
    let cancelled = false;
    setJobDetailLoading(true);
    setJobDetailError(null);
    void apiClient
      .getScrapingJob(jobDetailId)
      .then(response => {
        if (!cancelled) setJobDetail(response);
      })
      .catch(error => {
        if (!cancelled)
          setJobDetailError(
            error instanceof Error ? error.message : 'Failed to load run'
          );
      })
      .finally(() => {
        if (!cancelled) setJobDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jobDetailId]);

  const activeJobDetailStatus =
    jobDetail?.status ?? jobs.find(job => job.id === jobDetailId)?.status;

  useEffect(() => {
    if (
      !jobDetailId ||
      (activeJobDetailStatus !== 'pending' &&
        activeJobDetailStatus !== 'running')
    ) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void apiClient
        .getScrapingJob(jobDetailId)
        .then(setJobDetail)
        .catch(error => {
          setJobDetailError(
            error instanceof Error ? error.message : 'Failed to load run'
          );
        });
    }, 2000);
    return () => clearInterval(intervalId);
  }, [activeJobDetailStatus, jobDetailId]);

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!openMenuId) return;
    const handler = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest('[data-source-menu]')) {
        setOpenMenuId(null);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [openMenuId]);

  /* ── Handlers ────────────────────────────────────────── */

  const setActionError = useCallback((sourceId: string, message: string) => {
    setActionErrors(current => ({ ...current, [sourceId]: message }));
  }, []);

  const clearActionError = useCallback((sourceId: string) => {
    setActionErrors(current => {
      const next = { ...current };
      delete next[sourceId];
      return next;
    });
  }, []);

  const markSourceBusy = useCallback((sourceId: string, busy: boolean) => {
    setSourceBusyIds(current =>
      busy
        ? Array.from(new Set([...current, sourceId]))
        : current.filter(id => id !== sourceId)
    );
  }, []);

  const resetCreateForm = useCallback(() => {
    setCreateForm(DEFAULT_SOURCE_FORM);
    setCreateError(null);
  }, []);

  const openEditModal = useCallback((source: ScrapingSourceResponse) => {
    const schedule = initialScheduleSelect(source.schedule_cron);
    setEditingSource(source);
    setEditForm({
      connectorName: source.connector_name,
      displayName: source.display_name,
      jurisdiction: source.jurisdiction,
      sourceUrl: source.source_url ?? '',
      schedule: schedule.value,
      customCron: schedule.custom,
      harvestLimit: source.harvest_limit,
      enabled: source.enabled,
    });
    setEditError(null);
    setEditOpen(true);
  }, []);

  const handleCreateSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    const payload: ScrapingSourceCreate = {
      connector_name: createForm.connectorName,
      display_name: createForm.displayName.trim(),
      jurisdiction: createForm.jurisdiction.trim(),
      enabled: createForm.enabled,
      harvest_limit: createForm.harvestLimit,
      schedule_cron: schedulePayloadFromForm(
        createForm.schedule,
        createForm.customCron
      ),
    };
    const sourceUrl = createForm.sourceUrl.trim();
    if (sourceUrl) payload.source_url = sourceUrl;

    try {
      await apiClient.createScrapingSource(payload);
      setCreateOpen(false);
      resetCreateForm();
      await Promise.all([loadSources(), loadStats()]);
    } catch (error) {
      setCreateError(
        error instanceof ApiClientError
          ? error.message
          : error instanceof Error
            ? error.message
            : 'Failed to create source'
      );
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleEditSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!editingSource) return;
    setEditSubmitting(true);
    setEditError(null);
    const payload: ScrapingSourceUpdate = {
      display_name: editForm.displayName.trim(),
      enabled: editForm.enabled,
      harvest_limit: editForm.harvestLimit,
      schedule_cron: schedulePayloadFromForm(
        editForm.schedule,
        editForm.customCron
      ),
    };

    try {
      await apiClient.updateScrapingSource(editingSource.id, payload);
      setEditOpen(false);
      setEditingSource(null);
      await Promise.all([loadSources(), loadStats()]);
    } catch (error) {
      setEditError(
        error instanceof ApiClientError
          ? error.message
          : error instanceof Error
            ? error.message
            : 'Failed to update source'
      );
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleToggleEnabled = async (source: ScrapingSourceResponse) => {
    clearActionError(source.id);
    markSourceBusy(source.id, true);
    try {
      await apiClient.updateScrapingSource(source.id, {
        enabled: !source.enabled,
      });
      await Promise.all([loadSources(), loadStats()]);
    } catch (error) {
      setActionError(
        source.id,
        error instanceof Error ? error.message : 'Failed to update source'
      );
    } finally {
      markSourceBusy(source.id, false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDeleteId) return;
    setDeleteSubmitting(true);
    try {
      await apiClient.deleteScrapingSource(confirmDeleteId);
      if (selectedSourceId === confirmDeleteId) setSelectedSourceId('all');
      setConfirmDeleteId(null);
      await Promise.all([loadSources(), loadJobs(), loadStats()]);
    } catch (error) {
      setSourcesError(
        error instanceof Error ? error.message : 'Failed to delete source'
      );
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const handleTrigger = async (source: ScrapingSourceResponse) => {
    clearActionError(source.id);
    setTriggerBusyId(source.id);
    try {
      const response = await apiClient.triggerScrapingSource(source.id);
      setSelectedSourceId(source.id);
      setJobDetail(null);
      setJobDetailError(null);
      setJobDetailId(response.job_id);
      setHighlightJobId(response.job_id);
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = setTimeout(() => {
        setHighlightJobId(null);
        highlightTimerRef.current = null;
      }, 2000);
      await Promise.all([loadSources(), loadJobs(), loadStats()]);
    } catch (error) {
      setActionError(
        source.id,
        error instanceof ApiClientError
          ? error.message
          : error instanceof Error
            ? error.message
            : 'Failed to trigger source'
      );
    } finally {
      setTriggerBusyId(null);
    }
  };

  /* ── Guard: non-admin ────────────────────────────────── */

  if (!isPlatformAdmin) {
    return (
      <motion.div className={`page-container ${styles.page}`} {...fadeUp}>
        <div className={styles.deniedState}>
          <h1>Scraping Control Center</h1>
          <p>This operator view is reserved for platform administrators.</p>
        </div>
      </motion.div>
    );
  }

  /* ── Render ──────────────────────────────────────────── */

  return (
    <motion.div className={`page-container ${styles.page}`} {...fadeUp}>
      {/* ── Header strip ──────────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>Scraping Control Center</h1>
          {!statsLoading && stats ? (
            <div className={styles.statPills}>
              <span className={styles.pill}>
                {stats.total_instruments.toLocaleString()} records
              </span>
              <span className={styles.pill}>
                {stats.active_sources}/{stats.total_sources} active
              </span>
              <span className={styles.pill}>{stats.running_jobs} queued</span>
              <span className={`${styles.pill} ${styles.pillMuted}`}>
                {stats.items_harvested_24h.toLocaleString()} in 24h
              </span>
            </div>
          ) : null}
        </div>
        <Button
          type="button"
          size="sm"
          onClick={() => {
            resetCreateForm();
            setCreateOpen(true);
          }}
        >
          Add source
        </Button>
      </header>

      {/* ── Two-column content ────────────────────────── */}
      <div className={styles.columns}>
        {/* ── Sources panel (left) ────────────────────── */}
        <section className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2>Sources</h2>
            <Badge variant="muted">{sources.length} configured</Badge>
          </div>

          {sourcesError ? (
            <div className={styles.panelBody}>
              <div className={styles.inlineError}>
                <span>{sourcesError}</span>
                <Button
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={() => {
                    setSourcesLoading(true);
                    void loadSources();
                  }}
                >
                  Retry
                </Button>
              </div>
            </div>
          ) : null}

          {sourcesLoading ? (
            <div className={styles.panelBody}>
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} variant="text" width="100%" />
              ))}
            </div>
          ) : sources.length === 0 ? (
            <div className={styles.emptyState}>
              <EmptyDocumentIcon />
              <h3>No sources configured</h3>
              <p>
                Add an official source to start building the legal corpus
                pipeline.
              </p>
              <Button
                type="button"
                onClick={() => {
                  resetCreateForm();
                  setCreateOpen(true);
                }}
              >
                Add first source
              </Button>
            </div>
          ) : (
            <div className={styles.sourceTableWrap}>
              <table className={styles.sourceTable}>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Jurisdiction</th>
                    <th className={styles.hideNarrow}>Schedule</th>
                    <th>Status</th>
                    <th className={styles.hideNarrow}>Last run</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {sources.map(source => {
                    const lastJob = source.last_job_id
                      ? jobsById.get(source.last_job_id)
                      : undefined;
                    const health = sourceHealth(source, lastJob);
                    const isBusy =
                      triggerBusyId === source.id ||
                      sourceBusyIds.includes(source.id);
                    const scheduleLabel = source.schedule_cron
                      ? describeCron(source.schedule_cron)
                      : 'Manual only';
                    const isRunning =
                      lastJob &&
                      (lastJob.status === 'pending' ||
                        lastJob.status === 'running');

                    return (
                      <tr
                        key={source.id}
                        className={
                          selectedSourceId === source.id
                            ? styles.focusedRow
                            : ''
                        }
                      >
                        <td>
                          <div className={styles.sourceNameCell}>
                            <strong>{source.display_name}</strong>
                            {source.source_url ? (
                              <a
                                href={source.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className={styles.externalLink}
                                title="Open source"
                              >
                                ↗
                              </a>
                            ) : null}
                          </div>
                        </td>
                        <td>
                          <Badge variant="viewer" size="sm">
                            {source.jurisdiction}
                          </Badge>
                        </td>
                        <td className={styles.hideNarrow}>{scheduleLabel}</td>
                        <td>
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
                        </td>
                        <td className={styles.hideNarrow}>
                          {formatRelativeTime(source.last_run_at)}
                        </td>
                        <td>
                          <div className={styles.actionCell}>
                            <Button
                              size="sm"
                              type="button"
                              loading={triggerBusyId === source.id}
                              disabled={isBusy || !source.enabled}
                              onClick={() => handleTrigger(source)}
                            >
                              Run
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              type="button"
                              disabled={isBusy}
                              onClick={() => openEditModal(source)}
                            >
                              Edit
                            </Button>
                            <div className={styles.moreWrap} data-source-menu>
                              <button
                                type="button"
                                className={styles.moreBtn}
                                onClick={() =>
                                  setOpenMenuId(
                                    openMenuId === source.id ? null : source.id
                                  )
                                }
                              >
                                ···
                              </button>
                              {openMenuId === source.id ? (
                                <div className={styles.moreMenu}>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setSelectedSourceId(source.id);
                                      setOpenMenuId(null);
                                    }}
                                  >
                                    Focus runs
                                  </button>
                                  <button
                                    type="button"
                                    disabled={isBusy}
                                    onClick={() => {
                                      void handleToggleEnabled(source);
                                      setOpenMenuId(null);
                                    }}
                                  >
                                    {source.enabled ? 'Disable' : 'Enable'}
                                  </button>
                                  <button
                                    type="button"
                                    className={styles.dangerItem}
                                    disabled={isBusy}
                                    onClick={() => {
                                      setConfirmDeleteId(source.id);
                                      setOpenMenuId(null);
                                    }}
                                  >
                                    Delete
                                  </button>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {Object.keys(actionErrors).length > 0 ? (
            <div className={styles.panelBody}>
              {Object.entries(actionErrors).map(([id, msg]) => (
                <div key={id} className={styles.inlineError}>
                  <span>
                    {sourceNameById.get(id) ?? 'Source'}: {msg}
                  </span>
                </div>
              ))}
            </div>
          ) : null}
        </section>

        {/* ── Activity panel (right) ──────────────────── */}
        <aside className={styles.panel}>
          <div className={styles.panelHeader}>
            <h2>Activity</h2>
            {selectedSource ? (
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() => setSelectedSourceId('all')}
              >
                Clear filter
              </Button>
            ) : null}
          </div>
          <div className={styles.activityScroll}>
            <Select
              label="Focus source"
              options={sourceOptions}
              value={selectedSourceId}
              onChange={e => setSelectedSourceId(e.target.value)}
            />

            {activeJobs.length > 0 ? (
              <div className={styles.activeSection}>
                <div className={styles.activeSectionHeader}>
                  <span className={styles.livePulse} aria-hidden />
                  <h3>
                    {activeJobs.length} active{' '}
                    {activeJobs.length === 1 ? 'run' : 'runs'}
                  </h3>
                </div>
                <div className={styles.activeList}>
                  {activeJobs.map(job => (
                    <button
                      key={job.id}
                      type="button"
                      className={styles.activeCard}
                      onClick={() => setJobDetailId(job.id)}
                    >
                      <div>
                        <strong>
                          {sourceNameById.get(job.source_id) ??
                            job.connector_name}
                        </strong>
                        <span>{formatTimestamp(job.created_at)}</span>
                      </div>
                      <Badge variant={getJobBadgeVariant(job.status)} size="sm">
                        {jobStatusLabel(job.status)}
                      </Badge>
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            {jobsError ? (
              <div className={styles.inlineError}>
                <span>{jobsError}</span>
                <Button
                  variant="outline"
                  size="sm"
                  type="button"
                  onClick={() => {
                    setJobsLoading(true);
                    void loadJobs();
                  }}
                >
                  Retry
                </Button>
              </div>
            ) : null}

            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Run history</h3>
              {jobsLoading ? (
                <div className={styles.skeletonStack}>
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Skeleton key={i} variant="text" width="100%" />
                  ))}
                </div>
              ) : filteredJobs.length === 0 ? (
                <div className={styles.emptySmall}>
                  <p>No runs yet.</p>
                </div>
              ) : (
                <div className={styles.runTableWrap}>
                  <table className={styles.runTable}>
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Status</th>
                        <th>Started</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {filteredJobs.map(job => {
                        const duration = jobDurationSeconds(job);
                        return (
                          <tr
                            key={job.id}
                            className={
                              highlightJobId === job.id
                                ? styles.highlightRow
                                : ''
                            }
                          >
                            <td>
                              {sourceNameById.get(job.source_id) ??
                                job.connector_name}
                            </td>
                            <td>
                              <Badge
                                variant={getJobBadgeVariant(job.status)}
                                size="sm"
                              >
                                {jobStatusLabel(job.status)}
                              </Badge>
                            </td>
                            <td className={styles.timeCell}>
                              {job.started_at
                                ? formatTimestamp(job.started_at)
                                : '-'}
                              {duration != null ? (
                                <> ({formatDuration(duration)})</>
                              ) : null}
                            </td>
                            <td>
                              <Button
                                variant="outline"
                                size="sm"
                                type="button"
                                onClick={() => setJobDetailId(job.id)}
                              >
                                Inspect
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className={styles.section}>
              <h3 className={styles.sectionTitle}>Coverage</h3>
              {statsLoading ? (
                <Skeleton variant="text" width="100%" />
              ) : stats &&
                Object.keys(stats.instruments_by_jurisdiction).length > 0 ? (
                <div className={styles.jurisdictionList}>
                  {Object.entries(stats.instruments_by_jurisdiction)
                    .sort(([, a], [, b]) => b - a)
                    .map(([jurisdiction, count]) => {
                      const pct =
                        stats.total_instruments > 0
                          ? (count / stats.total_instruments) * 100
                          : 0;
                      return (
                        <div
                          key={jurisdiction}
                          className={styles.jurisdictionRow}
                        >
                          <span className={styles.jurisdictionLabel}>
                            {jurisdiction}
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
              ) : (
                <div className={styles.emptySmall}>
                  <p>No data yet.</p>
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>

      {/* ── Modals (unchanged) ────────────────────────── */}

      <ScrapingSourceModal
        mode="create"
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        onSubmit={handleCreateSubmit}
        submitting={createSubmitting}
        error={createError}
        connectorName={createForm.connectorName}
        onConnectorNameChange={value => {
          const defaults = CONNECTOR_DEFAULTS[value];
          setCreateForm(current => ({
            ...current,
            connectorName: value,
            displayName: defaults?.display_name ?? current.displayName,
            jurisdiction: defaults?.jurisdiction ?? current.jurisdiction,
            sourceUrl: defaults?.source_url ?? current.sourceUrl,
          }));
        }}
        displayName={createForm.displayName}
        onDisplayNameChange={value =>
          setCreateForm(current => ({ ...current, displayName: value }))
        }
        jurisdiction={createForm.jurisdiction}
        onJurisdictionChange={value =>
          setCreateForm(current => ({ ...current, jurisdiction: value }))
        }
        sourceUrl={createForm.sourceUrl}
        onSourceUrlChange={value =>
          setCreateForm(current => ({ ...current, sourceUrl: value }))
        }
        schedule={createForm.schedule}
        onScheduleChange={value =>
          setCreateForm(current => ({ ...current, schedule: value }))
        }
        customCron={createForm.customCron}
        onCustomCronChange={value =>
          setCreateForm(current => ({ ...current, customCron: value }))
        }
        harvestLimit={createForm.harvestLimit}
        onHarvestLimitChange={value =>
          setCreateForm(current => ({ ...current, harvestLimit: value }))
        }
        enabled={createForm.enabled}
        onEnabledChange={value =>
          setCreateForm(current => ({ ...current, enabled: value }))
        }
      />

      <ScrapingSourceModal
        mode="edit"
        isOpen={editOpen}
        onClose={() => {
          setEditOpen(false);
          setEditingSource(null);
        }}
        onSubmit={handleEditSubmit}
        submitting={editSubmitting}
        error={editError}
        source={editingSource}
        connectorName={editForm.connectorName}
        onConnectorNameChange={() => {}}
        displayName={editForm.displayName}
        onDisplayNameChange={value =>
          setEditForm(current => ({ ...current, displayName: value }))
        }
        jurisdiction={editForm.jurisdiction}
        sourceUrl={editForm.sourceUrl}
        schedule={editForm.schedule}
        onScheduleChange={value =>
          setEditForm(current => ({ ...current, schedule: value }))
        }
        customCron={editForm.customCron}
        onCustomCronChange={value =>
          setEditForm(current => ({ ...current, customCron: value }))
        }
        harvestLimit={editForm.harvestLimit}
        onHarvestLimitChange={value =>
          setEditForm(current => ({ ...current, harvestLimit: value }))
        }
        enabled={editForm.enabled}
        onEnabledChange={value =>
          setEditForm(current => ({ ...current, enabled: value }))
        }
      />

      <ConfirmModal
        isOpen={!!confirmDeleteId}
        onClose={() => setConfirmDeleteId(null)}
        onConfirm={handleDelete}
        title="Delete source"
        message="Delete this source and all of its historical jobs? This cannot be undone."
        confirmText="Delete source"
        variant="danger"
        loading={deleteSubmitting}
      />

      <ScrapingJobDetailModal
        isOpen={!!jobDetailId}
        onClose={() => setJobDetailId(null)}
        jobDetail={jobDetail}
        loading={jobDetailLoading}
        error={jobDetailError}
        sourceLabel={
          (jobDetail?.source_id
            ? sourceNameById.get(jobDetail.source_id)
            : jobDetailId
              ? sourceNameById.get(
                  jobs.find(job => job.id === jobDetailId)?.source_id ?? ''
                )
              : null) ?? null
        }
      />
    </motion.div>
  );
}
