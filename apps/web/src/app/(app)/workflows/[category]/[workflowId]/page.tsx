'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { AminAvatar } from '@/components/amin/AminAvatar';
import {
  getCategoryMeta,
  getWorkflowById,
  getWorkflowDisplayName,
  getWorkflowEstimatedDuration,
  getWorkflowJourneySteps,
  hasWorkflowTemplate,
} from '@/lib/workflowRegistry';
import { getWorkflowExecuteHref } from '@/lib/workflowPresentation';
import { aminEntrance } from '@/lib/motion';
import { reportScreenContext } from '@/lib/screenContext';

const stepFlowVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const stepNodeVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.22,
      ease: 'easeOut',
    },
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

export default function WorkflowDetailPage() {
  const params = useParams<{ category: string; workflowId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const workflow = useMemo(
    () => getWorkflowById(params.workflowId),
    [params.workflowId]
  );
  const workflowSteps = useMemo(
    () => getWorkflowJourneySteps(workflow),
    [workflow]
  );
  const categoryMeta = getCategoryMeta(params.category as never);
  const caseId = searchParams.get('case');
  const [aminState, setAminState] = useState<'speaking' | 'idle'>('speaking');
  const [typedBrief, setTypedBrief] = useState('');
  const [launching, setLaunching] = useState(false);
  const [prefill, setPrefill] = useState<Record<string, string>>({});

  const workflowName = getWorkflowDisplayName(workflow);
  const workflowDuration = getWorkflowEstimatedDuration(workflow);
  const aminBrief = useMemo(() => {
    if (!workflow) return '';
    return `I'll be guiding you through each step. ${workflow.description} This takes ${workflowDuration}.`;
  }, [workflow, workflowDuration]);

  useEffect(() => {
    const timer = window.setTimeout(() => setAminState('idle'), 2500);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!workflow || !categoryMeta) return;

    setTypedBrief('');
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setTypedBrief(aminBrief.slice(0, index));
      if (index >= aminBrief.length) {
        window.clearInterval(timer);
      }
    }, 28);

    reportScreenContext({
      route: `/workflows/${workflow.category}/${workflow.id}`,
      page_title: `${workflowName} Launch`,
      document: null,
      ui_state: {
        page: 'workflow_launch',
        workflowId: workflow.id,
        category: workflow.category,
        currentStep: null,
        totalSteps: workflowSteps.length,
        stepName: null,
        caseId,
      },
    });

    window.dispatchEvent(
      new CustomEvent('amin:proactive', {
        detail: {
          workflowId: workflow.id,
          message: `I'm ready to help you with "${workflowName}". ${workflow.description}. When you're ready, press Begin and I'll guide you through each step.`,
        },
      })
    );

    return () => window.clearInterval(timer);
  }, [
    aminBrief,
    caseId,
    categoryMeta,
    workflow,
    workflowName,
    workflowSteps.length,
  ]);

  if (!workflow || workflow.category !== params.category || !categoryMeta) {
    return (
      <div className="workflow-empty-state">
        <h1 className="page-title">Workflow not found</h1>
        <p className="page-subtitle">
          The requested workflow could not be matched to this practice area.
        </p>
      </div>
    );
  }

  const executeHref = getWorkflowExecuteHref(workflow);

  const buildExecuteHref = (useTemplate = false) => {
    const query = new URLSearchParams();
    if (caseId) query.set('case', caseId);
    if (useTemplate) query.set('template', '1');
    Object.entries(prefill).forEach(([key, value]) => {
      if (value.trim()) query.set(key, value.trim());
    });
    return query.toString()
      ? `${executeHref}?${query.toString()}`
      : executeHref;
  };

  const handleBegin = () => {
    setLaunching(true);
    window.setTimeout(() => {
      router.push(buildExecuteHref(false));
    }, 300);
  };

  const renderPrefillFields = () => {
    if (workflow.id === 'RESEARCH_LEGAL_MEMO') {
      return (
        <div className="workflow-launch-fields">
          <div className="form-group">
            <label className="form-label">Research question</label>
            <textarea
              className="form-textarea workflow-launch-textarea"
              rows={3}
              value={prefill.query ?? ''}
              onChange={event =>
                setPrefill(current => ({
                  ...current,
                  query: event.target.value,
                }))
              }
              placeholder="Summarize the legal issue Amin should research."
            />
          </div>
          <div className="form-group">
            <label className="form-label">Jurisdiction</label>
            <select
              className="form-select"
              value={prefill.jurisdiction ?? 'KSA'}
              onChange={event =>
                setPrefill(current => ({
                  ...current,
                  jurisdiction: event.target.value,
                }))
              }
            >
              <option value="KSA">KSA</option>
              <option value="UAE">UAE</option>
              <option value="Qatar">Qatar</option>
            </select>
          </div>
        </div>
      );
    }

    if (workflow.id === 'ARBITRATION_CLAUSE') {
      return (
        <div className="workflow-launch-fields">
          <div className="form-group">
            <label className="form-label">Clause type</label>
            <select
              className="form-select"
              value={prefill.clauseType ?? 'liability'}
              onChange={event =>
                setPrefill(current => ({
                  ...current,
                  clauseType: event.target.value,
                }))
              }
            >
              <option value="liability">Liability</option>
              <option value="indemnity">Indemnity</option>
              <option value="termination">Termination</option>
              <option value="payment">Payment</option>
              <option value="confidentiality">Confidentiality</option>
              <option value="governing_law">Governing Law</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Target jurisdiction</label>
            <select
              className="form-select"
              value={prefill.jurisdiction ?? 'KSA'}
              onChange={event =>
                setPrefill(current => ({
                  ...current,
                  jurisdiction: event.target.value,
                }))
              }
            >
              <option value="KSA">KSA</option>
              <option value="UAE">UAE</option>
              <option value="Qatar">Qatar</option>
            </select>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="workflow-launch-screen">
      <div className="workflow-breadcrumb">
        <button type="button" onClick={() => router.push('/workflows')}>
          Workflows
        </button>
        <ChevronRight />
        <button
          type="button"
          onClick={() => router.push(`/workflows/${workflow.category}`)}
        >
          {categoryMeta.name}
        </button>
        <ChevronRight />
        <span>{workflowName}</span>
      </div>

      <div className="workflow-launch-layout">
        <section className="workflow-launch-brief">
          <span className="workflow-page-kicker">Workflow Brief</span>
          <h1 className="workflow-launch-title">{workflowName}</h1>
          <p className="workflow-launch-description">{workflow.description}</p>

          <div className="workflow-launch-section">
            <div className="workflow-launch-section-head">
              <span>What happens</span>
              <span>{workflowSteps.length} steps</span>
            </div>

            <div className="workflow-step-flow-shell">
              <svg
                className="workflow-step-flow-line"
                viewBox="0 0 100 4"
                preserveAspectRatio="none"
              >
                <line
                  x1="3"
                  y1="2"
                  x2="97"
                  y2="2"
                  stroke="rgba(255,255,255,0.12)"
                  strokeWidth="1.2"
                  strokeDasharray="5 5"
                />
              </svg>

              <motion.div
                className="workflow-step-flow"
                variants={stepFlowVariants}
                initial="hidden"
                animate="visible"
              >
                {workflowSteps.map(step => (
                  <motion.div
                    key={step.order}
                    className="workflow-step-node"
                    variants={stepNodeVariants}
                  >
                    <span className="workflow-step-node-circle">
                      {step.order}
                    </span>
                    <span className="workflow-step-node-label">
                      {step.name}
                    </span>
                  </motion.div>
                ))}
              </motion.div>
            </div>
          </div>

          {renderPrefillFields()}

          <div className="workflow-launch-actions">
            <button
              type="button"
              className="workflow-begin-button"
              onClick={handleBegin}
              disabled={launching}
            >
              {launching ? (
                <>
                  <span className="spinner spinner-sm" />
                  Preparing workflow
                </>
              ) : (
                'Begin Workflow'
              )}
            </button>

            {hasWorkflowTemplate(workflow) ? (
              <button
                type="button"
                className="workflow-template-button"
                onClick={() => router.push(buildExecuteHref(true))}
              >
                Use Template
              </button>
            ) : null}
          </div>
        </section>

        <motion.aside className="workflow-launch-amin" {...aminEntrance}>
          <div className="workflow-launch-amin-avatar">
            <AminAvatar
              size={72}
              state={aminState}
              showWaveform={aminState === 'speaking'}
            />
          </div>
          <div className="workflow-launch-amin-copy">
            <span className="workflow-page-kicker">Amin Brief</span>
            <p>{typedBrief}</p>
          </div>
          <div className="workflow-launch-meta-card">
            <span>Recent runs</span>
            <strong>None yet</strong>
          </div>
        </motion.aside>
      </div>
    </div>
  );
}
