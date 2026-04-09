'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import {
  apiClient,
  ApiClientError,
  ScrapingJobDetailResponse,
  ScrapingJobResponse,
  ScrapingJobRunLogEntry,
  ScrapingJobStatus,
  ScrapingSourceCreate,
  ScrapingSourceResponse,
  ScrapingSourceUpdate,
  ScrapingStatsResponse,
} from '@/lib/apiClient';
import { describeCron, formatDuration } from '@/lib/cronUtils';
import {
  ambientPulse,
  fadeUp,
  glassReveal,
  motionTokens,
  staggerContainer,
  staggerItem,
} from '@/lib/motion';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Skeleton } from '@/components/ui/Skeleton';
import { TabList } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';

const PRESET_CRONS = ['0 2 * * 0', '0 2 * * 1', '0 2 1 * *'] as const;
const CUSTOM_SENTINEL = '__custom__';

const CONNECTOR_OPTIONS = [
  { value: 'ksa_boe', label: 'KSA Bureau of Experts' },
  { value: 'ksa_moj', label: 'KSA Ministry of Justice' },
  { value: 'ksa_uaq', label: 'KSA Umm Al-Qura Gazette' },
  { value: 'uae_moj', label: 'UAE Ministry of Justice' },
  { value: 'qatar_almeezan', label: 'Qatar Al Meezan' },
] as const;

const CONNECTOR_DEFAULTS: Record<
  string,
  { display_name: string; jurisdiction: string; source_url: string }
> = {
  ksa_boe: {
    display_name: 'KSA Bureau of Experts',
    jurisdiction: 'KSA',
    source_url: 'https://laws.boe.gov.sa',
  },
  ksa_moj: {
    display_name: 'KSA Ministry of Justice',
    jurisdiction: 'KSA',
    source_url: 'https://www.moj.gov.sa',
  },
  ksa_uaq: {
    display_name: 'KSA Umm Al-Qura Gazette',
    jurisdiction: 'KSA',
    source_url: 'https://www.ummulqura.org.sa',
  },
  uae_moj: {
    display_name: 'UAE Ministry of Justice',
    jurisdiction: 'UAE',
    source_url: 'https://www.moj.gov.ae',
  },
  qatar_almeezan: {
    display_name: 'Qatar Al Meezan',
    jurisdiction: 'QATAR',
    source_url: 'https://www.almeezan.qa',
  },
};

const SCHEDULE_SELECT_OPTIONS = [
  { value: '', label: 'Manual only' },
  { value: '0 2 * * 0', label: 'Weekly (Sunday 2am)' },
  { value: '0 2 * * 1', label: 'Weekly (Monday 2am)' },
  { value: '0 2 1 * *', label: 'Monthly (1st of month)' },
  { value: CUSTOM_SENTINEL, label: 'Custom cron expression…' },
];

function formatRelativeTime(iso: string | null): string {
  if (!iso) return 'Never';
  const then = new Date(iso).getTime();
  const diffSec = Math.round((Date.now() - then) / 1000);
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  const abs = Math.abs(diffSec);
  if (abs < 60) return rtf.format(-diffSec, 'second');
  const diffMin = Math.round(diffSec / 60);
  if (Math.abs(diffMin) < 60) return rtf.format(-diffMin, 'minute');
  const diffHr = Math.round(diffMin / 60);
  if (Math.abs(diffHr) < 24) return rtf.format(-diffHr, 'hour');
  const diffDay = Math.round(diffHr / 24);
  if (Math.abs(diffDay) < 30) return rtf.format(-diffDay, 'day');
  const diffMonth = Math.round(diffDay / 30);
  return rtf.format(-diffMonth, 'month');
}

function jobDurationSeconds(job: ScrapingJobResponse): number | null {
  if (!job.started_at || !job.finished_at) return null;
  const a = new Date(job.started_at).getTime();
  const b = new Date(job.finished_at).getTime();
  const s = (b - a) / 1000;
  return Number.isFinite(s) && s >= 0 ? s : null;
}

function truncateMiddle(s: string, max: number): string {
  if (s.length <= max) return s;
  const half = Math.floor((max - 1) / 2);
  return `${s.slice(0, half)}…${s.slice(s.length - half)}`;
}

function schedulePayloadFromForm(
  scheduleValue: string,
  customCron: string
): string | null {
  if (scheduleValue === '') return null;
  if (scheduleValue === CUSTOM_SENTINEL) {
    const t = customCron.trim();
    return t.length ? t : null;
  }
  return scheduleValue;
}

function initialScheduleSelect(cron: string | null): {
  value: string;
  custom: string;
} {
  if (!cron) return { value: '', custom: '' };
  if ((PRESET_CRONS as readonly string[]).includes(cron)) {
    return { value: cron, custom: '' };
  }
  return { value: CUSTOM_SENTINEL, custom: cron };
}

function DocumentEmptyIcon() {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      aria-hidden
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14,2 14,8 20,8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden
    >
      <polyline points="3,6 5,6 21,6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function JobStatusBadge({ status }: { status: ScrapingJobStatus }) {
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  if (status === 'running') {
    return (
      <span className="kb-job-status kb-job-status-running">
        <motion.span
          className="kb-pulse-dot"
          variants={ambientPulse}
          animate="idle"
          aria-hidden
        />
        {label}
      </span>
    );
  }
  if (status === 'completed') {
    return (
      <Badge variant="success" size="sm">
        {label}
      </Badge>
    );
  }
  if (status === 'failed') {
    return (
      <Badge variant="error" size="sm">
        {label}
      </Badge>
    );
  }
  return (
    <Badge variant="muted" size="sm">
      {label}
    </Badge>
  );
}

function SourceStatusDot({
  enabled,
  lastJobFailed,
}: {
  enabled: boolean;
  lastJobFailed: boolean;
}) {
  let cls = 'kb-source-dot kb-source-dot-grey';
  if (enabled && lastJobFailed) cls = 'kb-source-dot kb-source-dot-warn';
  else if (enabled && !lastJobFailed) cls = 'kb-source-dot kb-source-dot-green';
  return <span className={cls} title={enabled ? 'Enabled' : 'Disabled'} />;
}

