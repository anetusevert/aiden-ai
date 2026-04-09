'use client';

import type { ReactNode } from 'react';
import type { ContextPaneCardData } from '../types';

function getString(
  value: Record<string, unknown>,
  key: string
): string | undefined {
  const entry = value[key];
  return typeof entry === 'string' ? entry : undefined;
}

function getNumber(
  value: Record<string, unknown>,
  key: string
): number | undefined {
  const entry = value[key];
  return typeof entry === 'number' ? entry : undefined;
}

function getObject(
  value: Record<string, unknown>,
  key: string
): Record<string, unknown> | undefined {
  const entry = value[key];
  return entry !== null && typeof entry === 'object' && !Array.isArray(entry)
    ? (entry as Record<string, unknown>)
    : undefined;
}

function getArray(value: Record<string, unknown>, key: string): unknown[] {
  const entry = value[key];
  return Array.isArray(entry) ? entry : [];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((entry): entry is string => typeof entry === 'string')
    : [];
}

function formatDate(value?: string): string {
  if (!value) return 'Not available';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatRelativeDeadline(value?: string): string {
  if (!value) return 'No deadline set';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const days = Math.ceil((date.getTime() - Date.now()) / 86_400_000);
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return 'Due today';
  if (days === 1) return 'Due in 1 day';
  return `Due in ${days} days`;
}

function initials(name?: string): string {
  if (!name) return 'A';
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase() ?? '')
    .join('');
}

function severityStyles(severity: string): {
  border: string;
  badgeBackground: string;
  badgeColor: string;
} {
  switch (severity.toLowerCase()) {
    case 'critical':
      return {
        border: 'rgba(248, 113, 113, 0.95)',
        badgeBackground: 'rgba(248, 113, 113, 0.14)',
        badgeColor: 'rgba(252, 165, 165, 0.95)',
      };
    case 'high':
      return {
        border: 'rgba(239, 68, 68, 0.8)',
        badgeBackground: 'rgba(239, 68, 68, 0.12)',
        badgeColor: 'rgba(252, 165, 165, 0.92)',
      };
    case 'medium':
      return {
        border: 'rgba(255, 255, 255, 0.22)',
        badgeBackground: 'rgba(255, 255, 255, 0.06)',
        badgeColor: 'var(--text-primary)',
      };
    default:
      return {
        border: 'rgba(255, 255, 255, 0.14)',
        badgeBackground: 'rgba(255, 255, 255, 0.05)',
        badgeColor: 'var(--text-secondary)',
      };
  }
}

function scoreColor(score: number): string {
  if (score >= 71) return 'rgba(248, 113, 113, 0.96)';
  if (score >= 31) return 'rgba(255, 255, 255, 0.88)';
  return 'rgba(52, 211, 153, 0.96)';
}

function cardTextRow(label: string, value?: string | number): ReactNode {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <span
        style={{
          fontSize: 11,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          color: 'var(--text-secondary)',
        }}
      >
        {label}
      </span>
      <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
        {value ?? '—'}
      </span>
    </div>
  );
}

function ClientCard({ card }: { card: ContextPaneCardData }) {
  const name = getString(card.data, 'name');
  const type = getString(card.data, 'type');
  const jurisdiction = getString(card.data, 'jurisdiction');
  const activeCases = getNumber(card.data, 'active_cases');
  const lastActivity = getString(card.data, 'last_activity');
  const phone = getString(card.data, 'phone');
  const email = getString(card.data, 'email');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 999,
            background: 'rgba(255,255,255,0.08)',
            color: 'var(--text-primary)',
            display: 'grid',
            placeItems: 'center',
            fontWeight: 700,
            fontSize: 16,
          }}
        >
          {initials(name)}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <strong style={{ fontSize: 15 }}>{name ?? card.title}</strong>
          {type && (
            <span
              style={{
                width: 'fit-content',
                padding: '2px 8px',
                borderRadius: 999,
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.08)',
                fontSize: 12,
                color: 'var(--text-secondary)',
              }}
            >
              {type}
            </span>
          )}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          gap: 12,
        }}
      >
        {cardTextRow('Jurisdiction', jurisdiction)}
        {cardTextRow('Active Cases', activeCases)}
        {cardTextRow('Last Activity', formatDate(lastActivity))}
        {cardTextRow('Email', email)}
        {phone ? cardTextRow('Phone', phone) : null}
      </div>
    </div>
  );
}

