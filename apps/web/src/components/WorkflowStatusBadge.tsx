'use client';

import { useTranslations } from 'next-intl';
import { WorkflowResultStatus } from '@/lib/apiClient';

const STATUS_VARIANT: Record<
  WorkflowResultStatus,
  { variant: 'success' | 'warning' | 'error' | 'info'; icon: string }
> = {
  success: { variant: 'success', icon: '✓' },
  insufficient_sources: { variant: 'warning', icon: '!' },
  policy_denied: { variant: 'error', icon: '✕' },
  citation_violation: { variant: 'warning', icon: '!' },
  validation_failed: { variant: 'error', icon: '✕' },
  generation_failed: { variant: 'error', icon: '✕' },
};

interface WorkflowStatusBadgeProps {
  status: WorkflowResultStatus;
  showDescription?: boolean;
}

/**
 * WorkflowStatusBadge - Display a trust status badge for workflow results.
 */
const STATUS_ORDER: WorkflowResultStatus[] = [
  'success',
  'insufficient_sources',
  'policy_denied',
  'citation_violation',
  'validation_failed',
  'generation_failed',
];

export function WorkflowStatusBadge({
  status,
  showDescription = false,
}: WorkflowStatusBadgeProps) {
  const t = useTranslations('workflowStatus');
  const meta = STATUS_VARIANT[status] || STATUS_VARIANT.success;
  const badgeClass = `workflow-status-badge workflow-status-${meta.variant}`;

  const labelMap = Object.fromEntries(
    STATUS_ORDER.map(s => [s, t(`${s}.label`)])
  ) as Record<WorkflowResultStatus, string>;
  const descMap = Object.fromEntries(
    STATUS_ORDER.map(s => [s, t(`${s}.description`)])
  ) as Record<WorkflowResultStatus, string>;

  return (
    <div className={badgeClass}>
      <span className="workflow-status-icon">{meta.icon}</span>
      <div className="workflow-status-content">
        <span className="workflow-status-label">{labelMap[status]}</span>
        {showDescription && (
          <span className="workflow-status-desc">{descMap[status]}</span>
        )}
      </div>
    </div>
  );
}

export default WorkflowStatusBadge;