function EnabledSwitch({
  enabled,
  onChange,
  id,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  id: string;
}) {
  return (
    <button
      type="button"
      id={id}
      role="switch"
      aria-checked={enabled}
      className={`kb-enabled-switch ${enabled ? 'kb-enabled-switch-on' : ''}`}
      onClick={() => onChange(!enabled)}
    >
      <span className="kb-enabled-switch-knob" />
    </button>
  );
}

export default function KnowledgeBasePage() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const isPlatformAdmin = user?.is_platform_admin === true;
  const isWorkspaceAdmin = user?.role === 'ADMIN';
  const canAccessKnowledgeBase = isPlatformAdmin || isWorkspaceAdmin;

  const routeTab: 'sources' | 'jobs' = pathname.endsWith('/jobs')
    ? 'jobs'
    : 'sources';
  const [activeTab, setActiveTab] = useState<'sources' | 'jobs'>(routeTab);

  const [sources, setSources] = useState<ScrapingSourceResponse[]>([]);
  const [sourcesLoading, setSourcesLoading] = useState(true);
  const [sourcesError, setSourcesError] = useState<string | null>(null);

  const [jobs, setJobs] = useState<ScrapingJobResponse[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const jobsById = useMemo(() => {
    const m = new Map<string, ScrapingJobResponse>();
    for (const j of jobs) m.set(j.id, j);
    return m;
  }, [jobs]);

  const [addOpen, setAddOpen] = useState(false);
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addFormError, setAddFormError] = useState<string | null>(null);
  const [connectorName, setConnectorName] = useState('ksa_boe');
  const [addDisplayName, setAddDisplayName] = useState(
    CONNECTOR_DEFAULTS.ksa_boe.display_name
  );
  const [addJurisdiction, setAddJurisdiction] = useState(
    CONNECTOR_DEFAULTS.ksa_boe.jurisdiction
  );
  const [addSourceUrl, setAddSourceUrl] = useState(
    CONNECTOR_DEFAULTS.ksa_boe.source_url
  );
  const [addSchedule, setAddSchedule] = useState('');
  const [addCustomCron, setAddCustomCron] = useState('');
  const [addHarvest, setAddHarvest] = useState(500);
  const [addEnabled, setAddEnabled] = useState(true);

  const [editOpen, setEditOpen] = useState(false);
  const [editSource, setEditSource] = useState<ScrapingSourceResponse | null>(
    null
  );
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editFormError, setEditFormError] = useState<string | null>(null);
  const [editDisplayName, setEditDisplayName] = useState('');
  const [editSchedule, setEditSchedule] = useState('');
  const [editCustomCron, setEditCustomCron] = useState('');
  const [editHarvest, setEditHarvest] = useState(500);
  const [editEnabled, setEditEnabled] = useState(true);

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const [jobDetailId, setJobDetailId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<ScrapingJobDetailResponse | null>(
    null
  );
  const [jobDetailLoading, setJobDetailLoading] = useState(false);
  const [jobDetailError, setJobDetailError] = useState<string | null>(null);

  const [highlightJobId, setHighlightJobId] = useState<string | null>(null);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [triggerBusyId, setTriggerBusyId] = useState<string | null>(null);
  const triggerErrorTimeouts = useRef<
    Map<string, ReturnType<typeof setTimeout>>
  >(new Map());
  const [triggerErrors, setTriggerErrors] = useState<Record<string, string>>(
    {}
  );

  const [stats, setStats] = useState<ScrapingStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    setActiveTab(routeTab);
  }, [routeTab]);

  const loadStats = useCallback(async () => {
    if (!canAccessKnowledgeBase) return;
    try {
      const data = await apiClient.getScrapingStats();
      setStats(data);
    } catch {
      /* stats are non-critical */
    } finally {
      setStatsLoading(false);
    }
  }, [canAccessKnowledgeBase]);

  const loadSources = useCallback(async () => {
    if (!canAccessKnowledgeBase) return;
    setSourcesError(null);
    try {
      const list = await apiClient.getScrapingSources();
      setSources(list);
    } catch (e) {
      setSourcesError(
        e instanceof Error ? e.message : 'Failed to load scraping sources'
      );
    } finally {
      setSourcesLoading(false);
    }
  }, [canAccessKnowledgeBase]);

  const loadJobs = useCallback(async () => {
    if (!canAccessKnowledgeBase) return;
    setJobsError(null);
    try {
      const list = await apiClient.getScrapingJobs({ limit: 50 });
      setJobs(list);
    } catch (e) {
      setJobsError(
        e instanceof Error ? e.message : 'Failed to load scraping jobs'
      );
    } finally {
      setJobsLoading(false);
    }
  }, [canAccessKnowledgeBase]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!canAccessKnowledgeBase) return;
    setSourcesLoading(true);
    setJobsLoading(true);
    setStatsLoading(true);
    void loadSources();
    void loadJobs();
    void loadStats();
  }, [canAccessKnowledgeBase, loadSources, loadJobs, loadStats]);

  const hasActiveJobOnSource = useMemo(() => {
    return sources.some(s => {
      if (!s.last_job_id) return false;
      const j = jobsById.get(s.last_job_id);
      return j?.status === 'running' || j?.status === 'pending';
    });
  }, [sources, jobsById]);

  const jobsNeedPoll = useMemo(
    () => jobs.some(j => j.status === 'running' || j.status === 'pending'),
    [jobs]
  );

  useEffect(() => {
    if (!canAccessKnowledgeBase || !jobsNeedPoll) return;
    const id = window.setInterval(() => {
      void loadJobs();
    }, 5000);
    return () => clearInterval(id);
  }, [canAccessKnowledgeBase, jobsNeedPoll, loadJobs]);

  useEffect(() => {
    if (!canAccessKnowledgeBase || !hasActiveJobOnSource) return;
    const id = window.setInterval(() => {
      void loadSources();
      void loadJobs();
      void loadStats();
    }, 15000);
    return () => clearInterval(id);
  }, [
    canAccessKnowledgeBase,
    hasActiveJobOnSource,
    loadSources,
    loadJobs,
    loadStats,
  ]);

  useEffect(() => {
    const triggerTimeouts = triggerErrorTimeouts.current;
    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      triggerTimeouts.forEach(t => clearTimeout(t));
      triggerTimeouts.clear();
    };
  }, []);

  const openAddModal = () => {
    setAddFormError(null);
    const d = CONNECTOR_DEFAULTS.ksa_boe;
    setConnectorName('ksa_boe');
    setAddDisplayName(d.display_name);
    setAddJurisdiction(d.jurisdiction);
    setAddSourceUrl(d.source_url);
    setAddSchedule('');
    setAddCustomCron('');
    setAddHarvest(500);
    setAddEnabled(true);
    setAddOpen(true);
  };

  const onConnectorChange = (v: string) => {
    setConnectorName(v);
    const def = CONNECTOR_DEFAULTS[v];
    if (def) {
      setAddDisplayName(def.display_name);
      setAddJurisdiction(def.jurisdiction);
      setAddSourceUrl(def.source_url);
    }
  };

  const openEditModal = (s: ScrapingSourceResponse) => {
    setEditFormError(null);
    setEditSource(s);
    setEditDisplayName(s.display_name);
    const sch = initialScheduleSelect(s.schedule_cron);
    setEditSchedule(sch.value);
    setEditCustomCron(sch.custom);
    setEditHarvest(s.harvest_limit);
    setEditEnabled(s.enabled);
    setEditOpen(true);
  };

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddSubmitting(true);
    setAddFormError(null);
    const schedule_cron = schedulePayloadFromForm(addSchedule, addCustomCron);
    const body: ScrapingSourceCreate = {
      connector_name: connectorName,
      display_name: addDisplayName.trim(),
      jurisdiction: addJurisdiction.trim(),
      enabled: addEnabled,
      harvest_limit: addHarvest,
      schedule_cron,
    };
    const url = addSourceUrl.trim();
    if (url) body.source_url = url;
    try {
      await apiClient.createScrapingSource(body);
      setAddOpen(false);
      await loadSources();
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to create source';
      setAddFormError(msg);
    } finally {
      setAddSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editSource) return;
    setEditSubmitting(true);
    setEditFormError(null);
    const schedule_cron = schedulePayloadFromForm(editSchedule, editCustomCron);
    const patch: ScrapingSourceUpdate = {
      display_name: editDisplayName.trim(),
      enabled: editEnabled,
      harvest_limit: editHarvest,
      schedule_cron,
    };
    try {
      await apiClient.updateScrapingSource(editSource.id, patch);
      setEditOpen(false);
      setEditSource(null);
      await loadSources();
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to update source';
      setEditFormError(msg);
    } finally {
      setEditSubmitting(false);
    }
  };

  const confirmDelete = async (s: ScrapingSourceResponse) => {
    try {
      await apiClient.deleteScrapingSource(s.id);
      setConfirmDeleteId(null);
      setSources(prev => prev.filter(x => x.id !== s.id));
      await loadJobs();
    } catch (err) {
      setSourcesError(
        err instanceof Error ? err.message : 'Failed to delete source'
      );
      setConfirmDeleteId(null);
    }
  };

  const setTriggerErrorForSource = (sourceId: string, message: string) => {
    const prev = triggerErrorTimeouts.current.get(sourceId);
    if (prev) clearTimeout(prev);
    setTriggerErrors(prev => ({ ...prev, [sourceId]: message }));
    const t = setTimeout(() => {
      setTriggerErrors(prev => {
        const next = { ...prev };
        delete next[sourceId];
        return next;
      });
      triggerErrorTimeouts.current.delete(sourceId);
    }, 4000);
    triggerErrorTimeouts.current.set(sourceId, t);
  };

  const handleTrigger = async (s: ScrapingSourceResponse) => {
    setTriggerBusyId(s.id);
    try {
      const res = await apiClient.triggerScrapingSource(s.id);
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      setHighlightJobId(res.job_id);
      highlightTimerRef.current = setTimeout(() => {
        setHighlightJobId(null);
        highlightTimerRef.current = null;
      }, 1600);
      setActiveTab('jobs');
      await loadSources();
      await loadJobs();
    } catch (err) {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Trigger failed';
      setTriggerErrorForSource(s.id, msg);
    } finally {
      setTriggerBusyId(null);
    }
  };

  const loadJobDetail = useCallback(async (id: string) => {
    setJobDetailLoading(true);
    setJobDetailError(null);
    try {
      const data = await apiClient.getScrapingJob(id);
      setJobDetail(data);
    } catch (e) {
      setJobDetailError(e instanceof Error ? e.message : 'Failed to load job');
    } finally {
      setJobDetailLoading(false);
    }
  }, []);

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
      .then(data => {
        if (!cancelled) {
          setJobDetail(data);
        }
      })
      .catch(e => {
        if (!cancelled) {
          setJobDetailError(
            e instanceof Error ? e.message : 'Failed to load job'
          );
        }
      })
      .finally(() => {
        if (!cancelled) setJobDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [jobDetailId]);

  const activeJobDetailStatus =
    jobDetail?.status ?? jobsById.get(jobDetailId ?? '')?.status;

  useEffect(() => {
    if (
      !jobDetailId ||
      (activeJobDetailStatus !== 'pending' &&
        activeJobDetailStatus !== 'running')
    ) {
      return;
    }

    const id = window.setInterval(() => {
      void loadJobDetail(jobDetailId);
    }, 5000);
    return () => clearInterval(id);
  }, [activeJobDetailStatus, jobDetailId, loadJobDetail]);

  const sourceNameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const s of sources) m.set(s.id, s.display_name);
    return m;
  }, [sources]);

  const renderRunLogEntry = (entry: ScrapingJobRunLogEntry, i: number) => {
    const url = entry.source_url ?? entry.url ?? '—';
    const result = entry.result ?? entry.status ?? '—';
    const normalizedResult = result.toLowerCase();
    const ok = normalizedResult === 'success' || normalizedResult === 'ok';
    const fail =
      normalizedResult === 'fail' ||
      normalizedResult === 'failed' ||
      normalizedResult === 'error';
    return (
      <li key={i} className="kb-runlog-row">
        <div className="kb-runlog-main">
          <span className="kb-runlog-url" title={url}>
            {truncateMiddle(url, 56)}
          </span>
          {entry.error ? (
            <span className="kb-runlog-error" title={entry.error}>
              {truncateMiddle(entry.error, 72)}
            </span>
          ) : null}
        </div>
        <span
          className={
            fail
              ? 'kb-runlog-result kb-runlog-fail'
              : ok
                ? 'kb-runlog-result kb-runlog-ok'
                : 'kb-runlog-result'
          }
        >
          {result}
        </span>
      </li>
    );
  };

  if (!canAccessKnowledgeBase) {
    return (
      <div className="page-container">
        <div className="alert alert-error">
          <h3>Access Denied</h3>
          <p>
            This page is only available to workspace administrators or platform
            administrators.
          </p>
        </div>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp} className="page-container kb-page">
      <div className="page-header">
        <div>
          <h1>Legal Harvester</h1>
          <p className="text-secondary">
            Scrape, ingest, and monitor official legal publications across
            jurisdictions.
          </p>
        </div>
      </div>

      {/* ── Dashboard KPI cards ────────────────────────────────────── */}
      <div className="kb-kpi-grid">
        {statsLoading ? (
          <>
            {[0, 1, 2, 3].map(i => (
              <div key={i} className="kb-kpi-card">
                <Skeleton variant="title" width="40%" />
                <Skeleton variant="text" width="60%" />
              </div>
            ))}
          </>
        ) : stats ? (
          <>
            <div className="kb-kpi-card">
              <span className="kb-kpi-value">
                {stats.total_instruments.toLocaleString()}
              </span>
              <span className="kb-kpi-label">Legal Instruments</span>
            </div>
            <div className="kb-kpi-card">
              <span className="kb-kpi-value">
                {stats.active_sources}
                <span className="kb-kpi-secondary">
                  {' '}
                  / {stats.total_sources}
                </span>
              </span>
              <span className="kb-kpi-label">Active Sources</span>
            </div>
            <div className="kb-kpi-card">
              <span className="kb-kpi-value">
                {stats.running_jobs > 0 && (
                  <motion.span
                    className="kb-kpi-pulse"
                    variants={ambientPulse}
                    animate="idle"
                    aria-hidden
                  />
                )}
                {stats.running_jobs}
              </span>
              <span className="kb-kpi-label">Running Jobs</span>
            </div>
            <div className="kb-kpi-card">
              <span className="kb-kpi-value">
                {stats.items_harvested_7d.toLocaleString()}
              </span>
              <span className="kb-kpi-label">Harvested (7d)</span>
            </div>
          </>
        ) : null}
      </div>

      {/* ── Jurisdiction breakdown ─────────────────────────────────── */}
      {stats && Object.keys(stats.instruments_by_jurisdiction).length > 0 && (
        <div className="kb-jurisdiction-bar">
          <h3 className="kb-jurisdiction-heading">Corpus by Jurisdiction</h3>
          <div className="kb-jurisdiction-tracks">
            {Object.entries(stats.instruments_by_jurisdiction)
              .sort(([, a], [, b]) => b - a)
              .map(([jurisdiction, count]) => {
                const pct =
                  stats.total_instruments > 0
                    ? (count / stats.total_instruments) * 100
                    : 0;
                return (
                  <div key={jurisdiction} className="kb-jurisdiction-row">
                    <span className="kb-jurisdiction-name">{jurisdiction}</span>
                    <div className="kb-jurisdiction-track">
                      <motion.div
                        className="kb-jurisdiction-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.max(pct, 1)}%` }}
                        transition={{ duration: 0.6, ease: 'easeOut' }}
                      />
                    </div>
                    <span className="kb-jurisdiction-count">
                      {count.toLocaleString()}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      <div className="kb-panel">
        <TabList
          className="kb-tabs"
          tabs={[
            { id: 'sources', label: 'Sources' },
            { id: 'jobs', label: 'Jobs' },
          ]}
          activeTab={activeTab}
          onChange={id => setActiveTab(id as 'sources' | 'jobs')}
        />

        <div className="kb-tab-panel">
          {activeTab === 'sources' && (
            <motion.div
              key="sources"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: motionTokens.duration.base,
                ease: motionTokens.ease,
              }}
            >
              <div className="kb-sources-toolbar">
                <h2>Scraping sources ({sources.length})</h2>
                <Button type="button" onClick={openAddModal}>
                  Add Source
                </Button>
              </div>

              {sourcesError && (
                <div className="kb-inline-error kb-error-banner">
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
              )}

              {sourcesLoading ? (
                <div className="kb-source-skeleton-list">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="kb-source-card kb-source-skeleton">
                      <Skeleton variant="avatar" width={10} height={10} />
                      <div className="kb-skel-col">
                        <Skeleton variant="title" width="40%" />
                        <Skeleton variant="text" width="60%" />
                      </div>
                      <Skeleton variant="text" width={72} />
                      <Skeleton variant="text" width={120} />
                      <Skeleton variant="text" width={100} />
                      <Skeleton variant="button" width={120} height={32} />
                    </div>
                  ))}
                </div>
              ) : sources.length === 0 ? (
                <div className="kb-empty">
                  <DocumentEmptyIcon />
                  <h3>No sources configured</h3>
                  <p className="text-muted">
                    Add a connector to start harvesting official publications.
                  </p>
                  <Button type="button" onClick={openAddModal}>
                    Add your first source
                  </Button>
                </div>
              ) : (
                <div className="kb-source-list">
                  <AnimatePresence initial={false}>
                    {sources.map(s => {
                      const lastJob = s.last_job_id
                        ? jobsById.get(s.last_job_id)
                        : undefined;
                      const lastFailed = lastJob?.status === 'failed';
                      const scheduleLabel = s.schedule_cron
                        ? describeCron(s.schedule_cron)
                        : null;
                      const isConfirm = confirmDeleteId === s.id;

                      return (
                        <motion.div
                          key={s.id}
                          layout
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, transition: { duration: 0.35 } }}
                          className="kb-source-card"
                        >
                          {isConfirm ? (
                            <div className="kb-delete-confirm">
                              <p>
                                Delete <strong>{s.display_name}</strong>? This
                                cannot be undone.
                              </p>
                              <div className="kb-delete-actions">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  type="button"
                                  onClick={() => setConfirmDeleteId(null)}
                                >
                                  Cancel
                                </Button>
                                <Button
                                  variant="danger"
                                  size="sm"
                                  type="button"
                                  onClick={() => confirmDelete(s)}
                                >
                                  Delete
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <>
                              <div className="kb-source-col kb-source-status">
                                <SourceStatusDot
                                  enabled={s.enabled}
                                  lastJobFailed={lastFailed}
                                />
                              </div>
                              <div className="kb-source-col kb-source-main">
                                <div className="kb-source-title">
                                  {s.display_name}
                                </div>
                                <div className="kb-source-sub text-muted">
                                  {s.connector_name}
                                </div>
                              </div>
                              <div className="kb-source-col">
                                <Badge variant="viewer" size="sm">
                                  {s.jurisdiction}
                                </Badge>
                              </div>
                              <div className="kb-source-col kb-source-schedule text-muted">
                                {scheduleLabel ?? (
                                  <span className="text-muted">
                                    Manual only
                                  </span>
                                )}
                              </div>
                              <div
                                className={`kb-source-col kb-source-lastrun ${lastFailed ? 'kb-lastrun-fail' : ''}`}
                              >
                                <span>{formatRelativeTime(s.last_run_at)}</span>
                                {lastJob && lastJob.status === 'completed' && (
                                  <span className="kb-source-lastjob-stats">
                                    {lastJob.items_upserted} upserted
                                    {lastJob.items_failed > 0 && (
                                      <>, {lastJob.items_failed} failed</>
                                    )}
                                    {(() => {
                                      const dur = jobDurationSeconds(lastJob);
                                      return dur != null
                                        ? `, ${formatDuration(dur)}`
                                        : '';
                                    })()}
                                  </span>
                                )}
                              </div>
                              <div className="kb-source-col kb-source-actions">
                                <button
                                  type="button"
                                  className="btn btn-ghost btn-sm kb-icon-btn"
                                  title="Trigger harvest"
                                  disabled={triggerBusyId === s.id}
                                  onClick={() => handleTrigger(s)}
                                >
                                  {triggerBusyId === s.id ? (
                                    <span className="spinner spinner-sm" />
                                  ) : (
                                    <PlayIcon />
                                  )}
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-ghost btn-sm kb-icon-btn"
                                  title="Edit"
                                  onClick={() => openEditModal(s)}
                                >
                                  <PencilIcon />
                                </button>
                                <button
                                  type="button"
                                  className="btn btn-ghost btn-sm kb-icon-btn"
                                  title="Delete"
                                  onClick={() => setConfirmDeleteId(s.id)}
                                >
                                  <TrashIcon />
                                </button>
                              </div>
                            </>
                          )}
                          <AnimatePresence>
                            {triggerErrors[s.id] && (
                              <motion.div
                                className="kb-trigger-toast"
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{
                                  duration: motionTokens.duration.fast,
                                }}
                              >
                                {triggerErrors[s.id]}
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                </div>
              )}
            </motion.div>
          )}

          {activeTab === 'jobs' && (
            <motion.div
              key="jobs"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: motionTokens.duration.base,
                ease: motionTokens.ease,
              }}
            >
              <h2 className="kb-jobs-heading">Recent jobs</h2>
              {jobsError && (
                <div className="kb-inline-error kb-error-banner">
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
              )}
              {jobsLoading ? (
                <div className="kb-jobs-skeleton">
                  {[0, 1, 2, 3].map(i => (
                    <SkeletonRow key={i} />
                  ))}
                </div>
              ) : jobs.length === 0 ? (
                <p className="text-muted kb-empty-jobs">No jobs yet.</p>
              ) : (
                <div className="kb-table-wrap">
                  <table className="kb-table">
                    <thead>
                      <tr>
                        <th>Source</th>
                        <th>Status</th>
                        <th>Triggered by</th>
                        <th>Started</th>
                        <th>Duration</th>
                        <th>Results</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <motion.tbody
                      variants={staggerContainer}
                      initial="hidden"
                      animate="visible"
                    >
                      {jobs.map(job => {
                        const flash = highlightJobId === job.id;
                        return (
                          <motion.tr
                            key={job.id}
                            variants={staggerItem}
                            className={flash ? 'kb-job-row-flash' : undefined}
                          >
                            <td>
                              {sourceNameById.get(job.source_id) ??
                                job.connector_name}
                            </td>
                            <td>
                              <JobStatusBadge status={job.status} />
                            </td>
                            <td>
                              <Badge
                                variant={
                                  job.triggered_by === 'scheduler'
                                    ? 'info'
                                    : 'default'
                                }
                                size="sm"
                              >
                                {job.triggered_by === 'scheduler'
                                  ? 'Scheduled'
                                  : 'Manual'}
                              </Badge>
                            </td>
                            <td className="text-muted">
                              {job.started_at
                                ? new Date(job.started_at).toLocaleString()
                                : '—'}
                            </td>
                            <td className="text-muted">
                              {(() => {
                                const dur = jobDurationSeconds(job);
                                if (dur != null) return formatDuration(dur);
                                if (
                                  job.status === 'running' ||
                                  job.status === 'pending'
                                )
                                  return '…';
                                return '—';
                              })()}
                            </td>
                            <td>
                              <span>
                                {job.items_upserted} upserted /{' '}
                                {job.items_failed} failed
                              </span>
                              {(job.status === 'running' ||
                                job.status === 'pending') &&
                                job.items_listed > 0 && (
                                  <div className="kb-job-progress-track">
                                    <motion.div
                                      className="kb-job-progress-fill"
                                      initial={{ width: 0 }}
                                      animate={{
                                        width: `${Math.min(
                                          100,
                                          ((job.items_upserted +
                                            job.items_failed) /
                                            job.items_listed) *
                                            100
                                        )}%`,
                                      }}
                                      transition={{
                                        duration: 0.4,
                                        ease: 'easeOut',
                                      }}
                                    />
                                  </div>
                                )}
                            </td>
                            <td>
                              <Button
                                variant="outline"
                                size="sm"
                                type="button"
                                onClick={() => setJobDetailId(job.id)}
                              >
                                View details
                              </Button>
                            </td>
                          </motion.tr>
                        );
                      })}
                    </motion.tbody>
                  </table>
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>

      <Modal
        isOpen={addOpen}
        onClose={() => !addSubmitting && setAddOpen(false)}
        title="Add scraping source"
        size="lg"
        footer={
          <>
            <Button
              variant="outline"
              type="button"
              disabled={addSubmitting}
              onClick={() => setAddOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="kb-add-source-form"
              loading={addSubmitting}
            >
              Add Source
            </Button>
          </>
        }
      >
        <motion.form
          id="kb-add-source-form"
          onSubmit={handleAddSubmit}
          initial={glassReveal.initial}
          animate={glassReveal.animate}
        >
          {addFormError && (
            <p className="form-hint text-error kb-modal-error">
              {addFormError}
            </p>
          )}
          <Select
            label="Connector"
            options={[...CONNECTOR_OPTIONS]}
            value={connectorName}
            onChange={e => onConnectorChange(e.target.value)}
          />
          <Input
            label="Display name"
            value={addDisplayName}
            onChange={e => setAddDisplayName(e.target.value)}
            required
          />
          <Input
            label="Jurisdiction"
            value={addJurisdiction}
            onChange={e => setAddJurisdiction(e.target.value)}
            required
          />
          <Input
            label="Source URL"
            optional
            placeholder="https://…"
            value={addSourceUrl}
            onChange={e => setAddSourceUrl(e.target.value)}
          />
          <Select
            label="Schedule"
            options={SCHEDULE_SELECT_OPTIONS}
            value={addSchedule}
            onChange={e => setAddSchedule(e.target.value)}
          />
          {addSchedule === CUSTOM_SENTINEL && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
            >
              <Input
                label="Cron expression"
                hint="Five fields: minute hour day-of-month month day-of-week"
                value={addCustomCron}
                onChange={e => setAddCustomCron(e.target.value)}
                placeholder="0 2 * * *"
              />
            </motion.div>
          )}
          <Input
            label="Harvest limit"
            type="number"
            min={10}
            max={5000}
            value={addHarvest}
            onChange={e =>
              setAddHarvest(
                Math.min(5000, Math.max(10, parseInt(e.target.value, 10) || 10))
              )
            }
          />
          <div className="form-group kb-toggle-row">
            <span className="form-label">Enabled</span>
            <EnabledSwitch
              id="add-enabled"
              enabled={addEnabled}
              onChange={setAddEnabled}
            />
          </div>
        </motion.form>
      </Modal>

      {editOpen && editSource && (
        <Modal
          isOpen
          onClose={() => !editSubmitting && setEditOpen(false)}
          title="Edit source"
          size="lg"
          footer={
            <>
              <Button
                variant="outline"
                type="button"
                disabled={editSubmitting}
                onClick={() => setEditOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                form="kb-edit-source-form"
                loading={editSubmitting}
              >
                Save
              </Button>
            </>
          }
        >
          <motion.form
            id="kb-edit-source-form"
            onSubmit={handleEditSubmit}
            initial={glassReveal.initial}
            animate={glassReveal.animate}
          >
            {editFormError && (
              <p className="form-hint text-error kb-modal-error">
                {editFormError}
              </p>
            )}
            <Input
              label="Display name"
              value={editDisplayName}
              onChange={e => setEditDisplayName(e.target.value)}
              required
            />
            <Select
              label="Schedule"
              options={SCHEDULE_SELECT_OPTIONS}
              value={editSchedule}
              onChange={e => setEditSchedule(e.target.value)}
            />
            {editSchedule === CUSTOM_SENTINEL && (
              <Input
                label="Cron expression"
                hint="Five fields: minute hour day-of-month month day-of-week"
                value={editCustomCron}
                onChange={e => setEditCustomCron(e.target.value)}
                placeholder="0 2 * * *"
              />
            )}
            <Input
              label="Harvest limit"
              type="number"
              min={10}
              max={5000}
              value={editHarvest}
              onChange={e =>
                setEditHarvest(
                  Math.min(
                    5000,
                    Math.max(10, parseInt(e.target.value, 10) || 10)
                  )
                )
              }
            />
            <div className="form-group kb-toggle-row">
              <span className="form-label">Enabled</span>
              <EnabledSwitch
                id="edit-enabled"
                enabled={editEnabled}
                onChange={setEditEnabled}
              />
            </div>
          </motion.form>
        </Modal>
      )}

      <Modal
        isOpen={!!jobDetailId}
        onClose={() => setJobDetailId(null)}
        title="Job details"
        size="lg"
        footer={
          <Button
            variant="outline"
            type="button"
            onClick={() => setJobDetailId(null)}
          >
            Close
          </Button>
        }
      >
        {jobDetailLoading && (
          <div className="kb-detail-loading">
            <span className="spinner spinner-md" />
          </div>
        )}
        {jobDetailError && (
          <p className="form-hint text-error">{jobDetailError}</p>
        )}
        {jobDetail && !jobDetailLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: motionTokens.duration.base }}
          >
            <div className="kb-detail-header">
              <span className="kb-detail-connector">
                {jobDetail.connector_name}
              </span>
              <JobStatusBadge status={jobDetail.status} />
              <Badge
                variant={
                  jobDetail.triggered_by === 'scheduler' ? 'info' : 'default'
                }
                size="sm"
              >
                {jobDetail.triggered_by === 'scheduler'
                  ? 'Scheduled'
                  : 'Manual'}
              </Badge>
            </div>
            <div className="kb-detail-meta">
              <div>
                <span className="text-muted">Started</span>
                <p>
                  {jobDetail.started_at
                    ? new Date(jobDetail.started_at).toLocaleString()
                    : '—'}
                </p>
              </div>
              <div>
                <span className="text-muted">Finished</span>
                <p>
                  {jobDetail.finished_at
                    ? new Date(jobDetail.finished_at).toLocaleString()
                    : '—'}
                </p>
              </div>
              <div>
                <span className="text-muted">Duration</span>
                <p>
                  {jobDurationSeconds(jobDetail) != null
                    ? formatDuration(jobDurationSeconds(jobDetail)!)
                    : '—'}
                </p>
              </div>
            </div>
            <div className="kb-detail-stats">
              <div className="kb-stat">
                <span className="kb-stat-value">{jobDetail.items_listed}</span>
                <span className="kb-stat-label">Listed</span>
              </div>
              <div className="kb-stat">
                <span className="kb-stat-value">
                  {jobDetail.items_upserted}
                </span>
                <span className="kb-stat-label">Upserted</span>
              </div>
              <div className="kb-stat">
                <span className="kb-stat-value">{jobDetail.items_failed}</span>
                <span className="kb-stat-label">Failed</span>
              </div>
            </div>
            {jobDetail.error_detail && (
              <pre className="kb-error-block">{jobDetail.error_detail}</pre>
            )}
            {jobDetail.run_log && jobDetail.run_log.length > 0 && (
              <div className="kb-runlog">
                <h4 className="text-muted">Run log</h4>
                <ul className="kb-runlog-list">
                  {jobDetail.run_log
                    .slice(0, 100)
                    .map((entry, i) => renderRunLogEntry(entry, i))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </Modal>

      <style jsx>{`
        .kb-page.page-container {
          padding: 2rem;
          max-width: 1400px;
          margin: 0 auto;
        }

        /* ── KPI Cards ──────────────────────────────────── */
        .kb-kpi-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: var(--space-4, 1rem);
          margin-bottom: var(--space-5, 1.25rem);
        }

        .kb-kpi-card {
          background: var(--card-bg, var(--bg-elevated, #fff));
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 8px;
          padding: var(--space-5, 1.25rem) var(--space-5, 1.25rem);
          display: flex;
          flex-direction: column;
          gap: var(--space-1, 0.25rem);
        }

        .kb-kpi-value {
          font-size: 2rem;
          font-weight: 700;
          line-height: 1.1;
          color: var(--foreground, inherit);
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }

        .kb-kpi-secondary {
          font-size: 1.1rem;
          font-weight: 500;
          color: var(--text-muted, #9ca3af);
        }

        .kb-kpi-label {
          font-size: 0.8rem;
          font-weight: 500;
          color: var(--text-muted, #9ca3af);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .kb-kpi-pulse {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.85);
          display: inline-block;
        }

        @media (max-width: 768px) {
          .kb-kpi-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        /* ── Jurisdiction breakdown ─────────────────────── */
        .kb-jurisdiction-bar {
          background: var(--card-bg, var(--bg-elevated, #fff));
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 8px;
          padding: var(--space-5, 1.25rem);
          margin-bottom: var(--space-5, 1.25rem);
        }

        .kb-jurisdiction-heading {
          margin: 0 0 var(--space-3, 0.75rem);
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-muted, #9ca3af);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .kb-jurisdiction-tracks {
          display: flex;
          flex-direction: column;
          gap: var(--space-2, 0.5rem);
        }

        .kb-jurisdiction-row {
          display: grid;
          grid-template-columns: 80px 1fr 60px;
          align-items: center;
          gap: var(--space-3, 0.75rem);
        }

        .kb-jurisdiction-name {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--foreground, inherit);
        }

        .kb-jurisdiction-track {
          height: 8px;
          border-radius: 4px;
          background: var(--secondary-light, rgba(255, 255, 255, 0.06));
          overflow: hidden;
        }

        .kb-jurisdiction-fill {
          height: 100%;
          border-radius: 4px;
          background: rgba(255, 255, 255, 0.85);
        }

        .kb-jurisdiction-count {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-muted, #9ca3af);
          text-align: right;
        }

        /* ── Job progress bar ───────────────────────────── */
        .kb-job-progress-track {
          margin-top: 4px;
          height: 4px;
          border-radius: 2px;
          background: var(--secondary-light, rgba(255, 255, 255, 0.06));
          overflow: hidden;
          min-width: 80px;
        }

        .kb-job-progress-fill {
          height: 100%;
          border-radius: 2px;
          background: rgba(255, 255, 255, 0.85);
        }

        /* ── Source last-job inline stats ────────────────── */
        .kb-source-lastrun {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .kb-source-lastjob-stats {
          font-size: 0.75rem;
          color: var(--text-muted, #9ca3af);
        }

        .page-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 2rem;
        }

        .page-header h1 {
          margin: 0 0 0.5rem 0;
        }

        .text-secondary {
          color: var(--text-secondary, #6b7280);
          margin: 0;
        }

        .text-muted {
          color: var(--text-muted, #9ca3af);
        }

        .kb-panel {
          background: var(--card-bg, var(--bg-elevated, #fff));
          border-radius: 8px;
          border: 1px solid var(--border-color, #e5e7eb);
          padding: var(--space-6, 1.5rem);
        }

        .kb-tabs {
          margin-bottom: var(--space-5, 1.25rem);
        }

        .kb-tab-panel {
          min-height: 200px;
        }

        .kb-sources-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: var(--space-4, 1rem);
        }

        .kb-sources-toolbar h2,
        .kb-jobs-heading {
          margin: 0;
          font-size: 1.1rem;
        }

        .kb-jobs-heading {
          margin-bottom: var(--space-4, 1rem);
        }

        .kb-error-banner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: var(--space-3);
          margin-bottom: var(--space-4);
        }

        .kb-inline-error {
          padding: var(--space-3) var(--space-4);
          border-radius: var(--radius-md, 6px);
          background: rgba(220, 38, 38, 0.1);
          border: 1px solid rgba(220, 38, 38, 0.25);
          color: var(--error, #f87171);
          font-size: var(--text-sm, 0.875rem);
        }

        .kb-source-skeleton-list,
        .kb-source-list {
          display: flex;
          flex-direction: column;
          gap: var(--space-4, 1rem);
        }

        .kb-source-card {
          display: grid;
          grid-template-columns: 24px 1fr 100px minmax(120px, 1.2fr) 120px 140px;
          gap: var(--space-4);
          align-items: center;
          padding: var(--space-4);
          border: 1px solid var(--border-color, #e5e7eb);
          border-radius: 6px;
          background: var(--bg-elevated, var(--card-bg));
          position: relative;
        }

        .kb-source-skeleton.kb-source-card {
          align-items: center;
        }

        .kb-skel-col {
          display: flex;
          flex-direction: column;
          gap: var(--space-2);
        }

        .kb-source-title {
          font-weight: 600;
          color: var(--foreground, inherit);
        }

        .kb-source-sub {
          font-size: 0.85rem;
        }

        .kb-source-schedule {
          font-size: 0.85rem;
        }

        .kb-lastrun-fail {
          color: var(--error, #ef4444);
        }

        .kb-source-actions {
          display: flex;
          gap: var(--space-1);
          justify-content: flex-end;
        }

        .kb-icon-btn {
          min-width: 36px;
          padding: var(--space-2);
        }

        .kb-delete-confirm {
          grid-column: 1 / -1;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: var(--space-3);
        }

        .kb-delete-actions {
          display: flex;
          gap: var(--space-2);
        }

        .kb-trigger-toast {
          grid-column: 1 / -1;
          margin-top: var(--space-2);
          padding: var(--space-2) var(--space-3);
          background: rgba(220, 38, 38, 0.12);
          border-radius: var(--radius-md);
          color: var(--error, #f87171);
          font-size: 0.85rem;
        }

        .kb-source-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          display: inline-block;
        }

        .kb-source-dot-green {
          background: #22c55e;
          box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.25);
        }

        .kb-source-dot-warn {
          background: rgba(255, 255, 255, 0.85);
          box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.2);
        }

        .kb-source-dot-grey {
          background: #6b7280;
        }

        .kb-empty {
          text-align: center;
          padding: var(--space-10) var(--space-4);
          color: var(--text-muted);
        }

        .kb-empty svg {
          margin-bottom: var(--space-4);
          opacity: 0.45;
        }

        .kb-empty h3 {
          margin: 0 0 var(--space-2);
          color: var(--foreground, inherit);
        }

        .kb-empty-jobs {
          padding: var(--space-6);
        }

        .kb-table-wrap {
          overflow-x: auto;
        }

        .kb-table {
          width: 100%;
          border-collapse: collapse;
        }

        .kb-table th,
        .kb-table td {
          padding: var(--space-3) var(--space-3);
          text-align: left;
          border-bottom: 1px solid var(--border-color, #e5e7eb);
        }

        .kb-table th {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--text-muted);
        }

        @keyframes kbJobFlash {
          0% {
            background-color: rgba(255, 255, 255, 0.12);
          }
          100% {
            background-color: transparent;
          }
        }

        .kb-job-row-flash {
          animation: kbJobFlash 1.5s ease-out forwards;
        }

        .kb-job-status {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: var(--text-sm, 0.875rem);
          font-weight: 500;
          color: var(--foreground, inherit);
        }

        .kb-pulse-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.85);
          display: inline-block;
        }

        .kb-modal-error {
          margin-bottom: var(--space-4);
        }

        .kb-toggle-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: var(--space-4);
        }

        .kb-enabled-switch {
          width: 44px;
          height: 24px;
          border-radius: 12px;
          border: 1px solid var(--border-color);
          background: var(--secondary-light, #374151);
          position: relative;
          cursor: pointer;
          transition: background 0.2s ease;
        }

        .kb-enabled-switch-on {
          background: var(--primary, #3b82f6);
        }

        .kb-enabled-switch-knob {
          position: absolute;
          top: 2px;
          left: 2px;
          width: 18px;
          height: 18px;
          border-radius: 50%;
          background: #fff;
          transition: transform 0.2s ease;
        }

        .kb-enabled-switch-on .kb-enabled-switch-knob {
          transform: translateX(20px);
        }

        .kb-detail-loading {
          display: flex;
          justify-content: center;
          padding: var(--space-8);
        }

        .kb-detail-header {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: var(--space-3);
          margin-bottom: var(--space-4);
        }

        .kb-detail-connector {
          font-weight: 600;
          font-size: 1.05rem;
        }

        .kb-detail-meta {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: var(--space-4);
          margin-bottom: var(--space-5);
        }

        .kb-detail-meta p {
          margin: var(--space-1) 0 0;
        }

        .kb-detail-stats {
          display: flex;
          gap: var(--space-6);
          flex-wrap: wrap;
          margin-bottom: var(--space-5);
        }

        .kb-stat {
          text-align: center;
          min-width: 88px;
        }

        .kb-stat-value {
          display: block;
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--foreground, inherit);
        }

        .kb-stat-label {
          font-size: 0.75rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        .kb-error-block {
          padding: var(--space-3);
          border-radius: var(--radius-md);
          border: 1px solid var(--error, #ef4444);
          background: rgba(220, 38, 38, 0.08);
          color: var(--error, #fca5a5);
          font-size: 0.85rem;
          white-space: pre-wrap;
          margin-bottom: var(--space-4);
        }

        .kb-runlog h4 {
          margin: 0 0 var(--space-2);
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .kb-runlog-list {
          list-style: none;
          margin: 0;
          padding: 0;
          max-height: 300px;
          overflow-y: auto;
          border: 1px solid var(--border-color);
          border-radius: var(--radius-md);
        }

        .kb-runlog-row {
          display: flex;
          justify-content: space-between;
          gap: var(--space-3);
          padding: var(--space-2) var(--space-3);
          border-bottom: 1px solid var(--border-color);
          font-size: 0.8rem;
        }

        .kb-runlog-row:last-child {
          border-bottom: none;
        }

        .kb-runlog-url {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: var(--text-muted);
        }

        .kb-runlog-main {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }

        .kb-runlog-error {
          color: rgba(255, 255, 255, 0.48);
          font-size: 0.72rem;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .kb-runlog-result {
          flex-shrink: 0;
          font-weight: 500;
        }

        .kb-runlog-ok {
          color: #22c55e;
        }

        .kb-runlog-fail {
          color: var(--error, #ef4444);
        }

        .alert.alert-error {
          padding: 1rem;
          border-radius: 6px;
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fecaca;
        }

        @media (max-width: 1024px) {
          .kb-source-card {
            grid-template-columns: 1fr;
            gap: var(--space-2);
          }
          .kb-source-actions {
            justify-content: flex-start;
          }
        }
      `}</style>
    </motion.div>
  );
}

function SkeletonRow() {
  return (
    <div
      className="kb-skeleton-row"
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 100px 100px 120px 100px 1fr 100px',
        gap: 'var(--space-3)',
        padding: 'var(--space-3) 0',
        borderBottom: '1px solid var(--border-color)',
      }}
    >
      {Array.from({ length: 7 }).map((_, i) => (
        <Skeleton key={i} variant="text" width={i === 0 ? '70%' : '80%'} />
      ))}
    </div>
  );
}
