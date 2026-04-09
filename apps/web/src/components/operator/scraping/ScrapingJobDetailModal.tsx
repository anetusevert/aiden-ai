'use client';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import {
  ScrapingJobDetailResponse,
  ScrapingJobRunLogEntry,
  ScrapingJobStatus,
} from '@/lib/apiClient';
import { formatDuration } from '@/lib/cronUtils';
import styles from './ScrapingControlCenter.module.css';

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

function truncateMiddle(value: string, max: number): string {
  if (value.length <= max) return value;
  const half = Math.floor((max - 1) / 2);
  return `${value.slice(0, half)}...${value.slice(value.length - half)}`;
}

function JobStatusBadge({ status }: { status: ScrapingJobStatus }) {
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  if (status === 'running') {
    return <Badge variant="info">{label}</Badge>;
  }
  if (status === 'completed') {
    return <Badge variant="success">{label}</Badge>;
  }
  if (status === 'failed') {
    return <Badge variant="error">{label}</Badge>;
  }
  return <Badge variant="warning">{label}</Badge>;
}

function renderRunLogEntry(entry: ScrapingJobRunLogEntry, index: number) {
  const url = entry.source_url ?? entry.url ?? '-';
  const result = entry.result ?? entry.status ?? '-';
  const normalized = result.toLowerCase();
  const resultClass =
    normalized === 'ok' || normalized === 'success'
      ? styles.runLogOk
      : normalized === 'error' ||
          normalized === 'failed' ||
          normalized === 'fail'
        ? styles.runLogFail
        : '';

  return (
    <li key={`${url}-${index}`} className={styles.runLogRow}>
      <div className={styles.runLogMain}>
        <span className={styles.runLogUrl} title={url}>
          {truncateMiddle(url, 80)}
        </span>
        {entry.error ? (
          <span className={styles.runLogError} title={entry.error}>
            {truncateMiddle(entry.error, 120)}
          </span>
        ) : null}
      </div>
      <span className={`${styles.runLogResult} ${resultClass}`}>{result}</span>
    </li>
  );
}

interface ScrapingJobDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobDetail: ScrapingJobDetailResponse | null;
  loading: boolean;
  error: string | null;
}

export function ScrapingJobDetailModal({
  isOpen,
  onClose,
  jobDetail,
  loading,
  error,
}: ScrapingJobDetailModalProps) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Run details"
      size="lg"
      footer={
        <Button variant="outline" type="button" onClick={onClose}>
          Close
        </Button>
      }
    >
      {loading ? (
        <div className={styles.modalLoading}>
          <span className="spinner spinner-md" />
        </div>
      ) : null}

      {!loading && error ? (
        <p className="form-hint text-error">{error}</p>
      ) : null}

      {!loading && jobDetail ? (
        <div className={styles.detailContent}>
          <div className={styles.detailHeader}>
            <div>
              <span className={styles.metaLabel}>Connector</span>
              <h3 className={styles.detailTitle}>{jobDetail.connector_name}</h3>
            </div>
            <div className={styles.detailBadges}>
              <JobStatusBadge status={jobDetail.status} />
              <Badge
                variant={
                  jobDetail.triggered_by === 'scheduler' ? 'info' : 'default'
                }
              >
                {jobDetail.triggered_by === 'scheduler'
                  ? 'Scheduled'
                  : 'Manual'}
              </Badge>
            </div>
          </div>

          <div className={styles.detailGrid}>
            <div className={styles.detailStat}>
              <span className={styles.metaLabel}>Started</span>
              <p>
                {jobDetail.started_at
                  ? new Date(jobDetail.started_at).toLocaleString()
                  : '-'}
              </p>
            </div>
            <div className={styles.detailStat}>
              <span className={styles.metaLabel}>Finished</span>
              <p>
                {jobDetail.finished_at
                  ? new Date(jobDetail.finished_at).toLocaleString()
                  : '-'}
              </p>
            </div>
            <div className={styles.detailStat}>
              <span className={styles.metaLabel}>Duration</span>
              <p>
                {jobDurationSeconds(jobDetail) != null
                  ? formatDuration(jobDurationSeconds(jobDetail)!)
                  : '-'}
              </p>
            </div>
          </div>

          <div className={styles.detailMetrics}>
            <div className={styles.metricCard}>
              <span className={styles.metricValue}>
                {jobDetail.items_listed}
              </span>
              <span className={styles.metricLabel}>Listed</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricValue}>
                {jobDetail.items_upserted}
              </span>
              <span className={styles.metricLabel}>Upserted</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricValue}>
                {jobDetail.items_failed}
              </span>
              <span className={styles.metricLabel}>Failed</span>
            </div>
          </div>

          {jobDetail.error_detail ? (
            <pre className={styles.detailError}>{jobDetail.error_detail}</pre>
          ) : null}

          {jobDetail.run_log && jobDetail.run_log.length > 0 ? (
            <div className={styles.runLogCard}>
              <div className={styles.sectionHeader}>
                <div>
                  <h4>Run log</h4>
                  <p>
                    The first 100 harvested items are retained for operator
                    review.
                  </p>
                </div>
              </div>
              <ul className={styles.runLogList}>
                {jobDetail.run_log.slice(0, 100).map(renderRunLogEntry)}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </Modal>
  );
}
