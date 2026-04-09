'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react';
import { useAmin, type AminStatus } from './useAmin';
import { useAuth } from '@/lib/AuthContext';
import { AminVoiceClient, setLanguage, setVoice } from '@/lib/aminVoiceClient';
import { WakeWordDetector } from '@/lib/wakeWordDetector';

export type VoiceMode = 'off' | 'active' | 'passive';
export type PanelSize = 'collapsed' | 'expanded' | 'fullscreen';

const QUIET_MODE_MS = 5 * 60 * 1000;
const QUIET_COMMAND_PATTERNS = [
  /\b(be|stay|keep|go)\s+quiet\b/i,
  /\b(be|stay)\s+silent\b/i,
  /\bstop\s+(talking|speaking)\b/i,
  /\bquiet\s+down\b/i,
  /\bsilence\s+please\b/i,
  /\bgo\s+to\s+sleep\b/i,
];

function isQuietCommand(text: string): boolean {
  const normalized = text.trim().toLowerCase();
  if (!normalized) return false;
  if (normalized === 'quiet' || normalized === 'silence') return true;
  return QUIET_COMMAND_PATTERNS.some(pattern => pattern.test(normalized));
}

function formatCountdown(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

interface AminContextValue extends ReturnType<typeof useAmin> {
  aminOpen: boolean;
  openPanel: () => void;
  closePanel: () => void;
  toggleAminPanel: () => void;
  voiceMode: VoiceMode;
  setVoiceMode: (mode: VoiceMode) => void;
  activateVoice: () => void;
  deactivateVoice: () => void;
  toggleVoice: () => void;
  quietVoice: () => void;
  interruptSpeech: () => void;
  isVoiceSpeaking: boolean;
  isQuietMode: boolean;
  quietCountdownMs: number;
  quietCountdownLabel: string | null;
  panelSize: PanelSize;
  setPanelSize: (size: PanelSize) => void;
  floatingMessage: string | null;
  dismissFloatingMessage: () => void;
  sendGreeting: () => void;
}

const AminContext = createContext<AminContextValue | null>(null);

export function AminProvider({ children }: { children: ReactNode }) {
  const amin = useAmin();
  const { aminVoice, appLanguage } = useAuth();
  const [aminOpen, setAminOpen] = useState(false);
  const [voiceMode, setVoiceMode] = useState<VoiceMode>('off');
  const [quietCountdownMs, setQuietCountdownMs] = useState(0);
  const [quietUntil, setQuietUntil] = useState<number | null>(null);
  const [panelSize, setPanelSize] = useState<PanelSize>('expanded');
  const [floatingMessage, setFloatingMessage] = useState<string | null>(null);
  const [isVoiceSpeaking, setIsVoiceSpeaking] = useState(false);
  const greetingSent = useRef(false);
  const lastMsgRef = useRef('');
  const voiceClientRef = useRef<AminVoiceClient | null>(null);
  const wakeDetectorRef = useRef<WakeWordDetector | null>(null);
  const quietTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const quietIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const isFirstCaseViewToday = useCallback(() => {
    const today = new Date().toISOString().slice(0, 10);
    const key = `amin:first-case-view:${today}`;
    if (sessionStorage.getItem(key)) {
      return false;
    }
    sessionStorage.setItem(key, '1');
    return true;
  }, []);

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

  const clearQuietTimers = useCallback(() => {
    if (quietTimerRef.current) {
      clearTimeout(quietTimerRef.current);
      quietTimerRef.current = null;
    }
    if (quietIntervalRef.current) {
      clearInterval(quietIntervalRef.current);
      quietIntervalRef.current = null;
    }
  }, []);

  const clearQuietMode = useCallback(() => {
    clearQuietTimers();
    setQuietUntil(null);
    setQuietCountdownMs(0);
  }, [clearQuietTimers]);

  const stopWakeDetector = useCallback(() => {
    wakeDetectorRef.current?.stop();
  }, []);

  const startWakeDetector = useCallback(() => {
    if (!WakeWordDetector.isSupported()) return;
    if (!wakeDetectorRef.current) {
      wakeDetectorRef.current = new WakeWordDetector(() => {
        clearQuietMode();
        setVoiceMode('active');
        voiceClientRef.current?.resumeMicCapture();
      });
    }
    wakeDetectorRef.current.start();
  }, [clearQuietMode]);

  const enterPassive = useCallback(
    (options?: { quietDurationMs?: number }) => {
      setVoiceMode('passive');
      voiceClientRef.current?.pauseMicCapture();
      stopWakeDetector();

      const quietDurationMs = options?.quietDurationMs;
      if (!quietDurationMs) {
        clearQuietMode();
        startWakeDetector();
        return;
      }

      const nextQuietUntil = Date.now() + quietDurationMs;
      clearQuietTimers();
      setQuietUntil(nextQuietUntil);
      setQuietCountdownMs(quietDurationMs);

      quietIntervalRef.current = setInterval(() => {
        const remaining = Math.max(0, nextQuietUntil - Date.now());
        setQuietCountdownMs(remaining);
      }, 1000);

      quietTimerRef.current = setTimeout(() => {
        clearQuietMode();
        if (voiceClientRef.current?.connected) {
          startWakeDetector();
        }
      }, quietDurationMs);
    },
    [clearQuietMode, clearQuietTimers, startWakeDetector, stopWakeDetector]
  );

  const getVoiceClient = useCallback(() => {
    if (voiceClientRef.current) return voiceClientRef.current;

    voiceClientRef.current = new AminVoiceClient({
      onAutoIdle: () => enterPassive(),
      onStandbyRequested: () => enterPassive(),
      onAssistantSpeakingChange: speaking => {
        setIsVoiceSpeaking(speaking);
      },
      onTranscript: (text, role) => {
        if (role === 'user' && isQuietCommand(text)) {
          voiceClientRef.current?.interrupt();
          enterPassive({ quietDurationMs: QUIET_MODE_MS });
        }
      },
      onDisconnected: () => {
        clearQuietMode();
        stopWakeDetector();
        setIsVoiceSpeaking(false);
        setVoiceMode('off');
      },
      onError: err => console.warn('[AminVoice]', err),
    });

    return voiceClientRef.current;
  }, [clearQuietMode, enterPassive, stopWakeDetector]);

  const sendGreeting = useCallback(async () => {
    if (greetingSent.current) return;
    greetingSent.current = true;
    try {
      if (!amin.activeConversation) {
        await amin.createConversation();
      }
      amin.sendMessage('__greeting__');
    } catch {
      /* */
    }
  }, [amin]);

  const activateVoice = useCallback(() => {
    clearQuietMode();
    setVoiceMode('active');
    stopWakeDetector();

    sendGreeting();

    if (aminVoice) setVoice(aminVoice);
    setLanguage(appLanguage);

    const voiceClient = getVoiceClient();
    if (!voiceClient.connected) {
      void voiceClient.connect();
    } else {
      voiceClient.resumeMicCapture();
    }
  }, [
    aminVoice,
    appLanguage,
    clearQuietMode,
    getVoiceClient,
    sendGreeting,
    stopWakeDetector,
  ]);

  const deactivateVoice = useCallback(() => {
    clearQuietMode();
    setVoiceMode('off');
    setIsVoiceSpeaking(false);
    stopWakeDetector();
    voiceClientRef.current?.disconnect();
  }, [clearQuietMode, stopWakeDetector]);

  const toggleVoice = useCallback(() => {
    if (voiceMode === 'active') {
      deactivateVoice();
      return;
    }
    activateVoice();
  }, [activateVoice, deactivateVoice, voiceMode]);

  const quietVoice = useCallback(() => {
    if (voiceMode === 'off') return;
    voiceClientRef.current?.interrupt();
    enterPassive({ quietDurationMs: QUIET_MODE_MS });
  }, [enterPassive, voiceMode]);

  const interruptSpeech = useCallback(() => {
    voiceClientRef.current?.interrupt();
    if (voiceMode === 'active') {
      voiceClientRef.current?.resumeMicCapture();
    }
    setIsVoiceSpeaking(false);
  }, [voiceMode]);

  useEffect(() => {
    const aminMessages = amin.messages;
    if (aminMessages.length === 0) return;

    const last = aminMessages[aminMessages.length - 1];
    if (
      last.role === 'assistant' &&
      last.content !== lastMsgRef.current &&
      !aminOpen
    ) {
      lastMsgRef.current = last.content;
      if (floatingMessage !== last.content) {
        setFloatingMessage(last.content);
      }
    }
  }, [amin.messages, aminOpen, floatingMessage]);

  useEffect(() => {
    const handleAminContext = async (event: Event) => {
      const customEvent = event as CustomEvent<{
        message?: string;
        workflowId?: string;
      }>;
      const message = customEvent.detail?.message?.trim();
      if (!message) return;

      try {
        if (!amin.activeConversation) {
          await amin.createConversation();
        }
        amin.injectMessage('assistant', message);
      } catch {
        /* ignore */
      }
    };

    window.addEventListener('amin:context', handleAminContext as EventListener);
    window.addEventListener(
      'amin:proactive',
      handleAminContext as EventListener
    );

    return () => {
      window.removeEventListener(
        'amin:context',
        handleAminContext as EventListener
      );
      window.removeEventListener(
        'amin:proactive',
        handleAminContext as EventListener
      );
    };
  }, [amin]);

  useEffect(() => {
    const handleContextHint = async (event: Event) => {
      const customEvent = event as CustomEvent<{
        type?: string;
        case_id?: string;
        case_title?: string;
        client_name?: string;
      }>;

      if (customEvent.detail?.type !== 'case_viewed') return;

      const shouldTrigger = aminOpen || isFirstCaseViewToday();
      if (!shouldTrigger) return;

      const caseTitle = customEvent.detail.case_title ?? 'Untitled case';
      const clientName = customEvent.detail.client_name ?? 'Unknown client';

      await amin.sendSystemTrigger(
        `[SYSTEM] The user just opened case: ${caseTitle} (Client: ${clientName}). ` +
          `Show a case_card in the context pane proactively. ` +
          `Do not produce a conversational reply unless the user directly asked for one.`
      );
    };

    window.addEventListener(
      'amin:context_hint',
      handleContextHint as EventListener
    );

    return () => {
      window.removeEventListener(
        'amin:context_hint',
        handleContextHint as EventListener
      );
    };
  }, [amin, aminOpen, isFirstCaseViewToday]);

  useEffect(() => {
    return () => {
      clearQuietTimers();
      stopWakeDetector();
      voiceClientRef.current?.disconnect();
    };
  }, [clearQuietTimers, stopWakeDetector]);

  const quietCountdownLabel = useMemo(
    () => (quietUntil ? formatCountdown(quietCountdownMs) : null),
    [quietCountdownMs, quietUntil]
  );
  const isQuietMode = voiceMode === 'passive' && quietUntil !== null;

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
        activateVoice,
        deactivateVoice,
        toggleVoice,
        quietVoice,
        interruptSpeech,
        isVoiceSpeaking,
        isQuietMode,
        quietCountdownMs,
        quietCountdownLabel,
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
