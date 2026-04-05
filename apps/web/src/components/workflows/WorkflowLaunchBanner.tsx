'use client';

import { motion } from 'framer-motion';
import { useSearchParams } from 'next/navigation';
import { fadeIn } from '@/lib/motion';
import {
  WORKFLOW_CATEGORY_ACCENTS,
  getCategoryDisplayName,
  getToolLabel,
  getWorkflowFromSearchParam,
  renderCategoryIcon,
} from '@/lib/workflowPresentation';
import type { ToolRoute } from '@/lib/workflowRegistry';

interface WorkflowLaunchBannerProps {
  currentRoute: ToolRoute;
}

export function WorkflowLaunchBanner({
  currentRoute,
}: WorkflowLaunchBannerProps) {
  const searchParams = useSearchParams();
  const workflow = getWorkflowFromSearchParam(searchParams.get('workflow'));

  if (!workflow) return null;

  const accent = WORKFLOW_CATEGORY_ACCENTS[workflow.category];
  const toolLabel = getToolLabel(currentRoute);

  return (
    <motion.section
      className="workflow-launch-banner"
      style={{ '--workflow-accent': accent } as React.CSSProperties}
      {...fadeIn}
    >
      <div className="workflow-launch-banner-icon">
        {renderCategoryIcon(workflow.category, 20)}
      </div>

      <div className="workflow-launch-banner-copy">
        <p className="workflow-launch-banner-kicker">
          {getCategoryDisplayName(workflow.category)}
        </p>
        <h2 className="workflow-launch-banner-title">{workflow.name}</h2>
        <p className="workflow-launch-banner-description">
          Amin opened {toolLabel} as part of this workflow. Use this workspace
          to advance the next step.
        </p>
      </div>

      <div className="workflow-launch-banner-meta">
        <span className="workflow-launch-badge">Primary tool</span>
        <strong>{toolLabel}</strong>
      </div>
    </motion.section>
  );
}
