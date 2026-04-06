'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { useAmin, type AminStatus } from './useAmin';

export type VoiceMode = 'off' | 'active' | 'passive';
export type PanelSize = 'collapsed' | 'expanded' | 'fullscreen';

interface AminContextValue extends ReturnType<typeof useAmin> {
  aminOpen: boolean;
  openPanel: () => void;
  closePanel: () => void;
  toggleAminPanel: () => void;
  voiceMode: VoiceMode;
  setVoiceMode: (mode: VoiceMode) => void;
  panelSize: PanelSize;
  setPanelSize: (size: PanelSize) => void;
  floatingMessage: string | null;
  dismissFloatingMessage: () => void;
  sendGreeting: () => void;
}

const AminContext = createContext<AminContextValue | null>(null);

export function AminProvider({ children }: { children: ReactNode }) {
  const amin = useAmin();
  const [aminOpen, setAminOpen] = useState(false);
  const [voiceMode, setVoiceMode] = useState<VoiceMode>('off');
  const [panelSize, setPanelSize] = useState<PanelSize>('expanded');
  const [floatingMessage, setFloatingMessage] = useState<string | null>(null);
  const greetingSent = useState(false);

  const openPanel = useCallback(() => {
    setAminOpen(true);
    setPanelSize('expanded');
  }, []);
  const closePanel = useCallback(() => {
    setAminOpen(false);
    setPanelSize('collapsed');
  }, []);
  const toggleAminPanel = useCallback(() => {
    setAminOpen(prev => {
      if (!prev) setPanelSize('expanded');
      return !prev;
    });
  }, []);
  const dismissFloatingMessage = useCallback(
    () => setFloatingMessage(null),
    []
  );

  const sendGreeting = useCallback(async () => {
    if (greetingSent[0]) return;
    greetingSent[0] = true;
    try {
      if (!amin.activeConversation) {
        await amin.createConversation();
      }
      amin.sendMessage('__greeting__');
    } catch {
      /* */
    }
  }, [amin, greetingSent]);

  const lastMsgRef = useState('');
  const aminMessages = amin.messages;
  if (aminMessages.length > 0) {
    const last = aminMessages[aminMessages.length - 1];
    if (
      last.role === 'assistant' &&
      last.content !== lastMsgRef[0] &&
      !aminOpen
    ) {
      lastMsgRef[0] = last.content;
      if (floatingMessage !== last.content) {
        setTimeout(() => setFloatingMessage(last.content), 0);
      }
    }
  }

  return (
    <AminContext.Provider
      value={{
        ...amin,
        aminOpen,
        openPanel,
        closePanel,
        toggleAminPanel,
        voiceMode,
        setVoiceMode,
        panelSize,
        setPanelSize,
        floatingMessage,
        dismissFloatingMessage,
        sendGreeting,
      }}
    >
      {children}
    </AminContext.Provider>
  );
}

export function useAminContext(): AminContextValue {
  const ctx = useContext(AminContext);
  if (!ctx) throw new Error('useAminContext must be used within AminProvider');
  return ctx;
}
