'use client';

import { useMemo } from 'react';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import {
  WORKFLOW_REGISTRY,
  type WorkflowCategory,
} from '@/lib/workflowRegistry';
import {
  WORKFLOW_CATEGORY_ACCENTS,
  getCategoryDisplayName,
  getToolLabel,
  getWorkflowHref,
  renderCategoryIcon,
} from '@/lib/workflowPresentation';
import {
  fadeUp,
  staggerContainer,
  staggerItem,
  tileMotion,
} from '@/lib/motion';

export default function WorkflowCategoryPage() {
  const params = useParams<{ category: string }>();
  const { navigateTo } = useNavigation();
  const category = params.category as WorkflowCategory;

  const workflows = useMemo(
    () => WORKFLOW_REGISTRY.filter(workflow => workflow.category === category),
    [category]
  );

  if (workflows.length === 0) {
    return (
      <div className="workflow-empty-state">
        <h1 className="page-title">Workflow category not found</h1>
        <p className="page-subtitle">
          The requested practice area could not be loaded.
        </p>
      </div>
    );
  }

  const accent = WORKFLOW_CATEGORY_ACCENTS[category];
  return (
    <motion.div className="workflow-hub-page" {...fadeUp}>
      <section
        className="workflow-hub-hero"
        style={{ '--workflow-accent': accent } as React.CSSProperties}
      >
        <div className="workflow-hub-hero-icon">
          {renderCategoryIcon(category, 28)}
        </div>
        <div className="workflow-hub-hero-copy">
          <span className="workflow-hub-kicker">Practice area</span>
          <h1 className="workflow-hub-title">
            {getCategoryDisplayName(category)}
          </h1>
          <p className="workflow-hub-subtitle">
            Amin can guide lawyers through structured tasks, source the right
            workspace, and move each matter into the correct execution path.
          </p>
        </div>
        <div className="workflow-hub-hero-stat">
          <span>Available workflows</span>
          <strong>{workflows.length}</strong>
        </div>
      </section>

      <motion.section
        className="workflow-hub-grid"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {workflows.map(workflow => (
          <motion.button
            key={workflow.id}
            type="button"
            className="workflow-hub-card"
            style={{ '--workflow-accent': accent } as React.CSSProperties}
            variants={staggerItem}
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
            onClick={() => navigateTo(getWorkflowHref(workflow))}
          >
            <div className="workflow-hub-card-head">
              <span className="workflow-hub-card-icon">
                {renderCategoryIcon(workflow.category, 18)}
              </span>
              <span className="workflow-hub-card-tools">
                {getToolLabel(workflow.route)}
              </span>
            </div>
            <h2 className="workflow-hub-card-title">{workflow.name}</h2>
            <p className="workflow-hub-card-description">
              {workflow.description}
            </p>
            <div className="workflow-hub-card-footer">
              <span>{workflow.steps.length} steps</span>
              <span>Open workflow</span>
            </div>
          </motion.button>
        ))}
      </motion.section>
    </motion.div>
  );
}
