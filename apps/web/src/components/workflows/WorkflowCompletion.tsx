'use client';

import { motion } from 'framer-motion';

interface CaseOption {
  id: string;
  title: string;
}

export function WorkflowCompletion({
  workflowName,
  summary,
  isGeneratingSummary,
  onBack,
  onDownload,
  onFileToCase,
  caseStatusLabel,
  caseOptions = [],
  selectedCaseId,
  onCaseChange,
}: {
  workflowName: string;
  summary: string;
  isGeneratingSummary: boolean;
  onBack: () => void;
  onDownload: () => void;
  onFileToCase: () => void;
  caseStatusLabel?: string | null;
  caseOptions?: CaseOption[];
  selectedCaseId?: string;
  onCaseChange?: (caseId: string) => void;
}) {
  return (
    <div className="workflow-completion-card">
      <motion.svg
        className="workflow-completion-check"
        width="88"
        height="88"
        viewBox="0 0 88 88"
        fill="none"
        initial="hidden"
        animate="visible"
      >
        <circle
          cx="44"
          cy="44"
          r="38"
          stroke="rgba(255,255,255,0.14)"
          strokeWidth="2"
        />
        <motion.path
          d="M28 45.5L39 56.5L61 33.5"
          stroke="rgba(255,255,255,0.92)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
          variants={{
            hidden: { pathLength: 0, opacity: 0 },
            visible: {
              pathLength: 1,
              opacity: 1,
              transition: { duration: 0.6, ease: 'easeOut' },
            },
          }}
        />
      </motion.svg>

      <span className="workflow-page-kicker">Workflow Complete</span>
      <h2>{workflowName}</h2>

      <div className="workflow-completion-summary">
        <div className="workflow-completion-divider" />
        <span>Amin Summary</span>
        <div className="workflow-completion-divider" />
      </div>

      <div className="workflow-completion-summary-body">
        {isGeneratingSummary ? (
          <p className="workflow-completion-typing">
            Amin is summarizing the work...
          </p>
        ) : (
          <p>{summary}</p>
        )}
      </div>

      <div className="workflow-completion-actions">
        <button
          type="button"
          className="workflow-template-button"
          onClick={onFileToCase}
        >
          File to Case
        </button>
        <button
          type="button"
          className="workflow-template-button"
          onClick={onDownload}
        >
          Download
        </button>
        <button
          type="button"
          className="workflow-template-button"
          onClick={onBack}
        >
          Back to Workflows
        </button>
      </div>

      {caseOptions.length > 0 && onCaseChange ? (
        <div className="workflow-completion-case-select">
          <label className="form-label">Case</label>
          <select
            className="form-select"
            value={selectedCaseId ?? ''}
            onChange={event => onCaseChange(event.target.value)}
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
        <div className="workflow-completion-case-status">{caseStatusLabel}</div>
      ) : null}
    </div>
  );
}
