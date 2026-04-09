'use client';

import { useCallback, useState, type ReactNode } from 'react';
import { AnimatePresence, LayoutGroup } from 'framer-motion';
import { LeftPanelPane } from './LeftPanelPane';
import { TopBarPane } from './TopBarPane';
import { useAminContextPane } from './useAminContextPane';
import type { ContextPaneCardData } from './types';

export type { ContextPaneCardData, ContextPaneMode } from './types';

interface AminContextPaneProps {
  children: ReactNode;
}

export function AminContextPane({ children }: AminContextPaneProps) {
  const {
    mode,
    cards,
    focusedCardId,
    dismissCard,
    dismissAll,
    setMode,
    focusCard,
  } = useAminContextPane();
  const [topBarHeight, setTopBarHeight] = useState(0);

  const handleExpandCard = useCallback(
    (cardId: string) => {
      if (!cardId) return;
      focusCard(cardId);
    },
    [focusCard]
  );

  const content = (
    <div
      style={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        overflow: 'hidden',
        paddingTop: mode === 'top_bar' ? topBarHeight : 0,
      }}
    >
      {children}
    </div>
  );

  if (cards.length === 0 || mode === 'hidden') {
    return (
      <div
        style={{
          display: 'flex',
          flex: 1,
          minWidth: 0,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {content}
      </div>
    );
  }

  return (
    <LayoutGroup>
      <AnimatePresence initial={false}>
        {mode === 'top_bar' && (
          <TopBarPane
            cards={cards}
            onDismissCard={dismissCard}
            onDismissAll={dismissAll}
            onExpandCard={handleExpandCard}
            onHeightChange={setTopBarHeight}
          />
        )}
      </AnimatePresence>

      <div
        style={{
          display: 'flex',
          flex: 1,
          minWidth: 0,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        <AnimatePresence initial={false}>
          {mode === 'left_panel' && (
            <LeftPanelPane
              cards={cards}
              focusedCardId={focusedCardId}
              onDismissCard={dismissCard}
              onDismissAll={dismissAll}
              onCollapse={() => setMode('top_bar')}
              onExpandCard={handleExpandCard}
            />
          )}
        </AnimatePresence>
        {content}
      </div>
    </LayoutGroup>
  );
}