function CaseCard({ card }: { card: ContextPaneCardData }) {
  const status = getString(card.data, 'status') ?? 'active';
  const clientName = getString(card.data, 'client_name');
  const practiceArea = getString(card.data, 'practice_area');
  const jurisdiction = getString(card.data, 'jurisdiction');
  const nextDeadline = getString(card.data, 'next_deadline');
  const briefing = getString(card.data, 'amin_briefing');
  const priority = getString(card.data, 'priority');
  const days = nextDeadline
    ? Math.ceil((new Date(nextDeadline).getTime() - Date.now()) / 86_400_000)
    : null;
  const deadlineColor =
    days !== null && days < 3
      ? 'rgba(248, 113, 113, 0.95)'
      : 'var(--text-primary)';

  const statusStyles =
    status === 'closed'
      ? {
          color: 'rgba(161,161,170,0.86)',
          background: 'rgba(255,255,255,0.04)',
        }
      : status === 'pending'
        ? {
            color: 'rgba(212,212,216,0.92)',
            background: 'rgba(255,255,255,0.05)',
          }
        : {
            color: 'var(--text-primary)',
            background: 'rgba(255,255,255,0.08)',
          };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <strong style={{ fontSize: 15 }}>{card.title}</strong>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            {clientName ?? 'Unknown client'} · {practiceArea ?? 'General'} ·{' '}
            {jurisdiction ?? 'GCC'}
          </span>
        </div>
        <span
          style={{
            alignSelf: 'flex-start',
            padding: '4px 8px',
            borderRadius: 999,
            fontSize: 12,
            textTransform: 'capitalize',
            ...statusStyles,
          }}
        >
          {status}
        </span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          gap: 12,
        }}
      >
        <div
          style={{
            padding: 12,
            borderRadius: 12,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-secondary)',
              marginBottom: 4,
            }}
          >
            Next Deadline
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: deadlineColor }}>
            {formatRelativeDeadline(nextDeadline)}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            {formatDate(nextDeadline)}
          </div>
        </div>
        <div
          style={{
            padding: 12,
            borderRadius: 12,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          <div
            style={{
              fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--text-secondary)',
              marginBottom: 4,
            }}
          >
            Priority
          </div>
          <div style={{ fontSize: 18, fontWeight: 700 }}>
            {priority ?? 'Normal'}
          </div>
        </div>
      </div>

      {briefing && (
        <p
          style={{
            margin: 0,
            fontSize: 13,
            lineHeight: 1.6,
            color: 'var(--text-secondary)',
            fontStyle: 'italic',
          }}
        >
          {briefing}
        </p>
      )}
    </div>
  );
}

