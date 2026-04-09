'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { motion, useAnimationFrame } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { AminAvatar } from '@/components/amin/AminAvatar';
import { useAminContext } from '@/components/amin/AminProvider';
import { StepRail } from '@/components/workflows/StepRail';
import { StepWorkspace } from '@/components/workflows/StepWorkspace';
import { WorkflowCompletion } from '@/components/workflows/WorkflowCompletion';
import { reportScreenContext } from '@/lib/screenContext';
import {
  buildStepInstruction,
  buildWorkflowGreeting,
  buildCompletionSummaryPrompt,
} from '@/lib/workflowStepInstructions';
import {
  getWorkflowById,
  getWorkflowDisplayName,
  getWorkflowJourneySteps,
  getWorkflowStepEstimate,
  type WorkflowCategory,
} from '@/lib/workflowRegistry';

interface CaseListItem {
  id: string;
  title: string;
}

function triggerDownload(
  filename: string,
  content: string,
  type = 'text/plain'
) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function WorkflowExecutePage() {
  const params = useParams<{ category: string; workflowId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const outputScrollRef = useRef<HTMLDivElement | null>(null);

  const amin = useAminContext();
  const workflow = useMemo(
    () => getWorkflowById(params.workflowId),
    [params.workflowId]
  );
  const workflowId = params.workflowId;
  const category = params.category as WorkflowCategory;
  const steps = useMemo(() => getWorkflowJourneySteps(workflow), [workflow]);
  const workflowName = getWorkflowDisplayName(workflow);
  const caseId = searchParams.get('case');

  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [running, setRunning] = useState(false);
  const [successFlash, setSuccessFlash] = useState(false);
  const [particleStep, setParticleStep] = useState<number | null>(null);
  const [completionVisible, setCompletionVisible] = useState(false);
  const [completionSummary, setCompletionSummary] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [caseOptions, setCaseOptions] = useState<CaseListItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState(caseId ?? '');
  const [caseStatusLabel, setCaseStatusLabel] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [userInputs, setUserInputs] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    const query = searchParams.get('query');
    const jurisdiction = searchParams.get('jurisdiction');
    const clauseType = searchParams.get('clauseType');
    if (query) initial.query = query;
    if (jurisdiction) initial.jurisdiction = jurisdiction;
    if (clauseType) initial.clauseType = clauseType;
    return initial;
  });

  const [stepOutputs, setStepOutputs] = useState<Record<number, string>>({});
  const greetingSentRef = useRef(false);
  const lastStepTriggeredRef = useRef(-1);

  const currentStepDef = steps[currentStep];

  useAnimationFrame(time => {
    if (!canvasRef.current) return;
    const progress = (time % 30000) / 30000;
    const gx = 50 + Math.sin(progress * Math.PI * 2) * 35;
    const gy = 50 + Math.cos(progress * Math.PI * 2) * 35;
    canvasRef.current.style.setProperty('--gx', `${gx}%`);
    canvasRef.current.style.setProperty('--gy', `${gy}%`);
  });

  useEffect(() => {
    fetch('/api/v1/cases?limit=50&offset=0', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        const items = (data?.items ?? []) as Array<{
          id: string;
          title: string;
        }>;
        setCaseOptions(items.map(i => ({ id: i.id, title: i.title })));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!workflow || greetingSentRef.current) return;
    greetingSentRef.current = true;

    const initConversation = async () => {
      try {
        if (!amin.activeConversation) {
          await amin.createConversation();
        }
        amin.injectMessage('assistant', buildWorkflowGreeting(workflow));
      } catch {
        /* ignore */
      }
    };

    void initConversation();
  }, [workflow, amin]);

  useEffect(() => {
    if (!workflow || !currentStepDef) return;

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
        stepName: currentStepDef.name,
        caseId: selectedCaseId || null,
      },
    });
  }, [
    category,
    currentStep,
    currentStepDef,
    selectedCaseId,
    steps.length,
    workflow,
    workflowName,
  ]);

  const captureAminOutput = useCallback(() => {
    const msgs = amin.messages;
    const streaming = amin.streamingContent;

    let latestAssistant = '';
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') {
        latestAssistant = msgs[i].content;
        break;
      }
    }

    if (streaming) {
      return streaming;
    }
    return latestAssistant;
  }, [amin.messages, amin.streamingContent]);

  useEffect(() => {
    if (running && amin.aminStatus === 'idle' && !amin.isStreaming) {
      const output = captureAminOutput();
      if (output) {
        setStepOutputs(prev => ({ ...prev, [currentStep]: output }));
      }
      setRunning(false);
    }
  }, [
    amin.aminStatus,
    amin.isStreaming,
    captureAminOutput,
    currentStep,
    running,
  ]);

  useEffect(() => {
    if (running && amin.isStreaming) {
      setStepOutputs(prev => ({
        ...prev,
        [currentStep]: amin.streamingContent,
      }));
    }
  }, [amin.isStreaming, amin.streamingContent, currentStep, running]);

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [amin.messages, amin.streamingContent]);

  useEffect(() => {
    if (outputScrollRef.current) {
      outputScrollRef.current.scrollTop = outputScrollRef.current.scrollHeight;
    }
  }, [stepOutputs, currentStep]);

  useEffect(() => {
    if (!completionVisible || completionSummary || summaryLoading) return;
    if (!workflow) return;

    setSummaryLoading(true);
    const prompt = buildCompletionSummaryPrompt(workflow, steps.length);
    amin.sendSystemTrigger(prompt).catch(() => {});

    const timer = window.setTimeout(() => {
      const output = captureAminOutput();
      setCompletionSummary(
        output ||
          `${workflowName} completed successfully. All ${steps.length} steps were executed with Amin's guidance.`
      );
      setSummaryLoading(false);
    }, 8000);

    return () => window.clearTimeout(timer);
  }, [
    captureAminOutput,
    completionSummary,
    completionVisible,
    steps.length,
    summaryLoading,
    workflow,
    workflowName,
    amin,
  ]);

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

  function advanceStep() {
    const finishedStep = currentStep;
    setCompletedSteps(prev =>
      prev.includes(finishedStep) ? prev : [...prev, finishedStep]
    );
    setSuccessFlash(true);
    setParticleStep(finishedStep);

    window.setTimeout(() => setSuccessFlash(false), 400);
    window.setTimeout(() => setParticleStep(null), 450);

    if (finishedStep >= steps.length - 1) {
      setCompletionVisible(true);
      return;
    }

    setCurrentStep(finishedStep + 1);
    lastStepTriggeredRef.current = -1;
  }

  async function handleRunStep() {
    if (running) return;
    if (lastStepTriggeredRef.current === currentStep) return;

    lastStepTriggeredRef.current = currentStep;
    setRunning(true);

    const instruction = buildStepInstruction({
      workflowId,
      stepIndex: currentStep,
      userInputs,
      caseId,
    });

    try {
      await amin.sendSystemTrigger(instruction);
    } catch {
      setRunning(false);
    }
  }

  function handleChatSend() {
    const trimmed = chatInput.trim();
    if (!trimmed) return;
    setChatInput('');
    void amin.sendMessage(trimmed);
  }

  function handleChatKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSend();
    }
  }

  async function handleFileToCase() {
    if (!selectedCaseId) {
      setCaseStatusLabel('Select a case first.');
      return;
    }
    try {
      const r = await fetch(`/api/v1/cases/${selectedCaseId}/events`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'workflow_completed',
          title: workflowName,
          description: completionSummary || `${workflowName} completed.`,
        }),
      });
      if (!r.ok) throw new Error('Failed to file');
      const selected = caseOptions.find(o => o.id === selectedCaseId);
      setCaseStatusLabel(`Filed to ${selected?.title ?? selectedCaseId}`);
    } catch (err) {
      setCaseStatusLabel(err instanceof Error ? err.message : 'Filing failed.');
    }
  }

  function renderUserInputFields() {
    if (!currentStepDef) return null;
    const detail = currentStepDef.detail.toLowerCase();
    const fields: React.ReactNode[] = [];

    if (
      detail.includes('research') ||
      detail.includes('question') ||
      detail.includes('query') ||
      detail.includes('issue')
    ) {
      fields.push(
        <div key="query" className="form-group">
          <label className="form-label">Research question or topic</label>
          <textarea
            className="form-textarea workflow-launch-textarea"
            rows={3}
            value={userInputs.query ?? ''}
            onChange={e =>
              setUserInputs(prev => ({ ...prev, query: e.target.value }))
            }
            placeholder="Describe what Amin should research or work on for this step."
          />
        </div>
      );
    }

    if (
      detail.includes('jurisdict') ||
      detail.includes('saudi') ||
      detail.includes('gcc')
    ) {
      fields.push(
        <div key="jurisdiction" className="form-group">
          <label className="form-label">Jurisdiction</label>
          <select
            className="form-select"
            value={userInputs.jurisdiction ?? 'KSA'}
            onChange={e =>
              setUserInputs(prev => ({ ...prev, jurisdiction: e.target.value }))
            }
          >
            <option value="KSA">KSA</option>
            <option value="UAE">UAE</option>
            <option value="Qatar">Qatar</option>
            <option value="Bahrain">Bahrain</option>
            <option value="Kuwait">Kuwait</option>
            <option value="Oman">Oman</option>
          </select>
        </div>
      );
    }

    if (fields.length === 0) return null;

    return <div className="workflow-launch-fields">{fields}</div>;
  }

  function renderToolStatus() {
    if (amin.activeTools.length === 0) return null;
    return (
      <div className="workflow-tool-status">
        {amin.activeTools.map(tool => (
          <div
            key={tool.tool}
            className="workflow-tool-chip"
            data-status={tool.status}
          >
            <span className="workflow-tool-chip-dot" />
            <span>{tool.tool.replace(/_/g, ' ')}</span>
            {tool.summary ? <small>{tool.summary}</small> : null}
          </div>
        ))}
      </div>
    );
  }

  function renderStepOutput() {
    const output = stepOutputs[currentStep];
    if (!output) return null;

    return (
      <div ref={outputScrollRef} className="workflow-amin-output">
        <ReactMarkdown>{output}</ReactMarkdown>
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
          onDownload={() => {
            const allOutputs = Object.entries(stepOutputs)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([idx, content]) => {
                const s = steps[Number(idx)];
                return `## Step ${Number(idx) + 1}: ${s?.name ?? 'Step'}\n\n${content}`;
              })
              .join('\n\n---\n\n');
            triggerDownload(
              `${workflowName.replace(/\s+/g, '-').toLowerCase()}-output.md`,
              `# ${workflowName}\n\n${allOutputs}\n\n---\n\n## Summary\n\n${completionSummary}`
            );
          }}
          onFileToCase={() => void handleFileToCase()}
          caseStatusLabel={caseStatusLabel}
          caseOptions={!caseId ? caseOptions : []}
          selectedCaseId={selectedCaseId}
          onCaseChange={setSelectedCaseId}
        />
      );
    }

    const hasOutput = Boolean(stepOutputs[currentStep]);
    const stepDone = completedSteps.includes(currentStep);

    return (
      <div className="workflow-live-step-card">
        <h2>{currentStepDef?.name}</h2>
        <p>{currentStepDef?.detail}</p>

        {renderToolStatus()}
        {renderUserInputFields()}
        {renderStepOutput()}

        {running ? (
          <div className="workflow-amin-working">
            <span className="workflow-amin-working-dot" />
            Amin is working on this step...
          </div>
        ) : null}

        <div className="workflow-step-actions">
          {!stepDone ? (
            <button
              type="button"
              className="workflow-run-button"
              onClick={() => void handleRunStep()}
              disabled={running}
            >
              {running
                ? 'Amin is working...'
                : hasOutput
                  ? 'Re-run this step'
                  : 'Run this step'}
            </button>
          ) : null}

          {hasOutput && !stepDone ? (
            <button
              type="button"
              className="workflow-template-button"
              onClick={advanceStep}
            >
              {currentStep >= steps.length - 1
                ? 'Complete workflow'
                : 'Continue to next step'}
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div ref={canvasRef} className="workflow-execute-canvas">
      <StepRail
        steps={steps.map((step, idx) => ({
          title: step.name,
          estimate: getWorkflowStepEstimate(workflowId, idx),
        }))}
        currentStep={currentStep}
        completedSteps={completedSteps}
        onStepSelect={idx => {
          if (completedSteps.includes(idx) || idx === currentStep) {
            setCurrentStep(idx);
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

      <aside className="workflow-execute-amin" data-state={amin.aminStatus}>
        <div className="workflow-execute-amin-head">
          <AminAvatar
            size={48}
            state={
              amin.aminStatus === 'thinking'
                ? 'thinking'
                : amin.aminStatus === 'speaking'
                  ? 'speaking'
                  : 'idle'
            }
            showWaveform={amin.aminStatus === 'speaking'}
          />
          <div>
            <span className="workflow-page-kicker">Amin</span>
            <strong>
              {amin.aminStatus === 'thinking'
                ? 'Working'
                : amin.isStreaming
                  ? 'Responding'
                  : 'Guiding'}
            </strong>
          </div>
        </div>

        <div ref={chatScrollRef} className="workflow-execute-amin-chat">
          {amin.messages
            .filter(m => m.role === 'assistant' || m.role === 'user')
            .slice(-20)
            .map(msg => (
              <div
                key={msg.id}
                className={`workflow-chat-msg workflow-chat-msg-${msg.role}`}
              >
                {msg.role === 'user' ? (
                  <span className="workflow-chat-msg-label">You</span>
                ) : null}
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            ))}

          {amin.isStreaming && amin.streamingContent ? (
            <div className="workflow-chat-msg workflow-chat-msg-assistant workflow-chat-msg-streaming">
              <ReactMarkdown>{amin.streamingContent}</ReactMarkdown>
            </div>
          ) : null}

          {amin.aminStatus === 'thinking' && !amin.isStreaming ? (
            <div className="workflow-chat-msg workflow-chat-msg-assistant">
              <span className="workflow-completion-typing">Thinking...</span>
            </div>
          ) : null}
        </div>

        <div className="workflow-execute-amin-input">
          <textarea
            className="workflow-chat-textarea"
            rows={2}
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={handleChatKeyDown}
            placeholder="Ask Amin anything..."
          />
          <button
            type="button"
            className="workflow-chat-send"
            onClick={handleChatSend}
            disabled={!chatInput.trim() || amin.aminStatus === 'thinking'}
          >
            Send
          </button>
        </div>
      </aside>
    </div>
  );
}
