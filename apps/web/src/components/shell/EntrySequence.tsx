'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cinematicSweepIn, motionTokens } from '@/lib/motion';
import { AminAvatar, type AminAvatarState } from '@/components/amin/AminAvatar';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';

interface EntrySequenceProps {
  visible: boolean;
  onComplete: () => void;
}

const capabilities = [
  {
    icon: 'M9.663 17h4.674M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
    label: 'Your legal intelligence',
  },
  {
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
    label: 'Document analysis',
  },
  {
    icon: 'M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z',
    label: 'Voice-ready',
  },
];

export default function EntrySequence({
  visible,
  onComplete,
}: EntrySequenceProps) {
  const [phase, setPhase] = useState(0);
  const [avatarState, setAvatarState] = useState<AminAvatarState>('idle');
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!visible) {
      setPhase(0);
      return;
    }

    const timers = [
      setTimeout(() => setPhase(1), 1000),
      setTimeout(() => setAvatarState('speaking'), 1500),
      setTimeout(() => setAvatarState('idle'), 3000),
      setTimeout(() => setPhase(2), 2200),
      setTimeout(() => setPhase(3), 3200),
      setTimeout(() => onCompleteRef.current(), 4200),
    ];
    return () => timers.forEach(clearTimeout);
  }, [visible]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="entry-sequence"
          exit={{
            opacity: 0,
            scale: 1.04,
            transition: { duration: 0.5, ease: motionTokens.ease },
          }}
        >
          <div className="entry-sequence-content">
            {/* Phase 0: Logo mark + wordmark reveal */}
            <AnimatePresence>
              {phase === 0 && (
                <motion.div
                  className="entry-phase"
                  key="phase-logo"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{
                    opacity: 0,
                    scale: 1.05,
                    transition: { duration: 0.35 },
                  }}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                  }}
                >
                  <motion.div
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{
                      duration: 0.8,
                      ease: [0.0, 0.0, 0.2, 1],
                    }}
                    style={{ marginBottom: 24 }}
                  >
                    <HeyAminLogo variant="full" size={180} />
                  </motion.div>

                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.6,
                      delay: 0.8,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  >
                    <AminAvatar
                      size={120}
                      state={avatarState}
                      showWaveform={false}
                    />
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Phase 1: Capabilities sweep */}
            <AnimatePresence>
              {phase === 2 && (
                <motion.div
                  key="phase-caps"
                  className="entry-capabilities"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{
                    opacity: 0,
                    y: -20,
                    transition: { duration: 0.3 },
                  }}
                >
                  {capabilities.map((cap, i) => (
                    <motion.div
                      key={cap.label}
                      className="entry-capability"
                      variants={cinematicSweepIn}
                      custom={i}
                      initial="hidden"
                      animate="visible"
                    >
                      <svg
                        width="20"
                        height="20"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d={cap.icon} />
                      </svg>
                      <span>{cap.label}</span>
                    </motion.div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Phase 3: Avatar materialization */}
            <AnimatePresence>
              {phase === 3 && (
                <motion.div
                  key="phase-avatar"
                  initial={{ opacity: 0, scale: 0.6 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{
                    opacity: 0,
                    scale: 1.1,
                    transition: { duration: 0.4 },
                  }}
                  transition={{
                    duration: 0.6,
                    ease: [0.22, 1, 0.36, 1],
                  }}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 16,
                  }}
                >
                  <AminAvatar
                    size={120}
                    state={avatarState}
                    showWaveform={false}
                  />
                  <motion.p
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3, duration: 0.4 }}
                    style={{
                      color: 'var(--text-secondary, #9a9ba2)',
                      fontSize: '0.875rem',
                    }}
                  >
                    Ready to assist
                  </motion.p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
