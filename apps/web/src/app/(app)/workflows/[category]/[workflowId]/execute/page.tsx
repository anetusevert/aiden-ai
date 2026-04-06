'use client';

import {
  useState,
  useEffect,
  useCallback,
  useMemo,
  useRef,
  type ReactNode,
} from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigation } from '@/components/NavigationLoader';
import { useAminContext } from '@/components/amin/AminProvider';
import { CollaboraEditor } from '@/components/office/CollaboraEditor';
import {
  getWorkflowById,
  type WorkflowDefinition,
  type WorkflowStep,
  type WorkflowCategory,
} from '@/lib/workflowRegistry';
import {
  WORKFLOW_CATEGORY_ACCENTS,
  WORKFLOW_TEMPLATE_MAP,
  getCategoryDisplayName,
  getWorkflowHref,
  renderCategoryIcon,
} from '@/lib/workflowPresentation';
import { apiClient, type LegalResearchResponse } from '@/lib/apiClient';
import { officeApi, type OfficeDocument } from '@/lib/officeApi';
import { reportScreenContext } from '@/lib/screenContext';
import {
  GroupedEvidenceList,
  renderCitationsWithDifferentiation,
} from '@/components/EvidenceCard';
import { toEvidenceItemFromChunk } from '@/lib/evidence';
import { WorkflowStatusBadge } from '@/components/WorkflowStatusBadge';
import {
  motionTokens,
  glassReveal,
  glassBackdrop,
  staggerContainer,
  staggerItem,
} from '@/lib/motion';
import { AminAvatar } from '@/components/amin/AminAvatar';
import { useAminAvatarState } from '@/hooks/useAminAvatarState';

// ============================================================================
// Types
// ============================================================================

type StepType = 'research' | 'document' | 'review' | 'guidance';

interface WorkflowSession {
  workflowId: string;
  currentStep: number;
  completedSteps: number[];
  attachedDocId: string | null;
  startedAt: string;
  notes: Record<number, string>;
  checkedItems: Record<number, boolean[]>;
}

// ============================================================================
// Step type classification
// ============================================================================

const RESEARCH_KEYWORDS =
  /\b(research|analyse|analyze|identify|assess|due\s+diligence|analysis|investigate|jurisdictional\s+analysis)\b/i;
const DOCUMENT_KEYWORDS =
  /\b(draft|prepare|document|filing|submit|create|template|articles|registration|statement\s+of\s+claim|memorandum|notari)\b/i;
const REVIEW_KEYWORDS =
  /\b(review|check|verify|validate|examine|sharia.*review|regulatory\s+review|screen)\b/i;

function classifyStepType(
  step: WorkflowStep,
  workflow: WorkflowDefinition
): StepType {
  const text = `${step.name} ${step.detail}`;

  if (
    REVIEW_KEYWORDS.test(text) &&
    workflow.tools.includes('/contract-review')
  ) {
    return 'review';
  }
  if (RESEARCH_KEYWORDS.test(text)) return 'research';
  if (DOCUMENT_KEYWORDS.test(text)) return 'document';
  return 'guidance';
}

// ============================================================================
// Session persistence hook
// ============================================================================

/** Bump version to drop stale localStorage after backend/schema fixes (no manual clear). */
const WORKFLOW_EXEC_STORAGE_VERSION = 'v2';

function getSessionKey(workflowId: string) {
  return `exec_session_${WORKFLOW_EXEC_STORAGE_VERSION}_${workflowId}`;
}

function getDocKey(workflowId: string) {
  return `exec_doc_${WORKFLOW_EXEC_STORAGE_VERSION}_${workflowId}`;
}

