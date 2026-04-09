'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { motion, useAnimationFrame } from 'framer-motion';
import { AminAvatar } from '@/components/amin/AminAvatar';
import { StepRail } from '@/components/workflows/StepRail';
import { StepWorkspace } from '@/components/workflows/StepWorkspace';
import { WorkflowCompletion } from '@/components/workflows/WorkflowCompletion';
import {
  apiClient,
  type ClauseRedlinesResponse,
  type ContractReviewResponse,
  type LegalResearchResponse,
} from '@/lib/apiClient';
import { reportScreenContext } from '@/lib/screenContext';
import { runWorkflowSimulation } from '@/lib/workflowSimulator';
import {
  getWorkflowById,
  getWorkflowDisplayName,
  getWorkflowJourneySteps,
  getWorkflowSimulatedOutput,
  getWorkflowStepEstimate,
  getWorkflowStepMessage,
  isLiveWorkflow,
  type WorkflowCategory,
  type WorkflowSimulatedOutput,
} from '@/lib/workflowRegistry';

interface ActiveCaseInfo {
  case_id: string;
  case_title: string;
  client_name: string;
}

interface CaseListItem {
  id: string;
  title: string;
}

type AminState = 'idle' | 'thinking' | 'speaking' | 'success';

type StepResult =
  | { kind: 'research'; data: LegalResearchResponse }
  | { kind: 'contract'; data: ContractReviewResponse; score: number }
  | { kind: 'redlines'; data: ClauseRedlinesResponse; originalText: string }
  | { kind: 'simulated'; data: WorkflowSimulatedOutput }
  | { kind: 'text'; content: string };

function wait(ms: number) {
  return new Promise(resolve => window.setTimeout(resolve, ms));
}

function severityScore(severity: string): number {
  switch (severity) {
    case 'critical':
      return 95;
    case 'high':
      return 78;
    case 'medium':
      return 58;
    case 'low':
      return 28;
    default:
      return 12;
  }
}

function computeRiskScore(findings: ContractReviewResponse['findings']) {
  if (!findings.length) return 12;
  const total = findings.reduce(
    (sum, finding) => sum + severityScore(finding.severity),
    0
  );
  return Math.max(0, Math.min(100, Math.round(total / findings.length)));
}

function triggerDownload(
  filename: string,
  content: string,
  type = 'text/plain'
) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function buildFallbackSummary(
  workflowName: string,
  stepResults: Record<number, StepResult>
) {
  const completed = Object.keys(stepResults).length;
  return `${workflowName} completed successfully. ${completed} workflow stages were finished with Amin guiding each transition. The final outputs are ready to download or file into a case.`;
}

function tokenize(text: string) {
  return text.split(/(\s+)/).filter(Boolean);
}

