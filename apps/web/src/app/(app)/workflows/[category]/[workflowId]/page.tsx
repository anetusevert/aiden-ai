'use client';

import { useMemo, useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { getWorkflowById } from '@/lib/workflowRegistry';
import {
  WORKFLOW_CATEGORY_ACCENTS,
  getCategoryDisplayName,
  getToolLabel,
  getWorkflowExecuteHref,
  renderCategoryIcon,
} from '@/lib/workflowPresentation';
import {
  fadeUp,
  staggerContainer,
  staggerItem,
  tileMotion,
} from '@/lib/motion';

export default function WorkflowDetailPage() {
  const params = useParams<{ category: string; workflowId: string }>();
  const searchParams = useSearchParams();
  const { navigateTo } = useNavigation();
  const [activeCase, setActiveCase] = useState<{
    case_id: string;
    case_title: string;
    client_name: string;
  } | null>(null);

  const caseIdParam = searchParams.get('case');

  useEffect(() => {
    if (caseIdParam) {
      fetch(`/api/v1/cases/${caseIdParam}`, { credentials: 'include' })
        .then(r => (r.ok ? r.json() : null))
        .then(data => {
          if (data)
            setActiveCase({
              case_id: data.id,
              case_title: data.title,
              client_name: data.client?.display_name ?? '',
            });
        })
        .catch(() => {});
    } else {
      fetch('/api/v1/cases/active', { credentials: 'include' })
        .then(r => (r.ok ? r.json() : null))
        .then(data => {
          if (data) setActiveCase(data);
        })
        .catch(() => {});
    }
  }, [caseIdParam]);

  const workflow = useMemo(
    () => getWorkflowById(params.workflowId),
    [params.workflowId]
  );

  if (!workflow || workflow.category !== params.category) {
    return (
      <div className="workflow-empty-state">
        <h1 className="page-title">Workflow not found</h1>
        <p className="page-subtitle">
          The requested workflow could not be matched to this practice area.
        </p>
      </div>
    );
  }

  const accent = WORKFLOW_CATEGORY_ACCENTS[workflow.category];
  const baseLaunchHref = getWorkflowExecuteHref(workflow);
  const launchHref = activeCase
    ? `${baseLaunchHref}${baseLaunchHref.includes('?') ? '&' : '?'}case=${activeCase.case_id}`
    : baseLaunchHref;

  return (
    <motion.div className="workflow-detail-page" {...fadeUp}>
      {activeCase && (
        <div
          className="exec-case-banner"
          style={{ margin: '0 0 var(--space-2) 0' }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <rect x="2" y="7" width="20" height="14" rx="2" />
            <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
          </svg>
          <span>
            Case: <strong>{activeCase.case_title}</strong> |{' '}
            {activeCase.client_name}
          </span>
        </div>
      )}
      <section
        className="workflow-detail-hero wf-detail-compact"
        style={{ '--workflow-accent': accent } as React.CSSProperties}
      >
        <div className="workflow-detail-hero-top">
          <span className="workflow-detail-icon">
            {renderCategoryIcon(workflow.category, 20)}
          </span>
          <span className="workflow-detail-category">
            {getCategoryDisplayName(workflow.category)}
          </span>
        </div>

        <h1 className="workflow-detail-title">{workflow.name}</h1>
        <p className="workflow-detail-description">{workflow.description}</p>

        <div className="workflow-detail-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => navigateTo(launchHref)}
          >
            Start workflow{activeCase ? ` for ${activeCase.case_title}` : ''}
          </button>
          {workflow.tools.map(tool => (
            <button
              key={tool}
              type="button"
              className="btn btn-outline"
              onClick={() =>
                navigateTo(
                  `${tool}?workflow=${workflow.id}&category=${workflow.category}`
                )
              }
            >
              Open {getToolLabel(tool)}
            </button>
          ))}
        </div>
      </section>

      <section className="workflow-detail-layout">
        <div className="workflow-detail-panel">
          <div className="workflow-detail-panel-header">
            <h2>Flow overview</h2>
            <span>{workflow.steps.length} stages</span>
          </div>

          <motion.div
            className="workflow-step-list"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {workflow.steps.map(step => (
              <motion.div
                key={step.order}
                className="workflow-step-card"
                variants={staggerItem}
              >
                <div className="workflow-step-number">{step.order}</div>
                <div className="workflow-step-copy">
                  <h3>{step.name}</h3>
                  <p>{step.detail}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>

        <div className="workflow-detail-sidepanel">
          <motion.div
            className="workflow-side-card"
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
          >
            <span className="workflow-side-kicker">Primary launch</span>
            <h3>{getToolLabel(workflow.route)}</h3>
            <p>
              Amin will prepare the most relevant workspace first, then you can
              branch into the other supporting tools.
            </p>
          </motion.div>

          <motion.div
            className="workflow-side-card"
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
          >
            <span className="workflow-side-kicker">Supporting tools</span>
            <div className="workflow-tool-pill-list">
              {workflow.tools.map(tool => (
                <span key={tool} className="workflow-tool-pill">
                  {getToolLabel(tool)}
                </span>
              ))}
            </div>
          </motion.div>

          <motion.div
            className="workflow-side-card workflow-side-card-cta"
            whileHover={tileMotion.hover}
            whileTap={tileMotion.tap}
          >
            <span className="workflow-side-kicker">Amin prompt</span>
            <p>
              “Prepare this workflow, identify the first required inputs, and
              guide me through the next step.”
            </p>
          </motion.div>
        </div>
      </section>
    </motion.div>
  );
}
