'use client';

import { AnimatePresence, LayoutGroup, motion } from 'framer-motion';
import { motionTokens } from '@/lib/motion';
import { ContextPaneCard } from './ContextPaneCard';
import type { ContextPaneCardData } from './types';

interface LeftPanelPaneProps {
  cards: ContextPaneCardData[];
  focusedCardId: string | null;
  onDismissCard: (cardId: string) => void;
  onDismissAll: () => void;
  onCollapse: () => void;
  onExpandCard: (cardId: string) => void;
}

export function LeftPanelPane({
  cards,
  focusedCardId,
  onDismissCard,
  onDismissAll,
  onCollapse,
  onExpandCard,
}: LeftPanelPaneProps) {
  const expandedCardId = focusedCardId ?? cards[0]?.id ?? null;

  return (
    <motion.aside
      initial={{ x: -360 }}
      animate={{
        x: 0,
        transition: {
          duration: 0.35,
          ease: motionTokens.ease,
        },
      }}
      exit={{
        x: -360,
        transition: {
          duration: motionTokens.duration.fast,
          ease: motionTokens.ease,
        },
      }}
      style={{
        width: 360,
        flexShrink: 0,
        height: '100%',
        background: 'var(--bg-surface)',
        borderRight: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          padding: '16px 16px 14px',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <strong style={{ fontSize: 14 }}>AMIN · Context</strong>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Structured matter context
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            type="button"
            onClick={onCollapse}
            style={{
              border: 0,
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 16,
            }}
            aria-label="Collapse context pane"
          >
            ←
          </button>
          <button
            type="button"
            onClick={onDismissAll}
            style={{
              border: 0,
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 18,
            }}
            aria-label="Dismiss all context cards"
          >
            ×
          </button>
        </div>
      </div>

      <div
        className="amin-context-scroll"
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          scrollbarWidth: 'thin',
        }}
      >
        <LayoutGroup>
          <AnimatePresence initial={false}>
            {cards.map(card => (
              <ContextPaneCard
                key={card.id}
                card={card}
                expanded={card.id === expandedCardId}
                onDismiss={onDismissCard}
                onToggleExpand={onExpandCard}
              />
            ))}
          </AnimatePresence>
        </LayoutGroup>
      </div>
    </motion.aside>
  );
}
