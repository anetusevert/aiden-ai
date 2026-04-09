import {
  getWorkflowById,
  getWorkflowJourneySteps,
  type WorkflowDefinition,
  type WorkflowStep,
} from './workflowRegistry';

interface StepInstructionOptions {
  workflowId: string;
  stepIndex: number;
  userInputs?: Record<string, string>;
  caseId?: string | null;
}

function toolHints(workflowId: string, stepDetail: string): string {
  const lower = stepDetail.toLowerCase();
  const hints: string[] = [];

  if (
    lower.includes('research') ||
    lower.includes('statut') ||
    lower.includes('decree') ||
    lower.includes('legal basis')
  )
    hints.push('legal_research');
  if (
    lower.includes('draft') ||
    lower.includes('memorandum') ||
    lower.includes('letter') ||
    lower.includes('claim')
  )
    hints.push('draft_document');
  if (
    lower.includes('review') ||
    lower.includes('contract') ||
    lower.includes('agreement')
  )
    hints.push('contract_review');
  if (lower.includes('redline') || lower.includes('clause'))
    hints.push('clause_redlines');
  if (
    lower.includes('search') ||
    lower.includes('corpus') ||
    lower.includes('precedent')
  )
    hints.push('search_legal_corpus');
  if (lower.includes('summar')) hints.push('summarize');
  if (lower.includes('translat') || lower.includes('arabic'))
    hints.push('translate');

  if (hints.length === 0) {
    hints.push('legal_research', 'draft_document');
  }

  return hints.join(', ');
}

export function buildStepInstruction(options: StepInstructionOptions): string {
  const { workflowId, stepIndex, userInputs, caseId } = options;

  const workflow = getWorkflowById(workflowId);
  if (!workflow) return `Execute step ${stepIndex + 1} of the workflow.`;

  const steps = getWorkflowJourneySteps(workflow);
  const step = steps[stepIndex];
  if (!step) return `Execute the next step of ${workflow.name}.`;

  const lines: string[] = [
    `[WORKFLOW STEP INSTRUCTION]`,
    `Workflow: ${workflow.name}`,
    `Category: ${workflow.category}`,
    `Description: ${workflow.description}`,
    ``,
    `Step ${step.order} of ${steps.length}: ${step.name}`,
    `Detail: ${step.detail}`,
    ``,
    `Suggested tools: ${toolHints(workflowId, step.detail)}`,
  ];

  if (userInputs && Object.keys(userInputs).length > 0) {
    lines.push('', 'User-provided inputs:');
    for (const [key, value] of Object.entries(userInputs)) {
      if (value.trim()) {
        lines.push(`  ${key}: ${value}`);
      }
    }
  }

  if (caseId) {
    lines.push('', `This workflow is linked to case ID: ${caseId}.`);
  }

  lines.push(
    '',
    'Instructions:',
    '- Act as a senior KSA legal professional guiding a colleague.',
    '- Execute this step using your available tools. Do real work, not placeholders.',
    '- Reference specific Saudi laws, Royal Decrees, ministerial resolutions, or Sharia principles where applicable.',
    '- If the step involves drafting, produce actual legal content in professional language.',
    '- If the step involves research, cite specific sources and explain their relevance.',
    '- If the step involves review, provide detailed findings with risk assessment.',
    '- Keep your response focused on this specific step.',
    '- When you finish, summarize what was accomplished.'
  );

  return lines.join('\n');
}

export function buildWorkflowGreeting(workflow: WorkflowDefinition): string {
  const steps = getWorkflowJourneySteps(workflow);
  const stepList = steps.map(s => `${s.order}. ${s.name}`).join('\n');

  return [
    `I'm ready to guide you through "${workflow.name}".`,
    '',
    workflow.description,
    '',
    `We'll work through ${steps.length} steps together:`,
    stepList,
    '',
    `Let's begin with step 1: ${steps[0]?.name ?? 'the first step'}. Click "Run this step" when you're ready, or ask me anything first.`,
  ].join('\n');
}

export function buildCompletionSummaryPrompt(
  workflow: WorkflowDefinition | undefined,
  stepCount: number
): string {
  const name = workflow?.name ?? 'the workflow';
  return [
    `[WORKFLOW COMPLETION]`,
    `The user just completed all ${stepCount} steps of "${name}".`,
    `${workflow?.description ?? ''}`,
    '',
    `Provide a 2-3 sentence professional summary of what was accomplished.`,
    `Reference the key deliverables produced during the workflow.`,
    `Keep the tone professional and suitable for a KSA law firm.`,
  ].join('\n');
}
