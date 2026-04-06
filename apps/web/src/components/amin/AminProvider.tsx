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
}

const AminContext = createContext<AminContextValue | null>(null);

export function AminProvider({ children }: { children: ReactNode }) {
  const amin = useAmin();
  const [aminOpen, setAminOpen] = useState(false);
  const [voiceMode, setVoiceMode] = useState<VoiceMode>('off');
  const [panelSize, setPanelSize] = useState<PanelSize>('expanded');

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
