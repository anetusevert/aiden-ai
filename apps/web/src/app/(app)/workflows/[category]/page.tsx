'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
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
  glassReveal,
  glassBackdrop,
} from '@/lib/motion';

export default function WorkflowCategoryPage() {
  const params = useParams<{ category: string }>();
  const { navigateTo } = useNavigation();
  const category = params.category as WorkflowCategory;
  const [showCreateModal, setShowCreateModal] = useState(false);

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
      {/* Compact inline header */}
      <section
        className="wf-hub-header"
        style={{ '--workflow-accent': accent } as React.CSSProperties}
      >
        <div className="wf-hub-header-row">
          <div className="wf-hub-header-icon">
            {renderCategoryIcon(category, 22)}
          </div>
          <div className="wf-hub-header-meta">
            <h1 className="wf-hub-header-title">
              {getCategoryDisplayName(category)}
            </h1>
            <span className="wf-hub-header-count">
              {workflows.length} workflow{workflows.length !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
        <p className="wf-hub-header-sub">
          Structured tasks guided by Amin — source the right workspace and move
          each matter into the correct execution path.
        </p>
      </section>

      {/* Workflow cards */}
      <motion.section
        className="wf-hub-grid"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {workflows.map(workflow => (
          <motion.button
            key={workflow.id}
            type="button"
            className="wf-hub-card"
            style={{ '--workflow-accent': accent } as React.CSSProperties}
            variants={staggerItem}
            onClick={() => navigateTo(getWorkflowHref(workflow))}
          >
            <div className="wf-hub-card-body">
              <h2 className="wf-hub-card-title">{workflow.name}</h2>
              <p className="wf-hub-card-desc">{workflow.description}</p>
            </div>
            <div className="wf-hub-card-meta">
              <span className="wf-hub-pill">{workflow.steps.length} steps</span>
              <span className="wf-hub-pill">
                {getToolLabel(workflow.route)}
              </span>
              <span className="wf-hub-card-open">Open &rarr;</span>
            </div>
          </motion.button>
        ))}

        {/* Create Workflow placeholder */}
        <motion.button
          type="button"
          className="wf-hub-card wf-create-card"
          variants={staggerItem}
          onClick={() => setShowCreateModal(true)}
        >
          <div className="wf-create-icon">+</div>
          <span className="wf-create-label">Create Workflow</span>
        </motion.button>
      </motion.section>

      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            className="modal-backdrop"
            {...glassBackdrop}
            onClick={() => setShowCreateModal(false)}
          >
            <motion.div
              className="modal-content"
              {...glassReveal}
              onClick={e => e.stopPropagation()}
              style={{ maxWidth: 420 }}
            >
              <div className="modal-header">
                <h2>Create Workflow</h2>
                <button
                  type="button"
                  className="modal-close"
                  onClick={() => setShowCreateModal(false)}
                >
                  &times;
                </button>
              </div>
              <div
                className="modal-body"
                style={{ textAlign: 'center', padding: '2rem 1.5rem' }}
              >
                <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  Custom workflow creation is coming soon. You will be able to
                  define your own multi-step workflows, assign tools, and share
                  them across your practice.
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