function useWorkflowSession(workflowId: string, totalSteps: number) {
  const [session, setSession] = useState<WorkflowSession>(() => {
    if (typeof window === 'undefined') {
      return createFreshSession(workflowId);
    }
    try {
      const stored = localStorage.getItem(getSessionKey(workflowId));
      if (stored) return JSON.parse(stored) as WorkflowSession;
    } catch {
      /* ignore */
    }
    return createFreshSession(workflowId);
  });

  const [showCompletion, setShowCompletion] = useState(false);

  const persist = useCallback(
    (next: WorkflowSession) => {
      setSession(next);
      try {
        localStorage.setItem(getSessionKey(workflowId), JSON.stringify(next));
      } catch {
        /* quota */
      }
    },
    [workflowId]
  );

  const advanceStep = useCallback(() => {
    setSession(prev => {
      const completed = prev.completedSteps.includes(prev.currentStep)
        ? prev.completedSteps
        : [...prev.completedSteps, prev.currentStep];

      if (prev.currentStep >= totalSteps - 1) {
        try {
          localStorage.removeItem(getSessionKey(workflowId));
          localStorage.removeItem(getDocKey(workflowId));
        } catch {
          /* ignore */
        }
        setShowCompletion(true);
        return { ...prev, completedSteps: completed };
      }

      const next: WorkflowSession = {
        ...prev,
        currentStep: prev.currentStep + 1,
        completedSteps: completed,
      };
      try {
        localStorage.setItem(getSessionKey(workflowId), JSON.stringify(next));
      } catch {
        /* quota */
      }
      return next;
    });
  }, [totalSteps, workflowId]);

  const goToStep = useCallback(
    (stepIndex: number) => {
      persist({ ...session, currentStep: stepIndex });
    },
    [persist, session]
  );

  const setAttachedDoc = useCallback(
    (docId: string) => {
      const next = { ...session, attachedDocId: docId };
      persist(next);
      try {
        localStorage.setItem(getDocKey(workflowId), docId);
      } catch {
        /* quota */
      }
    },
    [persist, session, workflowId]
  );

  return {
    ...session,
    showCompletion,
    setShowCompletion,
    advanceStep,
    goToStep,
    setAttachedDoc,
  };
}

function createFreshSession(workflowId: string): WorkflowSession {
  return {
    workflowId,
    currentStep: 0,
    completedSteps: [],
    attachedDocId: null,
    startedAt: new Date().toISOString(),
    notes: {},
    checkedItems: {},
  };
}

// ============================================================================
// Utility helpers
// ============================================================================

function extractSubTasks(detail: string, max = 5): string[] {
  return detail
    .split(/\.\s+/)
    .map(s => s.trim().replace(/\.$/, ''))
    .filter(s => s.length > 10)
    .slice(0, max);
}

function extractPrompts(detail: string): string[] {
  const sentences = detail
    .split(/\.\s+/)
    .map(s => s.trim().replace(/\.$/, ''))
    .filter(s => s.length > 10);

  return sentences.slice(0, 3).map(s => `Help me with: ${s}`);
}

