'use client';

import { useEffect } from 'react';
import { create } from 'zustand';
import type {
  ContextPaneCardData,
  ContextPaneMode,
  ContextPanePushEventDetail,
} from './types';

interface ContextPaneState {
  mode: ContextPaneMode;
  cards: ContextPaneCardData[];
  focusedCardId: string | null;
  pushCard: (
    card: ContextPaneCardData,
    mode?: Exclude<ContextPaneMode, 'hidden'>
  ) => void;
  dismissCard: (cardId: string) => void;
  dismissAll: () => void;
  setMode: (mode: ContextPaneMode) => void;
  focusCard: (cardId: string) => void;
}

const MAX_STACK = 5;

const useContextPaneStore = create<ContextPaneState>((set, get) => ({
  mode: 'hidden',
  cards: [],
  focusedCardId: null,
  pushCard: (card, requestedMode) =>
    set(state => {
      const withoutDuplicate = state.cards.filter(
        existing => existing.id !== card.id
      );
      const nextCards = [...withoutDuplicate, card].slice(-MAX_STACK);
      const nextMode =
        requestedMode ?? (state.mode === 'hidden' ? 'top_bar' : state.mode);
      const focusedStillExists =
        state.focusedCardId !== null &&
        nextCards.some(existing => existing.id === state.focusedCardId);

      return {
        cards: nextCards,
        mode: state.mode === 'left_panel' ? 'left_panel' : nextMode,
        focusedCardId: focusedStillExists
          ? state.focusedCardId
          : (nextCards[nextCards.length - 1]?.id ?? null),
      };
    }),
  dismissCard: cardId =>
    set(state => {
      const nextCards = state.cards.filter(card => card.id !== cardId);
      if (nextCards.length === 0) {
        return { cards: [], mode: 'hidden', focusedCardId: null };
      }

      const nextFocusedCardId =
        state.focusedCardId === cardId
          ? (nextCards[0]?.id ?? null)
          : state.focusedCardId;

      return {
        cards: nextCards,
        focusedCardId: nextFocusedCardId,
      };
    }),
  dismissAll: () => set({ cards: [], mode: 'hidden', focusedCardId: null }),
  setMode: mode =>
    set(state => ({
      mode: state.cards.length === 0 ? 'hidden' : mode,
      focusedCardId: state.focusedCardId ?? state.cards[0]?.id ?? null,
    })),
  focusCard: cardId => {
    const state = get();
    if (!state.cards.some(card => card.id === cardId)) {
      return;
    }
    set({ focusedCardId: cardId, mode: 'left_panel' });
  },
}));

export function useAminContextPane() {
  const state = useContextPaneStore();

  useEffect(() => {
    const handleContextPane = (event: Event) => {
      const customEvent = event as CustomEvent<ContextPanePushEventDetail>;
      const detail = customEvent.detail;
      if (!detail?.card) return;
      state.pushCard(detail.card, detail.mode ?? 'top_bar');
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        state.dismissAll();
      }
    };

    window.addEventListener(
      'amin:context_pane',
      handleContextPane as EventListener
    );
    window.addEventListener('keydown', handleEscape);

    return () => {
      window.removeEventListener(
        'amin:context_pane',
        handleContextPane as EventListener
      );
      window.removeEventListener('keydown', handleEscape);
    };
  }, [state]);

  return state;
}

export function pushContextPaneCard(
  card: ContextPaneCardData,
  mode?: Exclude<ContextPaneMode, 'hidden'>
) {
  useContextPaneStore.getState().pushCard(card, mode);
}
