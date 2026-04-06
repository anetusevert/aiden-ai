'use client';

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import type { AminAvatarState } from './AminAvatar';

interface AminEyesProps {
  state: AminAvatarState;
  size: number;
}

const BLINK_INTERVALS: Record<AminAvatarState, [number, number]> = {
  idle: [3000, 6000],
  thinking: [7000, 10000],
  speaking: [2000, 4000],
  listening: [4000, 7000],
  sleeping: [Infinity, Infinity],
  success: [1500, 3000],
};

const BLINK_DURATION = 0.12;

export function AminEyes({ state, size }: AminEyesProps) {
  const [isBlinking, setIsBlinking] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const permanentlyClosed = state === 'sleeping';

  useEffect(() => {
    if (permanentlyClosed) {
      setIsBlinking(false);
      return;
    }

    const [minMs, maxMs] = BLINK_INTERVALS[state] ?? [3000, 6000];
    if (!isFinite(minMs)) return;

    const scheduleBlink = () => {
      const delay = minMs + Math.random() * (maxMs - minMs);
      timerRef.current = setTimeout(() => {
        setIsBlinking(true);
        setTimeout(
          () => {
            setIsBlinking(false);
            scheduleBlink();
          },
          (BLINK_DURATION * 2 + 0.1) * 1000
        );
      }, delay);
    };

    scheduleBlink();
    return () => clearTimeout(timerRef.current);
  }, [state, permanentlyClosed]);

  // Eye area: top ~38–50% of avatar, left 18%–82%, height ~12%
  const eyeTop = size * 0.38;
  const eyeHeight = size * 0.13;
  const leftEyeX = size * 0.28;
  const rightEyeX = size * 0.62;
  const eyeWidth = size * 0.14;

  // For "thinking", shift eyes up slightly
  const yOffset = state === 'thinking' ? -size * 0.025 : 0;
  // For "listening", widen eyes slightly (narrower eyelid = more white showing)
  const eyelidScaleY = state === 'listening' ? 0.6 : 1;

  const eyesClosedOpacity = permanentlyClosed ? 1 : isBlinking ? 1 : 0;

  return (
    <motion.svg
      className="amin-avatar-eyes"
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
        zIndex: 2,
      }}
      animate={{ y: yOffset }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {/* Left eyelid */}
      <motion.ellipse
        cx={leftEyeX}
        cy={eyeTop + eyeHeight / 2}
        rx={eyeWidth / 2}
        ry={(eyeHeight / 2) * eyelidScaleY}
        fill="#c8956c"
        animate={{ opacity: eyesClosedOpacity }}
        transition={{ duration: BLINK_DURATION, ease: 'linear' }}
      />
      {/* Right eyelid */}
      <motion.ellipse
        cx={rightEyeX}
        cy={eyeTop + eyeHeight / 2}
        rx={eyeWidth / 2}
        ry={(eyeHeight / 2) * eyelidScaleY}
        fill="#c8956c"
        animate={{ opacity: eyesClosedOpacity }}
        transition={{ duration: BLINK_DURATION, ease: 'linear' }}
      />
    </motion.svg>
  );
}
