'use client';

import { motion } from 'framer-motion';

const ZS = [
  { size: 10, delay: 0, yEnd: -20 },
  { size: 13, delay: 0.7, yEnd: -24 },
  { size: 10, delay: 1.4, yEnd: -20 },
];

export function AminSleepIndicator() {
  return (
    <motion.div
      className="amin-sleep-indicator"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      style={{
        position: 'absolute',
        top: '-28px',
        right: '-4px',
        display: 'flex',
        alignItems: 'flex-end',
        gap: '2px',
        pointerEvents: 'none',
      }}
    >
      {ZS.map(({ size, delay, yEnd }, i) => (
        <motion.span
          key={i}
          style={{
            fontSize: size,
            fontFamily: 'monospace',
            color: '#94a3b8',
            display: 'block',
            lineHeight: 1,
          }}
          animate={{
            y: [0, yEnd],
            opacity: [0, 1, 0],
          }}
          transition={{
            duration: 2,
            delay,
            repeat: Infinity,
            ease: 'easeOut',
          }}
        >
          z
        </motion.span>
      ))}
    </motion.div>
  );
}
