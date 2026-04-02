'use client';

import type { ToolExecution, SubTaskInfo } from './useAmin';

interface AminToolStatusProps {
  tools: ToolExecution[];
  subTasks?: SubTaskInfo[];
  onConfirm?: (toolName: string, approved: boolean) => void;
}

const TOOL_LABELS: Record<string, string> = {
  search_documents: 'Searching documents…',
  search_legal_corpus: 'Searching legal corpus…',
  legal_research: 'Researching…',
  contract_review: 'Reviewing contract…',
  clause_redlines: 'Generating redlines…',
  draft_document: 'Drafting document…',
  translate: 'Translating…',
  summarize: 'Summarizing…',
};

const RISK_COLORS: Record<string, string> = {
  low: 'var(--color-success)',
  medium: 'var(--color-warning, #f59e0b)',
  high: 'var(--color-error, #ef4444)',
};

export function AminToolStatus({
  tools,
  subTasks,
  onConfirm,
}: AminToolStatusProps) {
  const hasContent = tools.length > 0 || (subTasks && subTasks.length > 0);
  if (!hasContent) return null;

  return (
    <div className="amin-tool-status">
      {/* Sub-task status cards */}
      {subTasks && subTasks.length > 0 && (
        <div className="amin-subtasks">
          <div className="amin-subtasks-header">Parallel Tasks</div>
          {subTasks.map((st, i) => (
            <div
              key={`st-${i}`}
              className="amin-subtask-item"
              data-status={st.status}
            >
              {st.status === 'running' && (
                <span className="amin-tool-spinner" />
              )}
              {st.status === 'complete' && <span>✓</span>}
              <span className="amin-tool-name">{st.description}</span>
              {st.summary && (
                <span className="amin-subtask-summary">{st.summary}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tool execution status */}
      {tools.map((t, i) => (
        <div
          key={`${t.tool}-${i}`}
          className="amin-tool-item"
          data-status={t.status}
        >
          {t.status === 'running' && <span className="amin-tool-spinner" />}
          {t.status === 'complete' && <span>✓</span>}
          {t.status === 'error' && <span>⚠</span>}
          {t.status === 'pending_confirmation' && <span>🔒</span>}
          <span className="amin-tool-name">{t.tool}</span>

          {t.status === 'pending_confirmation' ? (
            <div className="amin-confirmation">
              <div className="amin-confirmation-info">
                <span
                  className="amin-risk-badge"
                  style={{
                    backgroundColor: RISK_COLORS[t.riskLevel ?? 'medium'],
                  }}
                >
                  {t.riskLevel ?? 'medium'} risk
                </span>
                <span className="amin-confirmation-label">
                  Requires your approval
                </span>
              </div>
              {t.params && Object.keys(t.params).length > 0 && (
                <div className="amin-confirmation-params">
                  {Object.entries(t.params)
                    .slice(0, 3)
                    .map(([k, v]) => (
                      <div key={k} className="amin-param-row">
                        <span className="amin-param-key">{k}:</span>
                        <span className="amin-param-value">
                          {typeof v === 'string'
                            ? v.slice(0, 80)
                            : JSON.stringify(v).slice(0, 80)}
                        </span>
                      </div>
                    ))}
                </div>
              )}
              <div className="amin-confirmation-actions">
                <button
                  className="amin-confirm-btn amin-confirm-approve"
                  onClick={() => onConfirm?.(t.tool, true)}
                >
                  Approve
                </button>
                <button
                  className="amin-confirm-btn amin-confirm-deny"
                  onClick={() => onConfirm?.(t.tool, false)}
                >
                  Deny
                </button>
              </div>
            </div>
          ) : (
            <span>
              {t.status === 'running'
                ? (TOOL_LABELS[t.tool] ?? 'Working…')
                : (t.summary ?? (t.status === 'error' ? 'Failed' : 'Done'))}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
