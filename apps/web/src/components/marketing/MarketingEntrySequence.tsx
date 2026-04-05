'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  motionTokens,
  goldLineExpand,
  marketingEntryExit,
} from '@/lib/motion';
import { AminAvatar, type AminAvatarState } from '@/components/amin/AminAvatar';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';

interface MarketingEntrySequenceProps {
  visible: boolean;
  onComplete: () => void;
}

export default function MarketingEntrySequence({
  visible,
  onComplete,
}: MarketingEntrySequenceProps) {
  const [phase, setPhase] = useState(0);
  const [avatarState, setAvatarState] = useState<AminAvatarState>('idle');
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  useEffect(() => {
    if (!visible) {
      setPhase(0);
      setAvatarState('idle');
      return;
    }

    const timers = [
      setTimeout(() => setAvatarState('idle'), 400),
      setTimeout(() => setPhase(1), 1200),
      setTimeout(() => setAvatarState('speaking'), 1600),
      setTimeout(() => setAvatarState('idle'), 2200),
      setTimeout(() => setPhase(2), 2500),
      setTimeout(() => setPhase(3), 3800),
      setTimeout(() => onCompleteRef.current(), 4500),
    ];
    return () => timers.forEach(clearTimeout);
  }, [visible]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div className="mkt-entry" exit={marketingEntryExit}>
          <div className="mkt-entry-content">
            {/* Phase 0: Avatar materializes from void */}
            <AnimatePresence mode="wait">
              {phase < 2 && (
                <motion.div
                  key="phase-avatar-brand"
                  className="mkt-entry-phase"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{
                    opacity: 0,
                    scale: 1.06,
                    transition: { duration: 0.4, ease: motionTokens.ease },
                  }}
                >
                  {/* Gold bloom behind avatar */}
                  <motion.div
                    className="mkt-entry-bloom"
                    initial={{ opacity: 0, scale: 0.4 }}
                    animate={{
                      opacity: [0, 0.5, 0.3],
                      scale: [0.4, 1.6, 1.8],
                    }}
                    transition={{ duration: 1.4, ease: 'easeOut', delay: 0.2 }}
                  />

                  {/* Avatar */}
                  <motion.div
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{
                      duration: 0.9,
                      ease: [0.22, 1, 0.36, 1],
                      delay: 0.15,
                    }}
                  >
                    <AminAvatar size={96} state={avatarState} showWaveform={false} />
                  </motion.div>

                  {/* Phase 1: Logo + gold line */}
                  <AnimatePresence>
                    {phase >= 1 && (
                      <motion.div
                        key="wordmark-group"
                        className="mkt-entry-wordmark-group"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, transition: { duration: 0.2 } }}
                      >
                        <motion.div
                          initial={{ opacity: 0, scale: 0.85 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ duration: 0.6, ease: motionTokens.ease }}
                        >
                          <HeyAminLogo variant="full" size={200} />
                        </motion.div>

                        <motion.div
                          className="mkt-entry-gold-line"
                          {...goldLineExpand}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Phase 2: Tagline */}
            <AnimatePresence mode="wait">
              {phase === 2 && (
                <motion.div
                  key="phase-tagline"
                  className="mkt-entry-phase"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{
                    opacity: 0,
                    y: -20,
                    transition: { duration: 0.35 },
                  }}
                >
                  <motion.div
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{
                      duration: 0.6,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                  >
                    <AminAvatar size={56} state="idle" showWaveform={false} />
                  </motion.div>

                  <motion.h1
                    className="mkt-entry-tagline"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.6,
                      ease: motionTokens.ease,
                      delay: 0.15,
                    }}
                  >
                    Legal intelligence,{' '}
                    <span className="ha-accent">elevated.</span>
                  </motion.h1>

                  <motion.div
                    className="mkt-entry-gold-line"
                    {...goldLineExpand}
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Phase 3: Final "Enter" moment */}
            <AnimatePresence>
              {phase === 3 && (
                <motion.div
                  key="phase-enter"
                  className="mkt-entry-phase"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{
                    opacity: 0,
                    scale: 1.08,
                    transition: { duration: 0.4 },
                  }}
                  transition={{
                    duration: 0.5,
                    ease: [0.22, 1, 0.36, 1],
                  }}
                >
                  <motion.p
                    className="mkt-entry-welcome"
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 0.7, y: 0 }}
                    transition={{ delay: 0.1, duration: 0.4 }}
                  >
                    Welcome
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
