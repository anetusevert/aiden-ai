'use client';

import { useMemo } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { resolveApiUrl } from '@/lib/api';
import { motionTokens } from '@/lib/motion';
import {
  renderContextPaneCardContent,
  getCardPreviewValue,
} from './cards/renderers';
import type { ContextPaneCardAction, ContextPaneCardData } from './types';

interface ContextPaneCardProps {
  card: ContextPaneCardData;
  expanded: boolean;
  onToggleExpand: (cardId: string) => void;
  onDismiss: (cardId: string) => void;
}

function getStringParam(
  params: Record<string, unknown> | undefined,
  key: string
): string | null {
  const value = params?.[key];
  return typeof value === 'string' ? value : null;
}

function CardTypeIcon({ type }: { type: ContextPaneCardData['type'] }) {
  const label = useMemo(() => {
    switch (type) {
      case 'client_card':
        return 'CL';
      case 'case_card':
        return 'CS';
      case 'research_card':
        return 'RS';
      case 'risk_card':
        return 'RK';
      case 'timeline_card':
        return 'TL';
      case 'comparison_card':
        return 'CP';
      case 'document_card':
        return 'DC';
      case 'regulatory_card':
        return 'RG';
      case 'priority_matrix':
        return 'PM';
      default:
        return 'AM';
    }
  }, [type]);

  return (
    <div
      aria-hidden
      style={{
        width: 28,
        height: 28,
        borderRadius: 999,
        background: 'rgba(255,255,255,0.08)',
        border: '1px solid rgba(255,255,255,0.08)',
        color: 'var(--text-secondary)',
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: '0.08em',
        display: 'grid',
        placeItems: 'center',
        flexShrink: 0,
      }}
    >
      {label}
    </div>
  );
}

async function handleCardAction(action: ContextPaneCardAction) {
  switch (action.event) {
    case 'navigate': {
      const path = getStringParam(action.params, 'path');
      if (!path) return;
      window.dispatchEvent(
        new CustomEvent('amin:navigate', {
          detail: { path, message: '' },
        })
      );
      return;
    }
    case 'send_to_amin': {
      const text = getStringParam(action.params, 'text');
      if (!text) return;
      window.dispatchEvent(
        new CustomEvent('amin-prefill', {
          detail: { text },
        })
      );
      return;
    }
    case 'open_document': {
      const docId = getStringParam(action.params, 'doc_id');
      if (!docId) return;
      window.dispatchEvent(
        new CustomEvent('amin:navigate', {
          detail: { path: `/documents/${docId}`, message: '' },
        })
      );
      return;
    }
    case 'file_to_case': {
      const caseId = getStringParam(action.params, 'case_id');
      if (!caseId) return;
      await fetch(resolveApiUrl(`/api/v1/cases/${caseId}/events`), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title:
            getStringParam(action.params, 'title') ??
            'Filed from Amin context pane',
          description:
            getStringParam(action.params, 'description') ??
            getStringParam(action.params, 'content') ??
            action.label,
          type: getStringParam(action.params, 'event_type') ?? 'amin_action',
        }),
      }).catch(() => undefined);
      return;
    }
    case 'run_workflow': {
      const category = getStringParam(action.params, 'category');
      const workflowId = getStringParam(action.params, 'workflowId');
      if (!category || !workflowId) return;
      window.dispatchEvent(
        new CustomEvent('amin:navigate', {
          detail: {
            path: `/workflows/${category}/${workflowId}`,
            message: '',
          },
        })
      );
      return;
    }
    default:
      return;
  }
}

export function ContextPaneCard({
  card,
  expanded,
  onToggleExpand,
  onDismiss,
}: ContextPaneCardProps) {
  const preview = getCardPreviewValue(card);
  const actions = card.actions ?? [];

  return (
    <motion.section
      layout
      layoutId={card.id}
      initial={{ x: 0, opacity: 0, scale: 0.98 }}
      animate={{ x: 0, opacity: 1, scale: 1 }}
      exit={{
        x: 20,
        opacity: 0,
        scale: 0.95,
        transition: { duration: 0.2, ease: motionTokens.ease },
      }}
      style={{
        borderRadius: 16,
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <button
          type="button"
          onClick={() => onToggleExpand(card.id)}
          style={{
            background: 'transparent',
            border: 0,
            padding: 0,
            margin: 0,
            color: 'inherit',
            display: 'flex',
            gap: 12,
            alignItems: 'flex-start',
            textAlign: 'left',
            width: '100%',
            cursor: 'pointer',
          }}
        >
          <CardTypeIcon type={card.type} />
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
              minWidth: 0,
            }}
          >
            <strong
              style={{
                fontSize: 14,
                color: 'var(--text-primary)',
              }}
            >
              {card.title}
            </strong>
            <span
              style={{
                fontSize: 13,
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
              }}
            >
              {expanded ? (card.subtitle ?? preview) : preview}
            </span>
          </div>
        </button>

        <button
          type="button"
          aria-label={`Dismiss ${card.title}`}
          onClick={() => onDismiss(card.id)}
          style={{
            border: 0,
            background: 'transparent',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: 0,
          }}
        >
          ×
        </button>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="expanded"
            initial={{ opacity: 0, height: 0 }}
            animate={{
              opacity: 1,
              height: 'auto',
              transition: {
                duration: motionTokens.duration.base,
                ease: motionTokens.ease,
              },
            }}
            exit={{
              opacity: 0,
              height: 0,
              transition: {
                duration: motionTokens.duration.fast,
                ease: motionTokens.ease,
              },
            }}
            style={{
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
            }}
          >
            <div>{renderContextPaneCardContent(card)}</div>

            {actions.length > 0 && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 8,
                  paddingTop: 12,
                  borderTop: '1px solid rgba(255,255,255,0.08)',
                }}
              >
                {actions.map((action, index) => (
                  <div
                    key={`${card.id}-${action.label}-${index}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    {index > 0 && (
                      <span style={{ color: 'var(--text-secondary)' }}>·</span>
                    )}
                    <button
                      type="button"
                      onClick={() => void handleCardAction(action)}
                      style={{
                        border: 0,
                        background: 'transparent',
                        color: 'var(--text-secondary)',
                        fontSize: 13,
                        cursor: 'pointer',
                        padding: 0,
                      }}
                    >
                      {action.label}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
