'use client';

import { useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { voiceRingPulse } from '@/lib/motion';
import { useAminContext } from './AminProvider';
import { AminVoiceClient } from '@/lib/aminVoiceClient';
import { WakeWordDetector } from '@/lib/wakeWordDetector';

export type VoiceMode = 'off' | 'active' | 'passive';

const RING_COLORS: Record<VoiceMode, string> = {
  off: 'transparent',
  active: 'var(--status-success, #34d399)',
  passive: 'var(--status-info, #63b4ff)',
};

export function AminVoiceToggle() {
  const { voiceMode, setVoiceMode } = useAminContext();
  const voiceClientRef = useRef<AminVoiceClient | null>(null);
  const wakeDetectorRef = useRef<WakeWordDetector | null>(null);

  const enterPassive = useCallback(() => {
    setVoiceMode('passive');
    voiceClientRef.current?.pauseMicCapture();
    if (WakeWordDetector.isSupported()) {
      if (!wakeDetectorRef.current) {
        wakeDetectorRef.current = new WakeWordDetector(() => {
          setVoiceMode('active');
          voiceClientRef.current?.resumeMicCapture();
        });
      }
      wakeDetectorRef.current.start();
    }
  }, [setVoiceMode]);

  const enterActive = useCallback(() => {
    setVoiceMode('active');
    wakeDetectorRef.current?.stop();

    if (!voiceClientRef.current) {
      voiceClientRef.current = new AminVoiceClient({
        onAutoIdle: () => enterPassive(),
        onStandbyRequested: () => enterPassive(),
        onDisconnected: () => setVoiceMode('off'),
        onError: err => console.warn('[AminVoice]', err),
      });
    }

    if (!voiceClientRef.current.connected) {
      void voiceClientRef.current.connect();
    } else {
      voiceClientRef.current.resumeMicCapture();
    }
  }, [setVoiceMode, enterPassive]);

  const enterOff = useCallback(() => {
    setVoiceMode('off');
    wakeDetectorRef.current?.stop();
    voiceClientRef.current?.disconnect();
  }, [setVoiceMode]);

  const cycleMode = useCallback(() => {
    if (voiceMode === 'off') {
      enterActive();
    } else if (voiceMode === 'active') {
      enterPassive();
    } else {
      enterOff();
    }
  }, [voiceMode, enterActive, enterPassive, enterOff]);

  useEffect(() => {
    return () => {
      wakeDetectorRef.current?.stop();
      voiceClientRef.current?.disconnect();
    };
  }, []);

  return (
    <motion.button
      className="amin-voice-toggle"
      data-mode={voiceMode}
      onClick={cycleMode}
      aria-label={`Voice mode: ${voiceMode}`}
      whileHover={{ scale: 1.08 }}
      whileTap={{ scale: 0.92 }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
    >
      <AnimatePresence>
        {voiceMode !== 'off' && (
          <motion.div
            className="amin-voice-ring"
            style={{ border: `2px solid ${RING_COLORS[voiceMode]}` }}
            variants={voiceRingPulse}
            initial="off"
            animate={voiceMode}
            exit="off"
          />
        )}
      </AnimatePresence>

      {voiceMode === 'off' ? (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="1" y1="1" x2="23" y2="23" />
          <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
          <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .76-.13 1.49-.36 2.18" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      ) : (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      )}
    </motion.button>
  );
}
