'use client';

import { motion } from 'framer-motion';

export function AminThinkingDots() {
  return (
    <motion.div
      className="amin-thinking-dots"
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 4 }}
      transition={{ duration: 0.25 }}
    >
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          style={{
            width: 5,
            height: 5,
            borderRadius: '50%',
            backgroundColor: '#6366f1',
          }}
          animate={{ scale: [0.5, 1, 0.5] }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
            ease: 'easeInOut',
          }}
        />
      ))}
    </motion.div>
  );
}