function suggestResearchQuestion(step: WorkflowStep): string {
  return `What are the key legal requirements and considerations for: ${step.name}? Context: ${step.detail}`;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

// ============================================================================
// Step transition animation variants
// ============================================================================

const stepTransition = {
  initial: { x: 20, opacity: 0 },
  animate: {
    x: 0,
    opacity: 1,
    transition: {
      duration: motionTokens.duration.slow,
      ease: motionTokens.ease,
    },
  },
  exit: {
    x: -20,
    opacity: 0,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

const railSlideIn = {
  initial: { x: -20, opacity: 0 },
  animate: {
    x: 0,
    opacity: 1,
    transition: {
      duration: motionTokens.duration.slow,
      ease: motionTokens.ease,
    },
  },
};

// ============================================================================
// StepRail
// ============================================================================

function StepRail({
  workflow,
  steps,
  currentStep,
  completedSteps,
  accent,
  onGoToStep,
  onExit,
}: {
  workflow: WorkflowDefinition;
  steps: WorkflowStep[];
  currentStep: number;
  completedSteps: number[];
  accent: string;
  onGoToStep: (idx: number) => void;
  onExit: () => void;
}) {
  const [shakingStep, setShakingStep] = useState<number | null>(null);

  const handleStepClick = (idx: number) => {
    if (completedSteps.includes(idx)) {
      onGoToStep(idx);
    } else if (idx !== currentStep) {
      setShakingStep(idx);
      setTimeout(() => setShakingStep(null), 500);
    }
  };

  const completedCount = completedSteps.length;
  const progress = (completedCount / steps.length) * 100;

  return (
    <motion.aside className="exec-rail" {...railSlideIn}>
      <button className="exec-rail-exit" onClick={onExit} type="button">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
        Exit
      </button>

      <span className="exec-rail-title">{workflow.name}</span>
      <div className="exec-rail-divider" />

      <motion.div
        className="exec-rail-steps"
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
      >
        {steps.map((step, idx) => {
          const isCompleted = completedSteps.includes(idx);
          const isActive = idx === currentStep;
          const isUpcoming = !isCompleted && !isActive;
          const isShaking = shakingStep === idx;

          return (
            <motion.div key={step.order} variants={staggerItem}>
              {idx > 0 && (
                <div
                  className="exec-rail-line"
                  style={{
                    backgroundColor: completedSteps.includes(idx - 1)
                      ? accent
                      : 'rgba(255,255,255,0.1)',
                  }}
                />
              )}
              <button
                type="button"
                className={`exec-rail-step ${isShaking ? 'exec-rail-step--shake' : ''}`}
                data-state={
                  isCompleted ? 'completed' : isActive ? 'active' : 'upcoming'
                }
                onClick={() => handleStepClick(idx)}
              >
                <span
                  className="exec-rail-indicator"
                  style={
                    isCompleted
                      ? { backgroundColor: accent, borderColor: accent }
                      : isActive
                        ? { borderColor: 'rgba(255,255,255,0.9)' }
                        : undefined
                  }
                >
                  {isCompleted && (
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#fff"
                      strokeWidth="3"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </span>
                <span className="exec-rail-label">{step.name}</span>
              </button>
            </motion.div>
          );
        })}
      </motion.div>

      <div className="exec-rail-footer">
        <div className="exec-rail-progress">
          <div
            className="exec-rail-progress-fill"
            style={{ width: `${progress}%`, backgroundColor: accent }}
          />
        </div>
        <span className="exec-rail-progress-text">
          {completedCount} of {steps.length} complete
        </span>
      </div>
    </motion.aside>
  );
}

// ============================================================================
// StepTopBar
// ============================================================================

function StepTopBar({
  stepNumber,
  totalSteps,
  stepName,
  canAdvance,
  isLastStep,
  onAdvance,
}: {
  stepNumber: number;
  totalSteps: number;
  stepName: string;
  canAdvance: boolean;
  isLastStep: boolean;
  onAdvance: () => void;
}) {
  return (
    <div className="exec-topbar">
      <div className="exec-topbar-left">
        <span className="exec-topbar-counter">
          Step {stepNumber} of {totalSteps}
        </span>
        <span className="exec-topbar-name">{stepName}</span>
      </div>
      <button
        type="button"
        className={`exec-topbar-advance ${canAdvance ? '' : 'exec-topbar-advance--disabled'}`}
        disabled={!canAdvance}
        onClick={onAdvance}
        title={
          canAdvance ? undefined : 'Complete the step below before advancing'
        }
      >
        {isLastStep ? 'Complete Workflow' : 'Mark Step Complete'} →
      </button>
    </div>
  );
}

// ============================================================================
// ResearchStepContent
// ============================================================================

function ResearchStepContent({
  step,
  onComplete,
}: {
  step: WorkflowStep;
  onComplete: () => void;
}) {
  const [question, setQuestion] = useState(() => suggestResearchQuestion(step));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LegalResearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await apiClient.legalResearch({
        question,
        limit: 10,
        output_language: 'en',
        evidence_scope: 'both',
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="exec-research">
      <div className="exec-research-banner">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        Researching: {step.name}
      </div>

      <form onSubmit={handleSubmit} className="exec-research-form">
        <textarea
          className="exec-research-textarea"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="Enter your research question..."
          rows={3}
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || !question.trim()}
        >
          {loading ? (
            <>
              <span className="spinner spinner-sm" /> Researching...
            </>
          ) : (
            'Submit Research'
          )}
        </button>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && !result && (
        <div className="exec-research-loading">
          <span className="spinner spinner-lg" />
          <p>Analyzing documents and generating cited answer...</p>
        </div>
      )}

      {result && (
        <div className="exec-research-results">
          <div className="exec-research-results-header">
            <h3>Research Results</h3>
            <WorkflowStatusBadge status={result.meta.status} />
          </div>

          <div className="workflow-answer">
            <div className="workflow-answer-text">
              {renderCitationsWithDifferentiation(result.answer_text, {})}
            </div>
          </div>

          {result.evidence.length > 0 && (
            <div className="exec-research-evidence">
              <h4>Evidence ({result.evidence.length})</h4>
              <GroupedEvidenceList
                evidence={result.evidence.map(toEvidenceItemFromChunk)}
                maxItemsPerSection={5}
                showGlobalLawBanner={true}
                showMore={true}
              />
            </div>
          )}

          <button
            type="button"
            className="btn btn-primary"
            onClick={onComplete}
            style={{ marginTop: 'var(--space-4)' }}
          >
            Research complete — mark step done
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// DocumentStepContent
// ============================================================================

function DocumentStepContent({
  step,
  workflow,
  attachedDocId,
  onDocAttached,
  isFirstStep,
}: {
  step: WorkflowStep;
  workflow: WorkflowDefinition;
  attachedDocId: string | null;
  onDocAttached: (docId: string) => void;
  isFirstStep: boolean;
}) {
  const [docId, setDocId] = useState<string | null>(attachedDocId);
  const [creating, setCreating] = useState(false);
  const [showEditor, setShowEditor] = useState(!!attachedDocId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const autoCreated = useRef(false);

  const templateConfig = WORKFLOW_TEMPLATE_MAP[workflow.id] ?? {
    title: `${workflow.name} — ${step.name}`,
    doc_type: 'docx' as const,
  };

  const createDocument = useCallback(async () => {
    setCreating(true);
    try {
      const doc = await officeApi.createDocument({
        title: templateConfig.title,
        doc_type: templateConfig.doc_type,
        template: templateConfig.template,
      });
      setDocId(doc.id);
      onDocAttached(doc.id);
      setShowEditor(true);
    } catch {
      /* toast would go here */
    } finally {
      setCreating(false);
    }
  }, [onDocAttached, templateConfig]);

  useEffect(() => {
    if (isFirstStep && !docId && !autoCreated.current) {
      autoCreated.current = true;
      void createDocument();
    }
  }, [isFirstStep, docId, createDocument]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    /* For MVP, create a doc then attach the file via the standard upload flow */
    await createDocument();
  };

  if (showEditor && docId) {
    return (
      <div className="exec-document">
        <CollaboraEditor
          docId={docId}
          title={templateConfig.title}
          docType={templateConfig.doc_type}
        />
      </div>
    );
  }

  return (
    <div className="exec-document">
      <div className="exec-document-choices">
        <button
          type="button"
          className="exec-document-card"
          onClick={createDocument}
          disabled={creating}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <line x1="9" y1="15" x2="15" y2="15" />
          </svg>
          <strong>{creating ? 'Creating...' : 'Open Collabora Editor'}</strong>
          <span>Create a new document with the appropriate template</span>
        </button>

        <button
          type="button"
          className="exec-document-card"
          onClick={() => fileInputRef.current?.click()}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <strong>Upload Existing Document</strong>
          <span>Attach a document you have already prepared</span>
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept=".docx,.xlsx,.pptx,.pdf"
          onChange={handleUpload}
          style={{ display: 'none' }}
        />
      </div>
    </div>
  );
}

// ============================================================================
// ReviewStepContent
// ============================================================================

function ReviewStepContent({
  step,
  workflow,
  attachedDocId,
  onComplete,
}: {
  step: WorkflowStep;
  workflow: WorkflowDefinition;
  attachedDocId: string | null;
  onComplete: () => void;
}) {
  const isContractWorkflow = workflow.tools.includes('/contract-review');

  if (isContractWorkflow && attachedDocId) {
    return (
      <div className="exec-guidance">
        <div className="exec-guidance-objective">
          <h3>Contract Review: {step.name}</h3>
          <p>{step.detail}</p>
        </div>
        <div className="exec-guidance-actions">
          <a
            href={`/contract-review?docId=${attachedDocId}&workflow=${workflow.id}`}
            className="btn btn-primary"
            target="_blank"
            rel="noopener noreferrer"
          >
            Open Contract Review Tool
          </a>
          <button
            type="button"
            className="btn btn-outline"
            onClick={onComplete}
          >
            Mark review complete
          </button>
        </div>
      </div>
    );
  }

  return <GuidanceStepContent step={step} onComplete={onComplete} />;
}

// ============================================================================
// GuidanceStepContent
// ============================================================================

function GuidanceStepContent({
  step,
  onComplete,
}: {
  step: WorkflowStep;
  onComplete: () => void;
}) {
  const { openPanel, sendMessage } = useAminContext();
  const prompts = useMemo(() => extractPrompts(step.detail), [step.detail]);
  const subTasks = useMemo(() => extractSubTasks(step.detail), [step.detail]);
  const [checked, setChecked] = useState<boolean[]>(() =>
    new Array(subTasks.length).fill(false)
  );

  const allChecked = subTasks.length > 0 && checked.every(Boolean);

  const toggleCheck = (idx: number) => {
    setChecked(prev => {
      const next = [...prev];
      next[idx] = !next[idx];
      return next;
    });
  };

  const handlePromptClick = (text: string) => {
    openPanel();
    sendMessage(text);
  };

  return (
    <div className="exec-guidance">
      <div className="exec-guidance-objective">
        <h3>{step.name}</h3>
        <p>{step.detail}</p>
      </div>

      {prompts.length > 0 && (
        <div className="exec-guidance-prompts">
          <span className="exec-guidance-prompts-label">Ask Amin</span>
          {prompts.map((prompt, i) => (
            <button
              key={i}
              type="button"
              className="exec-guidance-prompt"
              onClick={() => handlePromptClick(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      <button
        type="button"
        className="btn btn-outline exec-guidance-open-amin"
        onClick={openPanel}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        Open Amin
      </button>

      {subTasks.length > 0 && (
        <div className="exec-guidance-checklist">
          <span className="exec-guidance-checklist-label">Checklist</span>
          {subTasks.map((task, i) => (
            <label key={i} className="exec-guidance-check-item">
              <input
                type="checkbox"
                checked={checked[i]}
                onChange={() => toggleCheck(i)}
              />
              <span>{task}</span>
            </label>
          ))}
        </div>
      )}

      {allChecked && (
        <motion.button
          type="button"
          className="btn btn-primary"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          onClick={onComplete}
          style={{ marginTop: 'var(--space-4)' }}
        >
          All tasks complete — mark step done
        </motion.button>
      )}
    </div>
  );
}

// ============================================================================
// CompletionModal
// ============================================================================

function CompletionModal({
  workflow,
  completedSteps,
  startedAt,
  attachedDocId,
  category,
  onClose,
}: {
  workflow: WorkflowDefinition;
  completedSteps: number[];
  startedAt: string;
  attachedDocId: string | null;
  category: string;
  onClose: () => void;
}) {
  const { navigateTo } = useNavigation();

  return (
    <motion.div className="exec-completion" {...glassBackdrop}>
      <motion.div className="exec-completion-card" {...glassReveal}>
        <svg
          className="exec-completion-check"
          width="80"
          height="80"
          viewBox="0 0 80 80"
          fill="none"
        >
          <circle
            cx="40"
            cy="40"
            r="36"
            stroke="rgba(255,255,255,0.9)"
            strokeWidth="3"
            opacity="0.3"
          />
          <path
            className="exec-completion-check-path"
            d="M24 42 L34 52 L56 30"
            stroke="rgba(255,255,255,0.9)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        </svg>

        <h2 className="exec-completion-title">Workflow Complete</h2>
        <p className="exec-completion-name">{workflow.name}</p>
        <p className="exec-completion-stats">
          {completedSteps.length} steps completed &middot; Started{' '}
          {relativeTime(startedAt)} ago
        </p>

        <div className="exec-completion-actions">
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => navigateTo(`/workflows/${category}`)}
          >
            ← Back to Workflows
          </button>
          {attachedDocId && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => navigateTo(`/documents/${attachedDocId}`)}
            >
              View Document
            </button>
          )}
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => navigateTo('/research')}
          >
            Start New Research
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ============================================================================
// Main Page Component
// ============================================================================

interface ActiveCaseInfo {
  case_id: string;
  case_title: string;
  client_name: string;
  practice_area: string;
}

export default function WorkflowExecutePage() {
  const params = useParams<{ category: string; workflowId: string }>();
  const searchParams = useSearchParams();
  const { navigateTo } = useNavigation();
  const [activeCase, setActiveCase] = useState<ActiveCaseInfo | null>(null);

  const aminAvatarState = useAminAvatarState();
  const category = params.category as WorkflowCategory;
  const workflowId = params.workflowId;

  const workflow = useMemo(() => getWorkflowById(workflowId), [workflowId]);

  const steps = workflow?.steps ?? [];
  const accent = WORKFLOW_CATEGORY_ACCENTS[category] ?? 'rgba(255,255,255,0.9)';

  const {
    currentStep,
    completedSteps,
    attachedDocId,
    startedAt,
    showCompletion,
    setShowCompletion,
    advanceStep,
    goToStep,
    setAttachedDoc,
  } = useWorkflowSession(workflowId, steps.length);

  // Fetch active case and set from URL param if present
  useEffect(() => {
    const caseIdParam = searchParams.get('case');
    if (caseIdParam) {
      fetch(`/api/v1/cases/${caseIdParam}/set-active`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {});
    }
    fetch('/api/v1/cases/active', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data) setActiveCase(data);
      })
      .catch(() => {});
  }, [searchParams]);

  // File step completion to case timeline
  const fileStepToCase = useCallback(
    (stepName: string) => {
      if (!activeCase) return;
      fetch(`/api/v1/cases/${activeCase.case_id}/notes`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: `Workflow step completed: ${stepName} in ${workflow?.name ?? workflowId}`,
          is_amin_generated: true,
        }),
      }).catch(() => {});
    },
    [activeCase, workflow?.name, workflowId]
  );

  // Hydrate docId from search params or localStorage
  useEffect(() => {
    if (attachedDocId) return;
    const fromUrl = searchParams.get('docId');
    if (fromUrl) {
      setAttachedDoc(fromUrl);
      return;
    }
    try {
      const stored = localStorage.getItem(getDocKey(workflowId));
      if (stored) setAttachedDoc(stored);
    } catch {
      /* ignore */
    }
  }, [attachedDocId, searchParams, setAttachedDoc, workflowId]);

  // Report screen context on every step change
  useEffect(() => {
    if (!workflow) return;
    const step = steps[currentStep];
    if (!step) return;

    reportScreenContext({
      route: `/workflows/${category}/${workflowId}/execute`,
      page_title: `Executing: ${workflow.name}`,
      document: attachedDocId
        ? {
            doc_id: attachedDocId,
            title: workflow.name,
            doc_type: 'docx',
            current_view: 'editor',
            current_page: null,
            current_slide: null,
            current_sheet: null,
          }
        : null,
      ui_state: {
        workflow_id: workflowId,
        workflow_name: workflow.name,
        category,
        current_step: currentStep + 1,
        current_step_name: step.name,
        current_step_detail: step.detail,
        completed_steps: completedSteps.length,
        total_steps: steps.length,
        attached_doc_id: attachedDocId,
      },
    });
  }, [
    workflow,
    currentStep,
    completedSteps,
    attachedDocId,
    category,
    workflowId,
    steps,
  ]);

  // Determine current step type and whether advance is allowed
  const currentStepDef = steps[currentStep];
  const stepType =
    currentStepDef && workflow
      ? classifyStepType(currentStepDef, workflow)
      : 'guidance';

  const handleAdvance = useCallback(() => {
    const stepName = steps[currentStep]?.name ?? `Step ${currentStep + 1}`;
    fileStepToCase(stepName);
    advanceStep();
  }, [advanceStep, currentStep, steps, fileStepToCase]);

  const canAdvance =
    completedSteps.includes(currentStep) ||
    stepType === 'research' ||
    stepType === 'document';
  const isLastStep = currentStep >= steps.length - 1;

  if (!workflow) {
    return (
      <div className="workflow-empty-state">
        <h1 className="page-title">Workflow not found</h1>
        <p className="page-subtitle">
          The requested workflow could not be loaded.
        </p>
      </div>
    );
  }

  const handleExit = () => {
    navigateTo(getWorkflowHref(workflow));
  };

  const renderStepContent = () => {
    if (!currentStepDef) return null;

    switch (stepType) {
      case 'research':
        return (
          <ResearchStepContent
            step={currentStepDef}
            onComplete={handleAdvance}
          />
        );
      case 'document':
        return (
          <DocumentStepContent
            step={currentStepDef}
            workflow={workflow}
            attachedDocId={attachedDocId}
            onDocAttached={setAttachedDoc}
            isFirstStep={currentStep === 0}
          />
        );
      case 'review':
        return (
          <ReviewStepContent
            step={currentStepDef}
            workflow={workflow}
            attachedDocId={attachedDocId}
            onComplete={handleAdvance}
          />
        );
      case 'guidance':
      default:
        return (
          <GuidanceStepContent
            step={currentStepDef}
            onComplete={handleAdvance}
          />
        );
    }
  };

  return (
    <div
      className="exec-canvas"
      style={{ '--workflow-accent': accent } as React.CSSProperties}
    >
      <StepRail
        workflow={workflow}
        steps={steps}
        currentStep={currentStep}
        completedSteps={completedSteps}
        accent={accent}
        onGoToStep={goToStep}
        onExit={handleExit}
      />

      <div className="exec-workspace">
        {activeCase && (
          <div className="exec-case-banner">
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
              Working on: <strong>{activeCase.case_title}</strong> |{' '}
              {activeCase.client_name}
            </span>
          </div>
        )}
        <div
          style={{
            position: 'absolute',
            top: activeCase ? 48 : 12,
            right: 16,
            zIndex: 10,
          }}
        >
          <AminAvatar size={40} state={aminAvatarState} showWaveform={false} />
        </div>
        <StepTopBar
          stepNumber={currentStep + 1}
          totalSteps={steps.length}
          stepName={currentStepDef?.name ?? ''}
          canAdvance={canAdvance}
          isLastStep={isLastStep}
          onAdvance={handleAdvance}
        />

        <div className="exec-content">
          <AnimatePresence mode="wait">
            <motion.div key={currentStep} {...stepTransition}>
              {renderStepContent()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {showCompletion && (
          <CompletionModal
            workflow={workflow}
            completedSteps={completedSteps}
            startedAt={startedAt}
            attachedDocId={attachedDocId}
            category={category}
            onClose={() => setShowCompletion(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
