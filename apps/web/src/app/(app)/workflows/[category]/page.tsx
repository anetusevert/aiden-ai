'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  getCategoryMeta,
  getWorkflowsByCategory,
  type WorkflowCategory,
  getWorkflowDisplayName,
  getWorkflowEstimatedDuration,
  getWorkflowJourneySteps,
  isLiveWorkflow,
} from '@/lib/workflowRegistry';
import { getWorkflowHref } from '@/lib/workflowPresentation';
import { reportScreenContext } from '@/lib/screenContext';

const listVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.05,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.22, ease: 'easeOut' },
  },
};

function ChevronRight() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export default function WorkflowCategoryPage() {
  const params = useParams<{ category: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [pressedCard, setPressedCard] = useState<string | null>(null);

  const category = params.category as WorkflowCategory;
  const meta = getCategoryMeta(category);
  const workflows = useMemo(() => getWorkflowsByCategory(category), [category]);
  const caseId = searchParams.get('case');

  useEffect(() => {
    if (!meta) return;

    reportScreenContext({
      route: `/workflows/${category}`,
      page_title: `${meta.name} Workflows`,
      document: null,
      ui_state: {
        page: 'workflow_category',
        workflowId: null,
        category,
        currentStep: null,
        totalSteps: null,
        stepName: null,
        caseId,
      },
    });

    window.dispatchEvent(
      new CustomEvent('amin:context', {
        detail: {
          message: `You're browsing ${meta.name} workflows. ${workflows.length} available - the ones marked Live connect to real AI engines.`,
        },
      })
    );
  }, [category, caseId, meta, workflows.length]);

  if (!meta) {
    return (
      <div className="workflow-empty-state">
        <h1 className="page-title">Workflow category not found</h1>
        <p className="page-subtitle">
          The requested practice area could not be loaded.
        </p>
      </div>
    );
  }

  const handleOpenWorkflow = (workflowId: string) => {
    const href = `/workflows/${category}/${workflowId}${caseId ? `?case=${caseId}` : ''}`;
    setPressedCard(workflowId);
    window.setTimeout(() => {
      router.push(href);
      setPressedCard(null);
    }, 100);
  };

  return (
    <div className="workflow-category-screen">
      <div className="workflow-breadcrumb">
        <button type="button" onClick={() => router.push('/workflows')}>
          Workflows
        </button>
        <ChevronRight />
        <span>{meta.name}</span>
      </div>

      <div className="workflow-page-intro">
        <span className="workflow-page-kicker">{meta.name}</span>
        <h1 className="workflow-page-title">
          Choose the workflow Amin should prepare.
        </h1>
        <p className="workflow-page-subtitle">
          Launch directly into a guided flow with clear steps, timing, and live
          execution where available.
        </p>
      </div>

      <motion.div
        className="workflow-category-list"
        variants={listVariants}
        initial="hidden"
        animate="visible"
      >
        {workflows.map(workflow => (
          <motion.button
            key={workflow.id}
            type="button"
            variants={itemVariants}
            className="workflow-category-card"
            animate={
              pressedCard === workflow.id ? { scale: 0.98 } : { scale: 1 }
            }
            whileTap={{ scale: 0.98, transition: { duration: 0.1 } }}
            onClick={() => handleOpenWorkflow(workflow.id)}
          >
            <div className="workflow-category-card-top">
              <h2>{getWorkflowDisplayName(workflow)}</h2>
              {isLiveWorkflow(workflow) ? (
                <span className="workflow-live-badge">Live</span>
              ) : null}
            </div>
            <p>{workflow.description}</p>
            <div className="workflow-category-card-meta">
              <span>{getWorkflowEstimatedDuration(workflow)}</span>
              <span>{getWorkflowJourneySteps(workflow).length} steps</span>
            </div>
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}
