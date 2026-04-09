'use client';

import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { motionTokens } from '@/lib/motion';
import { getCardPreviewValue } from './cards/renderers';
import type { ContextPaneCardData } from './types';

interface TopBarPaneProps {
  cards: ContextPaneCardData[];
  onDismissCard: (cardId: string) => void;
  onDismissAll: () => void;
  onExpandCard: (cardId: string) => void;
  onHeightChange: (height: number) => void;
}

function CardPill({
  card,
  onDismiss,
  onExpand,
}: {
  card: ContextPaneCardData;
  onDismiss: (cardId: string) => void;
  onExpand: (cardId: string) => void;
}) {
  return (
    <motion.button
      layout
      type="button"
      onClick={() => onExpand(card.id)}
      initial={{ y: -20, opacity: 0 }}
      animate={{
        y: 0,
        opacity: 1,
        transition: {
          duration: 0.3,
          ease: motionTokens.ease,
        },
      }}
      exit={{
        y: -12,
        opacity: 0,
        scale: 0.9,
        transition: {
          duration: motionTokens.duration.fast,
          ease: motionTokens.ease,
        },
      }}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 10,
        borderRadius: 999,
        border: '1px solid rgba(255,255,255,0.1)',
        background: 'rgba(255,255,255,0.05)',
        padding: '10px 12px',
        color: 'var(--text-primary)',
        cursor: 'pointer',
        flexShrink: 0,
      }}
    >
      <span
        aria-hidden
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: 'rgba(255,255,255,0.72)',
          flexShrink: 0,
        }}
      />
      <span
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-start',
          minWidth: 0,
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600 }}>{card.title}</span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {getCardPreviewValue(card)}
        </span>
      </span>
      <span
        onClick={event => {
          event.stopPropagation();
          onDismiss(card.id);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={event => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            onDismiss(card.id);
          }
        }}
        style={{
          marginLeft: 4,
          color: 'var(--text-secondary)',
          lineHeight: 1,
        }}
      >
        ×
      </span>
    </motion.button>
  );
}

export function TopBarPane({
  cards,
  onDismissCard,
  onDismissAll,
  onExpandCard,
  onHeightChange,
}: TopBarPaneProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const updateHeight = () =>
      onHeightChange(element.getBoundingClientRect().height);
    updateHeight();

    const observer = new ResizeObserver(updateHeight);
    observer.observe(element);

    return () => {
      observer.disconnect();
      onHeightChange(0);
    };
  }, [onHeightChange]);

  return (
    <motion.div
      ref={ref}
      initial={{ y: -20, opacity: 0 }}
      animate={{
        y: 0,
        opacity: 1,
        transition: {
          duration: 0.3,
          ease: motionTokens.ease,
        },
      }}
      exit={{
        y: -16,
        opacity: 0,
        transition: {
          duration: motionTokens.duration.fast,
          ease: motionTokens.ease,
        },
      }}
      style={{
        position: 'fixed',
        top: 'var(--topbar-height)',
        left: 'var(--rail1-width, 52px)',
        right: 0,
        zIndex: 40,
        minHeight: 60,
        maxHeight: 200,
        background: 'var(--bg-surface)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        overflow: 'hidden',
      }}
    >
      <motion.div
        aria-hidden
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: 1,
          bottom: 0,
          background:
            'linear-gradient(to bottom, transparent, rgba(255,255,255,0.15), transparent)',
          backgroundSize: '100% 220%',
        }}
        animate={{ backgroundPositionY: ['0%', '50%', '100%'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: '12px 16px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexShrink: 0,
          }}
        >
          <span
            aria-hidden
            style={{
              width: 8,
              height: 8,
              borderRadius: 999,
              background: 'var(--text-primary)',
              boxShadow: '0 0 10px rgba(255,255,255,0.3)',
            }}
          />
          <span
            style={{
              fontSize: 12,
              letterSpacing: '0.16em',
              color: 'var(--text-secondary)',
            }}
          >
            AMIN
          </span>
        </div>

        <div
          className="amin-context-topbar-pills"
          style={{
            flex: 1,
            minWidth: 0,
            overflowX: 'auto',
            overflowY: 'hidden',
            whiteSpace: 'nowrap',
            display: 'flex',
            gap: 10,
            paddingBottom: 2,
          }}
        >
          <AnimatePresence initial={false}>
            {cards.map(card => (
              <CardPill
                key={card.id}
                card={card}
                onDismiss={onDismissCard}
                onExpand={onExpandCard}
              />
            ))}
          </AnimatePresence>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            flexShrink: 0,
          }}
        >
          <button
            type="button"
            onClick={() => onExpandCard(cards[0]?.id ?? '')}
            style={{
              border: 0,
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 16,
            }}
            aria-label="Expand context pane"
          >
            ↓
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
    </motion.div>
  );
}
