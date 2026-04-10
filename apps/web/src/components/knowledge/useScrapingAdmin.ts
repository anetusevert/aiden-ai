'use client';

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react';
import {
  apiClient,
  ApiClientError,
  type ScrapingJobDetailResponse,
  type ScrapingJobResponse,
  type ScrapingSourceCreate,
  type ScrapingSourceResponse,
  type ScrapingSourceUpdate,
  type ScrapingStatsResponse,
} from '@/lib/apiClient';
import {
  CONNECTOR_DEFAULTS,
  initialScheduleSelect,
  schedulePayloadFromForm,
} from '@/components/operator/scraping/config';

export type SourceFormState = {
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

export function useScrapingAdmin(enabled: boolean) {
  const [stats, setStats] = useState<ScrapingStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  const [sources, setSources] = useState<ScrapingSourceResponse[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<ScrapingJobResponse[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);

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

  const sourceNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of sources) map.set(s.id, s.display_name);
    return map;
  }, [sources]);

  const jobsById = useMemo(() => {
    const map = new Map<string, ScrapingJobResponse>();
    for (const j of jobs) map.set(j.id, j);
    return map;
  }, [jobs]);

  const hasActiveJobs = useMemo(
    () => jobs.some(j => j.status === 'pending' || j.status === 'running'),
    [jobs]
  );

  const recentJobs = useMemo(() => jobs.slice(0, 10), [jobs]);

  /* ── Loaders ──────────────────────────────────────── */

  const loadStats = useCallback(async () => {
    if (!enabled) return;
    try {
      setStats(await apiClient.getScrapingStats());
    } finally {
      setStatsLoading(false);
    }
  }, [enabled]);

  const loadSources = useCallback(async () => {
    if (!enabled) return;
    setSourcesError(null);
    try {
      setSources(await apiClient.getScrapingSources());
    } catch (e) {
      setSourcesError(
        e instanceof Error ? e.message : 'Failed to load scraping sources'
      );
    } finally {
      setSourcesLoading(false);
    }
  }, [enabled]);

  const loadJobs = useCallback(async () => {
    if (!enabled) return;
    setJobsError(null);
    try {
      setJobs(await apiClient.getScrapingJobs({ limit: 50 }));
    } catch (e) {
      setJobsError(
        e instanceof Error ? e.message : 'Failed to load scraping jobs'
      );
    } finally {
      setJobsLoading(false);
    }
  }, [enabled]);

  const loadAll = useCallback(() => {
    setStatsLoading(true);
    setSourcesLoading(true);
    setJobsLoading(true);
    return Promise.all([loadStats(), loadSources(), loadJobs()]);
  }, [loadStats, loadSources, loadJobs]);

  useEffect(() => {
    if (!enabled) return;
    void loadAll();
  }, [enabled, loadAll]);

  useEffect(() => {
    if (!enabled || !hasActiveJobs) return;
    const id = window.setInterval(() => {
      void loadJobs();
      void loadSources();
      void loadStats();
    }, 5000);
    return () => clearInterval(id);
  }, [hasActiveJobs, enabled, loadJobs, loadSources, loadStats]);

  /* ── Job detail polling ───────────────────────────── */

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
      .then(r => {
        if (!cancelled) setJobDetail(r);
      })
      .catch(e => {
        if (!cancelled)
          setJobDetailError(
            e instanceof Error ? e.message : 'Failed to load run'
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
    jobDetail?.status ?? jobs.find(j => j.id === jobDetailId)?.status;

  useEffect(() => {
    if (
      !jobDetailId ||
      (activeJobDetailStatus !== 'pending' &&
        activeJobDetailStatus !== 'running')
    )
      return;
    const id = window.setInterval(() => {
      void apiClient
        .getScrapingJob(jobDetailId)
        .then(setJobDetail)
        .catch(e => {
          setJobDetailError(
            e instanceof Error ? e.message : 'Failed to load run'
          );
        });
    }, 2000);
    return () => clearInterval(id);
  }, [activeJobDetailStatus, jobDetailId]);

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    };
  }, []);

  /* ── Handlers ─────────────────────────────────────── */

  const setActionError = useCallback((sourceId: string, msg: string) => {
    setActionErrors(c => ({ ...c, [sourceId]: msg }));
  }, []);

  const clearActionError = useCallback((sourceId: string) => {
    setActionErrors(c => {
      const next = { ...c };
      delete next[sourceId];
      return next;
    });
  }, []);

  const markSourceBusy = useCallback((sourceId: string, busy: boolean) => {
    setSourceBusyIds(c =>
      busy
        ? Array.from(new Set([...c, sourceId]))
        : c.filter(id => id !== sourceId)
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
    } catch (e) {
      setCreateError(
        e instanceof ApiClientError
          ? e.message
          : e instanceof Error
            ? e.message
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
    } catch (e) {
      setEditError(
        e instanceof ApiClientError
          ? e.message
          : e instanceof Error
            ? e.message
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
    } catch (e) {
      setActionError(
        source.id,
        e instanceof Error ? e.message : 'Failed to update source'
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
      setConfirmDeleteId(null);
      await Promise.all([loadSources(), loadJobs(), loadStats()]);
    } catch (e) {
      setSourcesError(
        e instanceof Error ? e.message : 'Failed to delete source'
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
    } catch (e) {
      setActionError(
        source.id,
        e instanceof ApiClientError
          ? e.message
          : e instanceof Error
            ? e.message
            : 'Failed to trigger source'
      );
    } finally {
      setTriggerBusyId(null);
    }
  };

  return {
    stats,
    statsLoading,
    sources,
    sourcesLoading,
    sourcesError,
    jobs,
    jobsLoading,
    jobsError,
    recentJobs,
    hasActiveJobs,
    sourceNameById,
    jobsById,
    highlightJobId,
    actionErrors,

    triggerBusyId,
    sourceBusyIds,

    createOpen,
    setCreateOpen,
    createSubmitting,
    createError,
    createForm,
    setCreateForm,
    resetCreateForm,
    handleCreateSubmit,

    editOpen,
    setEditOpen,
    editingSource,
    setEditingSource,
    editSubmitting,
    editError,
    editForm,
    setEditForm,
    openEditModal,
    handleEditSubmit,

    confirmDeleteId,
    setConfirmDeleteId,
    deleteSubmitting,
    handleDelete,

    handleToggleEnabled,
    handleTrigger,

    jobDetailId,
    setJobDetailId,
    jobDetail,
    jobDetailLoading,
    jobDetailError,

    loadAll,
    loadJobs,
    loadStats,
  };
}