function RiskCard({ card }: { card: ContextPaneCardData }) {
  const documentTitle = getString(card.data, 'document_title');
  const overallScore = getNumber(card.data, 'overall_score') ?? 0;
  const items = getArray(card.data, 'items')
    .map(asRecord)
    .filter((item): item is Record<string, unknown> => item !== null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <div
          style={{
            width: 80,
            height: 80,
            borderRadius: 999,
            border: '1px solid rgba(255,255,255,0.1)',
            display: 'grid',
            placeItems: 'center',
            color: scoreColor(overallScore),
            fontWeight: 700,
            fontSize: 24,
            flexShrink: 0,
          }}
        >
          {overallScore}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <strong style={{ fontSize: 15 }}>
            {documentTitle ?? card.title}
          </strong>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            Overall risk score
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {items.map((item, index) => {
          const severity = getString(item, 'severity') ?? 'low';
          const title = getString(item, 'title') ?? `Risk ${index + 1}`;
          const article = getString(item, 'article');
          const recommendation = getString(item, 'recommendation');
          const styles = severityStyles(severity);

          return (
            <div
              key={`${title}-${index}`}
              style={{
                paddingLeft: 12,
                borderLeft: `2px solid ${styles.border}`,
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  flexWrap: 'wrap',
                }}
              >
                <strong style={{ fontSize: 14 }}>{title}</strong>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: 999,
                    background: styles.badgeBackground,
                    color: styles.badgeColor,
                    fontSize: 11,
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  {severity}
                </span>
              </div>
              {article && (
                <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {article}
                </span>
              )}
              {recommendation && (
                <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>
                  {recommendation}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ResearchCard({ card }: { card: ContextPaneCardData }) {
  const query = getString(card.data, 'query');
  const findings = getArray(card.data, 'findings')
    .map(asRecord)
    .filter((item): item is Record<string, unknown> => item !== null);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {query && (
        <p
          style={{
            margin: 0,
            color: 'var(--text-secondary)',
            fontStyle: 'italic',
            fontSize: 13,
          }}
        >
          {query}
        </p>
      )}
      {findings.map((finding, index) => {
        const title = getString(finding, 'title') ?? `Finding ${index + 1}`;
        const source = getString(finding, 'source');
        const excerpt = getString(finding, 'excerpt');
        const citation = getString(finding, 'citation');

        return (
          <div
            key={`${title}-${index}`}
            style={{
              borderLeft: '2px solid rgba(255,255,255,0.12)',
              paddingLeft: 12,
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            <strong style={{ fontSize: 14 }}>{title}</strong>
            {source && (
              <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                {source}
              </span>
            )}
            {excerpt && (
              <span style={{ color: 'var(--text-primary)', fontSize: 13 }}>
                {excerpt}
              </span>
            )}
            {citation && (
              <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                {citation}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function RegulatoryCard({ card }: { card: ContextPaneCardData }) {
  const name = getString(card.data, 'name') ?? card.title;
  const authority = getString(card.data, 'authority');
  const effectiveDate = getString(card.data, 'effective_date');
  const provisions = getArray(card.data, 'provisions')
    .map(asRecord)
    .filter((item): item is Record<string, unknown> => item !== null);
  const implications = getArray(card.data, 'implications').filter(
    (entry): entry is string => typeof entry === 'string'
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div
        style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <strong style={{ fontSize: 15 }}>{name}</strong>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            Effective {formatDate(effectiveDate)}
          </span>
        </div>
        {authority && (
          <span
            style={{
              alignSelf: 'flex-start',
              padding: '4px 8px',
              borderRadius: 999,
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.08)',
              fontSize: 12,
              color: 'var(--text-secondary)',
            }}
          >
            {authority}
          </span>
        )}
      </div>

      <ol style={{ margin: 0, paddingLeft: 18, display: 'grid', gap: 8 }}>
        {provisions.map((item, index) => {
          const article = getString(item, 'article');
          const text = getString(item, 'text');
          return (
            <li key={`${article ?? 'article'}-${index}`}>
              <span style={{ fontWeight: 700 }}>
                {article ? `${article}: ` : ''}
              </span>
              <span style={{ color: 'var(--text-primary)', fontSize: 13 }}>
                {text ?? 'Provision summary unavailable.'}
              </span>
            </li>
          );
        })}
      </ol>

      {implications.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <strong style={{ fontSize: 13 }}>Compliance implications</strong>
          {implications.map((implication, index) => (
            <span
              key={`${implication}-${index}`}
              style={{ color: 'var(--text-secondary)', fontSize: 13 }}
            >
              {index + 1}. {implication}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function PriorityMatrixCard({ card }: { card: ContextPaneCardData }) {
  const tasks = getArray(card.data, 'tasks')
    .map(asRecord)
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(task => ({
      title: getString(task, 'title') ?? 'Untitled task',
      urgency: Boolean(task.urgency),
      impact: getString(task, 'impact') === 'high' ? 'high' : 'low',
      caseTitle: getString(task, 'case_title'),
    }));

  const quadrants = [
    {
      id: 'urgent-high',
      label: 'Urgent · High Impact',
      items: tasks
        .filter(task => task.urgency && task.impact === 'high')
        .slice(0, 3),
      color: 'var(--text-primary)',
    },
    {
      id: 'urgent-low',
      label: 'Urgent · Low Impact',
      items: tasks
        .filter(task => task.urgency && task.impact === 'low')
        .slice(0, 3),
      color: 'rgba(228,228,231,0.92)',
    },
    {
      id: 'not-urgent-high',
      label: 'Not Urgent · High Impact',
      items: tasks
        .filter(task => !task.urgency && task.impact === 'high')
        .slice(0, 3),
      color: 'rgba(212,212,216,0.92)',
    },
    {
      id: 'not-urgent-low',
      label: 'Not Urgent · Low Impact',
      items: tasks
        .filter(task => !task.urgency && task.impact === 'low')
        .slice(0, 3),
      color: 'rgba(113,113,122,0.9)',
    },
  ];

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: 10,
      }}
    >
      {quadrants.map(quadrant => (
        <div
          key={quadrant.id}
          style={{
            padding: 12,
            borderRadius: 12,
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.06)',
            minHeight: 132,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <strong style={{ fontSize: 12, color: quadrant.color }}>
            {quadrant.label}
          </strong>
          {quadrant.items.length === 0 ? (
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              No tasks
            </span>
          ) : (
            quadrant.items.map(item => (
              <div
                key={`${quadrant.id}-${item.title}`}
                style={{ display: 'flex', flexDirection: 'column', gap: 2 }}
              >
                <span style={{ fontSize: 13, color: quadrant.color }}>
                  {item.title}
                </span>
                {item.caseTitle && (
                  <span
                    style={{ fontSize: 11, color: 'var(--text-secondary)' }}
                  >
                    {item.caseTitle}
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      ))}
    </div>
  );
}

function ComparisonCard({ card }: { card: ContextPaneCardData }) {
  const left = getObject(card.data, 'left');
  const right = getObject(card.data, 'right');
  const leftLabel = left ? getString(left, 'label') : undefined;
  const rightLabel = right ? getString(right, 'label') : undefined;
  const leftItems = left ? asStringArray(left['items']) : [];
  const rightItems = right ? asStringArray(right['items']) : [];
  const maxRows = Math.max(leftItems.length, rightItems.length);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: 12,
      }}
    >
      {[leftLabel ?? 'Left', rightLabel ?? 'Right'].map(
        (label, columnIndex) => (
          <div
            key={label}
            style={{
              paddingLeft: columnIndex === 1 ? 12 : 0,
              borderLeft:
                columnIndex === 1 ? '1px solid rgba(255,255,255,0.08)' : 'none',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}
          >
            <strong style={{ fontSize: 13 }}>{label}</strong>
            {Array.from({ length: maxRows }).map((_, rowIndex) => {
              const leftItem = leftItems[rowIndex];
              const rightItem = rightItems[rowIndex];
              const currentItem = columnIndex === 0 ? leftItem : rightItem;
              const comparisonItem = columnIndex === 0 ? rightItem : leftItem;
              const differs = currentItem !== comparisonItem;

              return (
                <div
                  key={`${label}-${rowIndex}`}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 10,
                    background: differs
                      ? 'rgba(255,255,255,0.06)'
                      : 'rgba(255,255,255,0.03)',
                    color: differs
                      ? 'var(--text-primary)'
                      : 'var(--text-secondary)',
                    fontSize: 13,
                  }}
                >
                  {currentItem ?? '—'}
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}

function BasicTextCard({ card }: { card: ContextPaneCardData }) {
  const body = getString(card.data, 'body') ?? getString(card.data, 'text');
  const items = getArray(card.data, 'items').filter(
    (entry): entry is string => typeof entry === 'string'
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {body && (
        <p style={{ margin: 0, color: 'var(--text-primary)', fontSize: 13 }}>
          {body}
        </p>
      )}
      {items.map((item, index) => (
        <span
          key={`${item}-${index}`}
          style={{ color: 'var(--text-secondary)', fontSize: 13 }}
        >
          {index + 1}. {item}
        </span>
      ))}
    </div>
  );
}

export function getCardPreviewValue(card: ContextPaneCardData): string {
  switch (card.type) {
    case 'client_card':
      return getString(card.data, 'jurisdiction') ?? 'Client details';
    case 'case_card':
      return formatRelativeDeadline(getString(card.data, 'next_deadline'));
    case 'risk_card':
      return `Risk ${getNumber(card.data, 'overall_score') ?? 0}`;
    case 'research_card':
      return `${getArray(card.data, 'findings').length} findings`;
    case 'regulatory_card':
      return getString(card.data, 'authority') ?? 'Regulatory update';
    case 'priority_matrix':
      return `${getArray(card.data, 'tasks').length} tasks`;
    case 'comparison_card':
      return getString(card.data, 'title') ?? 'Comparison';
    case 'document_card':
      return getString(card.data, 'document_type') ?? 'Document';
    default:
      return card.subtitle ?? 'Open details';
  }
}

export function renderContextPaneCardContent(
  card: ContextPaneCardData
): ReactNode {
  switch (card.type) {
    case 'client_card':
      return <ClientCard card={card} />;
    case 'case_card':
      return <CaseCard card={card} />;
    case 'risk_card':
      return <RiskCard card={card} />;
    case 'research_card':
      return <ResearchCard card={card} />;
    case 'regulatory_card':
      return <RegulatoryCard card={card} />;
    case 'priority_matrix':
      return <PriorityMatrixCard card={card} />;
    case 'comparison_card':
      return <ComparisonCard card={card} />;
    default:
      return <BasicTextCard card={card} />;
  }
}
