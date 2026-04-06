'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AminWaveform } from './AminWaveform';
import { AminThinkingDots } from './AminThinkingDots';
import { AminSleepIndicator } from './AminSleepIndicator';
import { AminEyes } from './AminEyes';
import { AminAnimatedAvatar } from './AminAnimatedAvatar';

export type AminAvatarState =
  | 'idle'
  | 'thinking'
  | 'speaking'
  | 'listening'
  | 'sleeping'
  | 'success';

interface AminAvatarProps {
  size?: number;
  state?: AminAvatarState;
  showWaveform?: boolean;
  className?: string;
}

// Ring colors — white spectrum
const RING_COLORS: Record<AminAvatarState, string> = {
  idle: 'rgba(255,255,255,0.25)',
  thinking: 'rgba(255,255,255,0.6)',
  speaking: '#ffffff',
  listening: 'rgba(255,255,255,0.5)',
  sleeping: 'rgba(255,255,255,0.08)',
  success: '#ffffff',
};

const GLOW_COLORS: Record<AminAvatarState, string> = {
  idle: 'rgba(255,255,255,0.12)',
  thinking: 'rgba(255,255,255,0.35)',
  speaking: 'rgba(255,255,255,0.45)',
  listening: 'rgba(255,255,255,0.28)',
  sleeping: 'rgba(255,255,255,0.06)',
  success: 'rgba(255,255,255,0.5)',
};

export function AminAvatar({
  size = 56,
  state = 'idle',
  showWaveform = true,
  className,
}: AminAvatarProps) {
  const [internalState, setInternalState] = useState<AminAvatarState>(state);

  useEffect(() => {
    setInternalState(state);
    if (state === 'success') {
      const timer = setTimeout(() => setInternalState('idle'), 2000);
      return () => clearTimeout(timer);
    }
  }, [state]);

  const s = internalState;

  // ── Image animation ──────────────────────────────────────────
  const imgAnimate = (() => {
    if (s === 'idle') return {};
    if (s === 'thinking') return { rotate: [0, -1.5, 0, 1.5, 0] };
    if (s === 'speaking') return { scale: [1, 1.015, 1, 1.015, 1] };
    if (s === 'listening') return { scale: 1.015 };
    if (s === 'sleeping') return { scale: [0.97, 0.99, 0.97], opacity: 0.85 };
    if (s === 'success') return { y: [0, -10, 0], scale: [1, 1.05, 1.0] };
    return {};
  })();

  const imgTransition = (() => {
    if (s === 'thinking')
      return { duration: 2, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'speaking')
      return { duration: 0.6, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'listening')
      return { type: 'spring' as const, stiffness: 200, damping: 20 };
    if (s === 'sleeping')
      return { duration: 4, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'success')
      return { type: 'spring' as const, stiffness: 300, damping: 15 };
    return { duration: 0.4, ease: 'easeOut' };
  })();

  // ── Ring animation ───────────────────────────────────────────
  const ringAnimate = (() => {
    if (s === 'thinking')
      return {
        borderColor: RING_COLORS.thinking,
        borderWidth: ['2px', '3px', '2px'],
        boxShadow: [
          `0 0 8px rgba(255,255,255,0.25)`,
          `0 0 14px rgba(255,255,255,0.45)`,
          `0 0 8px rgba(255,255,255,0.25)`,
        ],
      };
    if (s === 'speaking')
      return {
        borderColor: RING_COLORS.speaking,
        boxShadow: [
          `0 0 8px rgba(255,255,255,0.35)`,
          `0 0 18px rgba(255,255,255,0.55)`,
          `0 0 8px rgba(255,255,255,0.35)`,
        ],
      };
    if (s === 'listening')
      return {
        borderColor: RING_COLORS.listening,
        boxShadow: `0 0 8px rgba(255,255,255,0.3)`,
      };
    if (s === 'sleeping')
      return {
        borderColor: RING_COLORS.sleeping,
        boxShadow: `0 0 4px rgba(255,255,255,0.12)`,
        opacity: 0.5,
      };
    if (s === 'success')
      return {
        borderColor: [RING_COLORS.success, RING_COLORS.idle],
        boxShadow: [
          `0 0 20px rgba(255,255,255,0.5)`,
          `0 0 8px rgba(255,255,255,0.2)`,
        ],
      };
    return {
      borderColor: RING_COLORS.idle,
      boxShadow: `0 0 8px rgba(255,255,255,0.2)`,
    };
  })();

  const ringTransition = (() => {
    if (s === 'thinking')
      return { duration: 1.5, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'speaking')
      return { duration: 0.5, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'success') return { duration: 0.3 };
    return { duration: 0.4, ease: 'easeOut' };
  })();

  // ── Glow animation ───────────────────────────────────────────
  const glowAnimate = (() => {
    if (s === 'idle') return { opacity: 0.2 };
    if (s === 'thinking') return { opacity: [0.4, 0.7, 0.4] };
    if (s === 'speaking') return { opacity: [0.6, 0.9, 0.6] };
    if (s === 'listening') return { opacity: 0.5 };
    if (s === 'sleeping') return { opacity: 0.05 };
    if (s === 'success') return { opacity: [0, 1, 0.2] };
    return { opacity: 0.2 };
  })();

  const glowTransition = (() => {
    if (s === 'thinking')
      return { duration: 1.5, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'speaking')
      return { duration: 0.5, repeat: Infinity, ease: 'easeInOut' };
    if (s === 'success') return { duration: 0.6, ease: 'easeOut' };
    return { duration: 0.5, ease: 'easeOut' };
  })();

  return (
    <div
      className={`amin-avatar-root${className ? ` ${className}` : ''}`}
      style={{ width: size, height: size, position: 'relative' }}
    >
      {/* Outer glow */}
      <motion.div
        className="amin-avatar-glow"
        animate={glowAnimate}
        transition={glowTransition}
        style={{
          background: `radial-gradient(circle, ${GLOW_COLORS[s]}, transparent 70%)`,
        }}
      />

      {/* Ring + Image */}
      <motion.div
        className="amin-avatar-ring"
        animate={ringAnimate}
        transition={ringTransition}
        style={{ borderColor: RING_COLORS[s] }}
      >
        {size >= 44 ? (
          <AminAnimatedAvatar size={size} state={s} />
        ) : (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/amin-avatar.png"
              className="amin-avatar-img"
              alt="Amin"
              draggable={false}
            />
            <AminEyes state={s} size={size} />
          </>
        )}
      </motion.div>

      {/* Sleep ZZZ indicator */}
      <AnimatePresence mode="wait">
        {s === 'sleeping' && <AminSleepIndicator key="sleep" />}
      </AnimatePresence>

      {/* Waveform (speaking only) */}
      <AnimatePresence mode="wait">
        {s === 'speaking' && showWaveform && (
          <AminWaveform key="waveform" size={size} />
        )}
      </AnimatePresence>

      {/* Thinking dots */}
      <AnimatePresence mode="wait">
        {s === 'thinking' && <AminThinkingDots key="dots" />}
      </AnimatePresence>
    </div>
  );
}
