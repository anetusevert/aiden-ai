'use client';

import { useCallback } from 'react';
import { motion } from 'framer-motion';
import { AminAvatar, type AminAvatarState } from './AminAvatar';
import { aminBreathing } from '@/lib/motion';
import { useAminContext } from './AminProvider';

const RING_COLORS = {
  off: 'rgba(255,255,255,0.25)',
  active: 'rgba(255,255,255,0.5)',
  passive: 'rgba(255,255,255,0.15)',
};

export function AminMinimized() {
  const {
    aminStatus,
    voiceMode,
    toggleVoice,
    quietVoice,
    interruptSpeech,
    isVoiceSpeaking,
    isQuietMode,
    quietCountdownLabel,
  } = useAminContext();

  const handleAvatarClick = useCallback(() => {
    if (voiceMode === 'active' && isVoiceSpeaking) {
      interruptSpeech();
      return;
    }
    toggleVoice();
  }, [interruptSpeech, isVoiceSpeaking, toggleVoice, voiceMode]);

  const avatarState: AminAvatarState =
    voiceMode === 'active'
      ? 'listening'
      : voiceMode === 'passive'
        ? 'sleeping'
        : (aminStatus as AminAvatarState);

  return (
    <div className="amin-fab-container">
      <div className="amin-fab-row">
        {isQuietMode ? (
          <button
            type="button"
            className="amin-quiet-chip amin-quiet-chip--countdown"
            onClick={toggleVoice}
            aria-label={`Amin is quiet for ${quietCountdownLabel}. Click to wake Amin.`}
          >
            <span className="amin-quiet-chip-icon" aria-hidden>
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="8" />
                <path d="M12 7v5l3 2" />
                <path d="M9 2h6" />
              </svg>
            </span>
            <span className="amin-quiet-chip-label">Quiet</span>
            <span className="amin-quiet-chip-time">{quietCountdownLabel}</span>
          </button>
        ) : voiceMode !== 'off' ? (
          <button
            type="button"
            className="amin-quiet-chip"
            onClick={isVoiceSpeaking ? interruptSpeech : quietVoice}
            aria-label={
              isVoiceSpeaking
                ? 'Interrupt Amin while speaking'
                : 'Ask Amin to stay quiet'
            }
          >
            <span className="amin-quiet-chip-icon" aria-hidden>
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="8" />
                <path d="M12 7v5l3 2" />
                <path d="M9 2h6" />
              </svg>
            </span>
            <span className="amin-quiet-chip-label">
              {isVoiceSpeaking ? 'Stop' : 'Quiet'}
            </span>
          </button>
        ) : null}

        <motion.button
          className="amin-minimized"
          onClick={handleAvatarClick}
          aria-label={
            voiceMode === 'off'
              ? 'Activate Amin'
              : voiceMode === 'active'
                ? isVoiceSpeaking
                  ? 'Interrupt Amin'
                  : 'Deactivate Amin'
                : 'Wake Amin'
          }
          type="button"
          variants={aminBreathing}
          animate="idle"
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        >
          <AminAvatar size={44} state={avatarState} showWaveform />

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
    </div>
  );
}
