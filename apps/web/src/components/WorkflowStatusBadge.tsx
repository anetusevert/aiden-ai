'use client';

import { WorkflowResultStatus } from '@/lib/apiClient';

/**
 * Status badge configuration for each workflow result status.
 */
const STATUS_CONFIG: Record<
  WorkflowResultStatus,
  {
    label: string;
    variant: 'success' | 'warning' | 'error' | 'info';
    icon: string;
    description: string;
  }
> = {
  success: {
    label: 'Verified',
    variant: 'success',
    icon: '✓',
    description: 'All citations validated',
  },
  insufficient_sources: {
    label: 'Limited Sources',
    variant: 'warning',
    icon: '!',
    description: 'Insufficient evidence for complete analysis',
  },
  policy_denied: {
    label: 'Policy Blocked',
    variant: 'error',
    icon: '✕',
    description: 'Blocked by workspace policy',
  },
  citation_violation: {
    label: 'Reduced Output',
    variant: 'warning',
    icon: '!',
    description: 'Some content removed due to citation requirements',
  },
  validation_failed: {
    label: 'Validation Failed',
    variant: 'error',
    icon: '✕',
    description: 'Failed to validate response',
  },
  generation_failed: {
    label: 'Generation Failed',
    variant: 'error',
    icon: '✕',
    description: 'Failed to generate response',
  },
};

interface WorkflowStatusBadgeProps {
  status: WorkflowResultStatus;
  showDescription?: boolean;
}

/**
 * WorkflowStatusBadge - Display a trust status badge for workflow results.
 */
export function WorkflowStatusBadge({
  status,
  showDescription = false,
}: WorkflowStatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.success;

  const badgeClass = `workflow-status-badge workflow-status-${config.variant}`;

  return (
    <div className={badgeClass}>
      <span className="workflow-status-icon">{config.icon}</span>
      <div className="workflow-status-content">
        <span className="workflow-status-label">{config.label}</span>
        {showDescription && (
          <span className="workflow-status-desc">{config.description}</span>
        )}
      </div>
    </div>
  );
}

export default WorkflowStatusBadge;
