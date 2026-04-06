'use client';

import { useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AminAvatar, type AminAvatarState } from './AminAvatar';
import { aminBreathing, voiceRingPulse } from '@/lib/motion';
import { useAminContext } from './AminProvider';
import { AminVoiceClient, setVoice } from '@/lib/aminVoiceClient';
import { WakeWordDetector } from '@/lib/wakeWordDetector';
import { useAuth } from '@/lib/AuthContext';

const RING_COLORS = {
  off: '#ef4444',
  active: '#34d399',
  passive: '#22c55e80',
};

export function AminMinimized() {
  const { aminStatus, voiceMode, setVoiceMode, openPanel, sendGreeting } =
    useAminContext();
  const { aminVoice } = useAuth();

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

    sendGreeting();

    if (aminVoice) setVoice(aminVoice);

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
  }, [setVoiceMode, enterPassive, sendGreeting, aminVoice]);

  const enterOff = useCallback(() => {
    setVoiceMode('off');
    wakeDetectorRef.current?.stop();
    voiceClientRef.current?.disconnect();
  }, [setVoiceMode]);

  const handleAvatarClick = useCallback(() => {
    if (voiceMode === 'off') {
      enterActive();
    } else {
      enterOff();
    }
  }, [voiceMode, enterActive, enterOff]);

  useEffect(() => {
    return () => {
      wakeDetectorRef.current?.stop();
      voiceClientRef.current?.disconnect();
    };
  }, []);

  const avatarState: AminAvatarState =
    voiceMode === 'active'
      ? 'listening'
      : voiceMode === 'passive'
        ? 'sleeping'
        : (aminStatus as AminAvatarState);

  return (
    <div className="amin-fab-container">
      <motion.button
        className="amin-minimized"
        onClick={handleAvatarClick}
        aria-label={voiceMode === 'off' ? 'Activate Amin' : 'Deactivate Amin'}
        type="button"
        variants={aminBreathing}
        animate="idle"
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      >
        <AminAvatar size={44} state={avatarState} showWaveform />

        {/* State indicator ring — red=off, green=on */}
        <motion.div
          className="amin-voice-ring"
          style={{
            position: 'absolute',
            inset: -4,
            borderRadius: '50%',
            border: `2px solid ${RING_COLORS[voiceMode]}`,
            pointerEvents: 'none',
          }}
          animate={{
            opacity: 1,
            scale: voiceMode === 'off' ? 1 : [1, 1.08, 1],
          }}
          transition={
            voiceMode === 'off'
              ? { duration: 0.3 }
              : { duration: 2, repeat: Infinity, ease: 'easeInOut' }
          }
        />
      </motion.button>
    </div>
  );
}