function buildDiffSegments(original: string, updated: string) {
  const left = tokenize(original);
  const right = tokenize(updated);
  const dp = Array.from({ length: left.length + 1 }, () =>
    Array<number>(right.length + 1).fill(0)
  );

  for (let i = left.length - 1; i >= 0; i -= 1) {
    for (let j = right.length - 1; j >= 0; j -= 1) {
      dp[i][j] =
        left[i] === right[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const segments: Array<{ type: 'same' | 'insert' | 'delete'; text: string }> =
    [];

  const push = (type: 'same' | 'insert' | 'delete', text: string) => {
    const last = segments[segments.length - 1];
    if (last?.type === type) {
      last.text += text;
      return;
    }
    segments.push({ type, text });
  };

  let i = 0;
  let j = 0;

  while (i < left.length && j < right.length) {
    if (left[i] === right[j]) {
      push('same', left[i]);
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      push('delete', left[i]);
      i += 1;
    } else {
      push('insert', right[j]);
      j += 1;
    }
  }

  while (i < left.length) {
    push('delete', left[i]);
    i += 1;
  }

  while (j < right.length) {
    push('insert', right[j]);
    j += 1;
  }

  return segments;
}

export default function WorkflowExecutePage() {
  const params = useParams<{ category: string; workflowId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const canvasRef = useRef<HTMLDivElement | null>(null);

  const workflow = useMemo(
    () => getWorkflowById(params.workflowId),
    [params.workflowId]
  );
  const workflowId = params.workflowId;
  const category = params.category as WorkflowCategory;
  const steps = useMemo(() => getWorkflowJourneySteps(workflow), [workflow]);
  const workflowName = getWorkflowDisplayName(workflow);
  const isLive = isLiveWorkflow(workflow);
  const caseId = searchParams.get('case');

  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [stepResults, setStepResults] = useState<Record<number, StepResult>>(
    {}
  );
  const [running, setRunning] = useState(false);
  const [runProgress, setRunProgress] = useState(0);
  const [successFlash, setSuccessFlash] = useState(false);
  const [particleStep, setParticleStep] = useState<number | null>(null);
  const [aminState, setAminState] = useState<AminState>('idle');
  const [aminMessage, setAminMessage] = useState('');
  const [completionVisible, setCompletionVisible] = useState(false);
  const [completionSummary, setCompletionSummary] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [activeCase, setActiveCase] = useState<ActiveCaseInfo | null>(null);
  const [caseOptions, setCaseOptions] = useState<CaseListItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState(caseId ?? '');
  const [caseStatusLabel, setCaseStatusLabel] = useState<string | null>(null);

  const [researchQuery, setResearchQuery] = useState(
    searchParams.get('query') ?? ''
  );
  const [researchJurisdiction, setResearchJurisdiction] = useState(
    searchParams.get('jurisdiction') ?? 'KSA'
  );
  const [researchResult, setResearchResult] =
    useState<LegalResearchResponse | null>(null);

  const [uploadedContract, setUploadedContract] = useState<{
    fileName: string;
    size: number;
    documentId: string;
    versionId: string;
  } | null>(null);
  const [contractResult, setContractResult] = useState<{
    response: ContractReviewResponse;
    score: number;
  } | null>(null);

  const [clauseText, setClauseText] = useState('');
  const [clauseType, setClauseType] = useState(
    searchParams.get('clauseType') ?? 'liability'
  );
  const [clauseJurisdiction, setClauseJurisdiction] = useState(
    searchParams.get('jurisdiction') ?? 'KSA'
  );
  const [clauseResult, setClauseResult] = useState<{
    response: ClauseRedlinesResponse;
    originalText: string;
  } | null>(null);

  useAnimationFrame(time => {
    if (!canvasRef.current) return;
    const progress = (time % 30000) / 30000;
    const gx = 50 + Math.sin(progress * Math.PI * 2) * 35;
    const gy = 50 + Math.cos(progress * Math.PI * 2) * 35;
    canvasRef.current.style.setProperty('--gx', `${gx}%`);
    canvasRef.current.style.setProperty('--gy', `${gy}%`);
  });

  useEffect(() => {
    fetch('/api/v1/cases/active', { credentials: 'include' })
      .then(response => (response.ok ? response.json() : null))
      .then(data => {
        if (data) {
          setActiveCase(data);
          if (!caseId) {
            setSelectedCaseId(data.case_id);
          }
        }
      })
      .catch(() => {});

    fetch('/api/v1/cases?limit=50&offset=0', { credentials: 'include' })
      .then(response => (response.ok ? response.json() : null))
      .then(data => {
        const items = (data?.items ?? []) as Array<{
          id: string;
          title: string;
        }>;
        setCaseOptions(items.map(item => ({ id: item.id, title: item.title })));
      })
      .catch(() => {});
  }, [caseId]);

  useEffect(() => {
    const step = steps[currentStep];
    if (!workflow || !step) return;

    setAminMessage(getWorkflowStepMessage(workflow.id, currentStep));
    setAminState('speaking');

    const timer = window.setTimeout(() => {
      setAminState(current => (current === 'thinking' ? current : 'idle'));
    }, 1500);

    reportScreenContext({
      route: `/workflows/${category}/${workflow.id}/execute`,
      page_title: `${workflowName} Execute`,
      document: null,
      ui_state: {
        page: 'workflow_execute',
        workflowId: workflow.id,
        category,
        currentStep,
        totalSteps: steps.length,
        stepName: step.name,
        caseId: selectedCaseId || null,
      },
    });

    return () => window.clearTimeout(timer);
  }, [category, currentStep, selectedCaseId, steps, workflow, workflowName]);

  useEffect(() => {
    if (!completionVisible || !workflow || completionSummary || summaryLoading)
      return;

    setSummaryLoading(true);
    setAminState('success');
    setAminMessage('Workflow complete. I am preparing the final summary.');

    fetch('/api/v1/agent/message', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message:
          'Summarize what was accomplished in this workflow in 2-3 sentences.',
        context: {
          workflow: workflow.id,
          results: stepResults,
        },
      }),
    })
      .then(async response => {
        if (!response.ok) {
          throw new Error('Summary request failed');
        }
        return response.json();
      })
      .then(data => {
        setCompletionSummary(
          data.summary ??
            data.content ??
            buildFallbackSummary(workflowName, stepResults)
        );
      })
      .catch(() => {
        setCompletionSummary(buildFallbackSummary(workflowName, stepResults));
      })
      .finally(() => {
        setSummaryLoading(false);
        setAminState('speaking');
      });
  }, [
    completionSummary,
    completionVisible,
    stepResults,
    summaryLoading,
    workflow,
    workflowName,
  ]);

  useEffect(() => {
    if (!completionVisible || !caseId || !selectedCaseId || caseStatusLabel)
      return;
    void handleFileToCase();
  }, [caseId, caseStatusLabel, completionVisible, selectedCaseId]);

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

  const currentStepDef = steps[currentStep];
  const displayedDiff = clauseResult
    ? buildDiffSegments(
        clauseResult.originalText,
        clauseResult.response.items[0]?.suggested_redline ??
          clauseResult.originalText
      )
    : [];

  function updateAmin(
    message: string,
    state: AminState = 'speaking',
    cooldownMs = 1500
  ) {
    setAminMessage(message);
    setAminState(state);
    if (state !== 'thinking') {
      window.setTimeout(() => {
        setAminState(current => (current === 'thinking' ? current : 'idle'));
      }, cooldownMs);
    }
  }

  async function advanceStep(message?: string) {
    const finishedStep = currentStep;
    setCompletedSteps(prev =>
      prev.includes(finishedStep) ? prev : [...prev, finishedStep]
    );
    setSuccessFlash(true);
    setParticleStep(finishedStep);
    updateAmin(message ?? 'Step complete. Moving to the next one.');

    window.setTimeout(() => setSuccessFlash(false), 400);
    window.setTimeout(() => setParticleStep(null), 450);

    await wait(800);

    if (finishedStep >= steps.length - 1) {
      setCompletionVisible(true);
      return;
    }

    setCurrentStep(finishedStep + 1);
  }

  async function runResearchFlow() {
    if (currentStep === 0) {
      if (!researchQuery.trim()) {
        updateAmin('Add the research question first so I know what to run.');
        return;
      }
      setStepResults(prev => ({
        ...prev,
        0: {
          kind: 'text',
          content: `Query defined for ${researchJurisdiction}.`,
        },
      }));
      await advanceStep('Query captured. I am ready to run the research.');
      return;
    }

    if (currentStep === 1) {
      setRunning(true);
      setRunProgress(0);
      setAminState('thinking');
      setAminMessage('Working on it...');

      let progressValue = 0;
      const timer = window.setInterval(() => {
        progressValue = Math.min(96, progressValue + 4);
        setRunProgress(progressValue);
      }, 300);

      try {
        const response = await apiClient.legalResearch({
          question: researchQuery,
          limit: 10,
          output_language: 'en',
          evidence_scope: 'both',
          filters: {
            jurisdiction: researchJurisdiction,
          },
        });
        window.clearInterval(timer);
        setRunProgress(100);
        setResearchResult(response);
        setStepResults(prev => ({
          ...prev,
          1: { kind: 'research', data: response },
        }));
        setRunning(false);
        await advanceStep(
          'Research complete. The cited results are ready for review.'
        );
      } catch (error) {
        window.clearInterval(timer);
        setRunning(false);
        updateAmin(
          error instanceof Error
            ? error.message
            : 'Research failed unexpectedly.'
        );
      }
      return;
    }

    if (currentStep === 2) {
      await advanceStep(
        'Results reviewed. The research package is ready to file.'
      );
      return;
    }

    if (!selectedCaseId) {
      updateAmin('Select a case to file this research output.');
      return;
    }

    setRunning(true);
    try {
      const response = await fetch(`/api/v1/cases/${selectedCaseId}/research`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: researchQuery,
          jurisdiction: researchJurisdiction,
          result: researchResult,
        }),
      });
      if (!response.ok) {
        throw new Error('Unable to save research to case');
      }
      setRunning(false);
      setCaseStatusLabel('Saved to case');
      await advanceStep('Saved to case. The workflow is complete.');
    } catch (error) {
      setRunning(false);
      updateAmin(
        error instanceof Error
          ? error.message
          : 'Unable to save research to case.'
      );
    }
  }

  async function runContractFlow(file?: File) {
    if (currentStep === 0) {
      if (!file) {
        updateAmin('Choose a contract file first.');
        return;
      }

      setRunning(true);
      setAminState('thinking');
      setAminMessage('Working on it...');

      try {
        const response = await apiClient.uploadDocument(file, {
          title: file.name.replace(/\.[^.]+$/, ''),
          document_type: 'contract',
          jurisdiction: 'KSA',
          language: 'en',
          confidentiality: 'internal',
        });
        setUploadedContract({
          fileName: file.name,
          size: file.size,
          documentId: response.document.id,
          versionId: response.version.id,
        });
        setStepResults(prev => ({
          ...prev,
          0: { kind: 'text', content: `${file.name} uploaded.` },
        }));
        setRunning(false);
        await advanceStep('Contract uploaded. I am ready to analyze it.');
      } catch (error) {
        setRunning(false);
        updateAmin(error instanceof Error ? error.message : 'Upload failed.');
      }
      return;
    }

    if (currentStep === 1) {
      if (!uploadedContract) {
        updateAmin('Upload the contract before running analysis.');
        return;
      }

      setRunning(true);
      setRunProgress(0);
      setAminState('thinking');
      setAminMessage('Working on it...');

      try {
        const response = await apiClient.contractReview({
          document_id: uploadedContract.documentId,
          version_id: uploadedContract.versionId,
          review_mode: 'standard',
          focus_areas: [
            'liability',
            'termination',
            'payment',
            'confidentiality',
          ],
          output_language: 'en',
          evidence_scope: 'workspace',
        });
        const score = computeRiskScore(response.findings);
        setContractResult({ response, score });
        setStepResults(prev => ({
          ...prev,
          1: { kind: 'contract', data: response, score },
        }));
        setRunning(false);
        setRunProgress(100);
        await advanceStep(
          'Analysis complete. Review the findings and risk score.'
        );
      } catch (error) {
        setRunning(false);
        updateAmin(error instanceof Error ? error.message : 'Analysis failed.');
      }
      return;
    }

    if (currentStep === 2) {
      await advanceStep('Findings reviewed. The report is ready to export.');
      return;
    }

    triggerDownload(
      `${workflowName.replace(/\s+/g, '-').toLowerCase()}-report.txt`,
      `Contract Review\n\nSummary\n${contractResult?.response.summary ?? ''}\n\nScore\n${contractResult?.score ?? 0}\n`
    );
    await advanceStep('Report exported. The workflow is complete.');
  }

  async function runRedlinesFlow() {
    if (currentStep === 0) {
      if (!clauseText.trim()) {
        updateAmin(
          'Paste the clause text first so I can prepare the redlines.'
        );
        return;
      }
      setStepResults(prev => ({
        ...prev,
        0: { kind: 'text', content: `${clauseType} clause captured.` },
      }));
      await advanceStep('Clause captured. I am ready to generate redlines.');
      return;
    }

    if (currentStep === 1) {
      setRunning(true);
      setAminState('thinking');
      setAminMessage('Working on it...');

      try {
        const inputFile = new File([clauseText], 'clause-input.txt', {
          type: 'text/plain',
        });
        const document = await apiClient.uploadDocument(inputFile, {
          title: 'Clause Redlines Input',
          document_type: 'contract',
          jurisdiction: clauseJurisdiction,
          language: 'en',
          confidentiality: 'internal',
        });

        const response = await apiClient.clauseRedlines({
          document_id: document.document.id,
          version_id: document.version.id,
          jurisdiction: clauseJurisdiction as 'KSA' | 'UAE',
          clause_types:
            clauseType === 'other'
              ? undefined
              : [
                  clauseType as
                    | 'liability'
                    | 'indemnity'
                    | 'termination'
                    | 'payment'
                    | 'confidentiality'
                    | 'governing_law',
                ],
          output_language: 'en',
          evidence_scope: 'workspace',
        });

        setClauseResult({ response, originalText: clauseText });
        setStepResults(prev => ({
          ...prev,
          1: { kind: 'redlines', data: response, originalText: clauseText },
        }));
        setRunning(false);
        await advanceStep(
          'Redlines generated. Review the side-by-side changes.'
        );
      } catch (error) {
        setRunning(false);
        updateAmin(error instanceof Error ? error.message : 'Redlines failed.');
      }
      return;
    }

    if (currentStep === 2) {
      await advanceStep(
        'Changes reviewed. The clause package is ready to export.'
      );
      return;
    }

    triggerDownload(
      `${workflowName.replace(/\s+/g, '-').toLowerCase()}-export.txt`,
      `Original Clause\n${clauseResult?.originalText ?? ''}\n\nRedlined Clause\n${clauseResult?.response.items[0]?.suggested_redline ?? ''}`
    );
    await advanceStep('Export complete. The workflow is complete.');
  }

  async function runDemoFlow() {
    setRunning(true);
    setRunProgress(0);
    setAminState('thinking');
    setAminMessage('Working on it...');

    await runWorkflowSimulation({
      onTick: tick => setRunProgress(tick.progress),
    });

    const output = getWorkflowSimulatedOutput(workflow.id, currentStep);
    setStepResults(prev => ({
      ...prev,
      [currentStep]: { kind: 'simulated', data: output },
    }));
    setRunning(false);
    await advanceStep('Step complete. Moving to the next one.');
  }

  async function handleRun(file?: File) {
    if (isLive && workflow.id === 'RESEARCH_LEGAL_MEMO') {
      await runResearchFlow();
      return;
    }
    if (isLive && workflow.id === 'CORPORATE_CONTRACTS') {
      await runContractFlow(file);
      return;
    }
    if (isLive && workflow.id === 'ARBITRATION_CLAUSE') {
      await runRedlinesFlow();
      return;
    }
    await runDemoFlow();
  }

  async function handleFileToCase() {
    if (!selectedCaseId) {
      setCaseStatusLabel('Select a case first.');
      return;
    }

    try {
      const response = await fetch(`/api/v1/cases/${selectedCaseId}/events`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'workflow_completed',
          title: workflowName,
          description:
            completionSummary ||
            buildFallbackSummary(workflowName, stepResults),
        }),
      });
      if (!response.ok) {
        throw new Error('Unable to file workflow to case');
      }
      const selectedCase = caseOptions.find(
        option => option.id === selectedCaseId
      );
      setCaseStatusLabel(
        `Filed to case ${selectedCase?.title ?? selectedCaseId} ✓`
      );
    } catch (error) {
      setCaseStatusLabel(
        error instanceof Error ? error.message : 'Unable to file workflow.'
      );
    }
  }

  function renderProgress() {
    if (!running) return null;
    return (
      <div className="workflow-run-progress">
        <div className="workflow-run-progress-bar">
          <motion.div
            className="workflow-run-progress-fill"
            animate={{ width: `${runProgress}%` }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
          />
        </div>
        <span>{Math.round(runProgress)}%</span>
      </div>
    );
  }

  function renderResearchView() {
    if (!currentStepDef) return null;

    if (currentStep === 0) {
      return (
        <div className="workflow-live-step-card">
          <h2>{currentStepDef.name}</h2>
          <p>{currentStepDef.detail}</p>
          <div className="form-group">
            <label className="form-label">Research question</label>
            <textarea
              className="form-textarea workflow-launch-textarea"
              rows={4}
              value={researchQuery}
              onChange={event => setResearchQuery(event.target.value)}
              placeholder="What should Amin research?"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Jurisdiction</label>
            <select
              className="form-select"
              value={researchJurisdiction}
              onChange={event => setResearchJurisdiction(event.target.value)}
            >
              <option value="KSA">KSA</option>
              <option value="UAE">UAE</option>
              <option value="Qatar">Qatar</option>
            </select>
          </div>
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
            disabled={running}
          >
            Run this step
          </button>
        </div>
      );
    }

    if (currentStep === 1) {
      return (
        <div className="workflow-live-step-card">
          <h2>{currentStepDef.name}</h2>
          <p>{currentStepDef.detail}</p>
          {renderProgress()}
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
            disabled={running}
          >
            {running ? 'Running Research...' : 'Run this step'}
          </button>
        </div>
      );
    }

    if (currentStep === 2 && researchResult) {
      return (
        <div className="workflow-live-step-card workflow-scroll-card">
          <div className="workflow-results-header-v2">
            <h2>Research Results</h2>
            <span>{researchResult.evidence.length} sources</span>
          </div>
          <div className="workflow-answer-text">
            {researchResult.answer_text}
          </div>
          <div className="workflow-results-grid">
            {researchResult.evidence.map(item => (
              <div key={item.chunk_id} className="workflow-result-card">
                <strong>
                  {item.source_label || item.document_title || 'Source'}
                </strong>
                <p>{item.snippet}</p>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
          >
            Continue
          </button>
        </div>
      );
    }

    return (
      <div className="workflow-live-step-card">
        <h2>{currentStepDef.name}</h2>
        <p>{currentStepDef.detail}</p>
        {!selectedCaseId ? (
          <div className="workflow-completion-case-select">
            <label className="form-label">
              Select a case to file this research
            </label>
            <select
              className="form-select"
              value={selectedCaseId}
              onChange={event => setSelectedCaseId(event.target.value)}
            >
              <option value="">Select a case</option>
              {caseOptions.map(option => (
                <option key={option.id} value={option.id}>
                  {option.title}
                </option>
              ))}
            </select>
          </div>
        ) : null}
        {caseStatusLabel ? (
          <div className="workflow-inline-note">{caseStatusLabel}</div>
        ) : null}
        <button
          type="button"
          className="workflow-run-button"
          onClick={() => void handleRun()}
          disabled={running}
        >
          {running ? 'Saving...' : 'Run this step'}
        </button>
      </div>
    );
  }

  function renderContractView() {
    if (!currentStepDef) return null;

    if (currentStep === 0) {
      return (
        <div className="workflow-live-step-card">
          <h2>{currentStepDef.name}</h2>
          <p>{currentStepDef.detail}</p>
          <label className="workflow-upload-dropzone">
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={event => {
                const file = event.target.files?.[0];
                if (file) void handleRun(file);
              }}
            />
            <span>Drag and drop a contract or click to upload</span>
          </label>
          {uploadedContract ? (
            <div className="workflow-inline-note">
              {uploadedContract.fileName} ·{' '}
              {(uploadedContract.size / 1024).toFixed(1)} KB
            </div>
          ) : null}
        </div>
      );
    }

    if (currentStep === 1) {
      return (
        <div className="workflow-live-step-card">
          <h2>{currentStepDef.name}</h2>
          <p>{currentStepDef.detail}</p>
          {renderProgress()}
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
            disabled={running}
          >
            {running ? 'Running Analysis...' : 'Run this step'}
          </button>
        </div>
      );
    }

    if (currentStep === 2 && contractResult) {
      const scoreTone =
        contractResult.score <= 30
          ? 'emerald'
          : contractResult.score <= 70
            ? 'amber'
            : 'red';

      return (
        <div className="workflow-live-step-card workflow-scroll-card">
          <div className="workflow-risk-score" data-tone={scoreTone}>
            <span>Risk Score</span>
            <strong>{contractResult.score}</strong>
          </div>
          <div className="workflow-results-grid">
            {contractResult.response.findings.map(finding => (
              <div key={finding.finding_id} className="workflow-result-card">
                <div className="workflow-result-card-head">
                  <strong>{finding.title}</strong>
                  <span className="workflow-severity-chip">
                    {finding.severity}
                  </span>
                </div>
                <p>{finding.issue}</p>
                <small>{finding.recommendation}</small>
              </div>
            ))}
          </div>
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
          >
            Continue
          </button>
        </div>
      );
    }

    return (
      <div className="workflow-live-step-card">
        <h2>{currentStepDef.name}</h2>
        <p>{currentStepDef.detail}</p>
        <div className="workflow-inline-actions">
          <button
            type="button"
            className="workflow-template-button"
            onClick={() =>
              triggerDownload(
                `${workflowName.replace(/\s+/g, '-').toLowerCase()}-report.txt`,
                `Contract Review\n\n${contractResult?.response.summary ?? ''}`
              )
            }
          >
            Download Report
          </button>
          {selectedCaseId ? (
            <button
              type="button"
              className="workflow-template-button"
              onClick={() => void handleFileToCase()}
            >
              File to Case
            </button>
          ) : null}
        </div>
        <button
          type="button"
          className="workflow-run-button"
          onClick={() => void handleRun()}
        >
          Complete Export
        </button>
      </div>
    );
  }

  function renderRedlinesView() {
    if (!currentStepDef) return null;

    if (currentStep === 0) {
      return (
        <div className="workflow-live-step-card">
          <h2>{currentStepDef.name}</h2>
          <p>{currentStepDef.detail}</p>
          <div className="form-group">
            <label className="form-label">Clause text</label>
            <textarea
              className="form-textarea workflow-launch-textarea"
              rows={6}
              value={clauseText}
              onChange={event => setClauseText(event.target.value)}
              placeholder="Paste the clause text here."
            />
          </div>
          <div className="workflow-inline-form">
            <div className="form-group">
              <label className="form-label">Clause type</label>
              <select
                className="form-select"
                value={clauseType}
                onChange={event => setClauseType(event.target.value)}
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
              <label className="form-label">Jurisdiction</label>
              <select
                className="form-select"
                value={clauseJurisdiction}
                onChange={event => setClauseJurisdiction(event.target.value)}
              >
                <option value="KSA">KSA</option>
                <option value="UAE">UAE</option>
              </select>
            </div>
          </div>
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
            disabled={running}
          >
            Run this step
          </button>
        </div>
      );
    }

    if (currentStep === 1) {
      return (
        <div className="workflow-live-step-card">
          <h2>{currentStepDef.name}</h2>
          <p>{currentStepDef.detail}</p>
          {renderProgress()}
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
            disabled={running}
          >
            {running ? 'Generating Redlines...' : 'Run this step'}
          </button>
        </div>
      );
    }

    if (currentStep === 2 && clauseResult) {
      return (
        <div className="workflow-live-step-card workflow-scroll-card">
          <div className="workflow-redline-grid">
            <div className="workflow-redline-pane">
              <span>Original</span>
              <div className="workflow-redline-text">
                {clauseResult.originalText}
              </div>
            </div>
            <div className="workflow-redline-pane">
              <span>Redlined</span>
              <div className="workflow-redline-text">
                {displayedDiff.map((segment, index) => (
                  <span
                    key={`${segment.type}-${index}`}
                    className={`workflow-redline-segment workflow-redline-segment-${segment.type}`}
                  >
                    {segment.text}
                  </span>
                ))}
              </div>
            </div>
          </div>
          <div className="workflow-inline-note">
            {clauseResult.response.items[0]?.rationale ??
              clauseResult.response.summary}
          </div>
          <button
            type="button"
            className="workflow-run-button"
            onClick={() => void handleRun()}
          >
            Continue
          </button>
        </div>
      );
    }

    return (
      <div className="workflow-live-step-card">
        <h2>{currentStepDef.name}</h2>
        <p>{currentStepDef.detail}</p>
        <button
          type="button"
          className="workflow-run-button"
          onClick={() => void handleRun()}
        >
          Export Package
        </button>
      </div>
    );
  }

  function renderDemoView() {
    const result = stepResults[currentStep];

    return (
      <div className="workflow-live-step-card">
        <div className="workflow-demo-chip">Demo mode</div>
        <h2>{currentStepDef?.name}</h2>
        <p>{currentStepDef?.detail}</p>
        {renderProgress()}
        {result?.kind === 'simulated' ? (
          <div className="workflow-simulated-output">
            {result.data.type === 'text' || result.data.type === 'document' ? (
              <pre>{result.data.content}</pre>
            ) : null}
            {result.data.type === 'list' ? (
              <div className="workflow-results-grid">
                {result.data.content.map(item => (
                  <div key={item.label} className="workflow-result-card">
                    <strong>{item.label}</strong>
                    <p>{item.detail}</p>
                    <small>{item.status}</small>
                  </div>
                ))}
              </div>
            ) : null}
            {result.data.type === 'score' ? (
              <div className="workflow-risk-score" data-tone="emerald">
                <span>{result.data.label}</span>
                <strong>{result.data.score}</strong>
              </div>
            ) : null}
          </div>
        ) : null}
        <button
          type="button"
          className="workflow-run-button"
          onClick={() => void handleRun()}
          disabled={running}
        >
          {running ? 'Running Step...' : 'Run this step'}
        </button>
      </div>
    );
  }

  function renderStepContent() {
    if (completionVisible) {
      return (
        <WorkflowCompletion
          workflowName={workflowName}
          summary={completionSummary}
          isGeneratingSummary={summaryLoading}
          onBack={() => router.push('/workflows')}
          onDownload={() =>
            triggerDownload(
              `${workflowName.replace(/\s+/g, '-').toLowerCase()}-summary.txt`,
              completionSummary ||
                buildFallbackSummary(workflowName, stepResults)
            )
          }
          onFileToCase={() => void handleFileToCase()}
          caseStatusLabel={caseStatusLabel}
          caseOptions={!caseId ? caseOptions : []}
          selectedCaseId={selectedCaseId}
          onCaseChange={setSelectedCaseId}
        />
      );
    }

    if (isLive && workflow.id === 'RESEARCH_LEGAL_MEMO') {
      return renderResearchView();
    }
    if (isLive && workflow.id === 'CORPORATE_CONTRACTS') {
      return renderContractView();
    }
    if (isLive && workflow.id === 'ARBITRATION_CLAUSE') {
      return renderRedlinesView();
    }
    return renderDemoView();
  }

  return (
    <div ref={canvasRef} className="workflow-execute-canvas">
      <StepRail
        steps={steps.map((step, index) => ({
          title: step.name,
          estimate: getWorkflowStepEstimate(workflowId, index),
        }))}
        currentStep={currentStep}
        completedSteps={completedSteps}
        onStepSelect={stepIndex => {
          if (completedSteps.includes(stepIndex) || stepIndex === currentStep) {
            setCurrentStep(stepIndex);
          }
        }}
        particleStep={particleStep}
      />

      <div className="workflow-execute-main">
        <div className="workflow-execute-topline">
          <div>
            <span className="workflow-page-kicker">{workflowName}</span>
            <h1>{currentStepDef?.name ?? workflowName}</h1>
          </div>
          {activeCase ? (
            <div className="workflow-inline-note">
              {activeCase.case_title} · {activeCase.client_name}
            </div>
          ) : null}
        </div>

        <StepWorkspace
          stepKey={
            completionVisible ? 'completion' : `${workflowId}-${currentStep}`
          }
          successFlash={successFlash}
        >
          {renderStepContent()}
        </StepWorkspace>
      </div>

      <aside className="workflow-execute-amin" data-state={aminState}>
        <div className="workflow-execute-amin-head">
          <AminAvatar
            size={56}
            state={
              aminState === 'success'
                ? 'success'
                : aminState === 'thinking'
                  ? 'thinking'
                  : aminState === 'speaking'
                    ? 'speaking'
                    : 'idle'
            }
            showWaveform={aminState === 'speaking'}
          />
          <div>
            <span className="workflow-page-kicker">Amin</span>
            <strong>{aminState === 'thinking' ? 'Thinking' : 'Guiding'}</strong>
          </div>
        </div>
        <div className="workflow-execute-amin-body">
          {aminState === 'thinking' ? (
            <p className="workflow-completion-typing">Working on it...</p>
          ) : (
            <p>{aminMessage}</p>
          )}
        </div>
      </aside>
    </div>
  );
}
