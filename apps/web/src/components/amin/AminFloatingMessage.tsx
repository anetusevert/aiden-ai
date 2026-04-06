'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAminContext } from './AminProvider';

export function AminFloatingMessage() {
  const { floatingMessage, dismissFloatingMessage, aminOpen } =
    useAminContext();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (floatingMessage && !aminOpen) {
      setVisible(true);
      const timer = setTimeout(() => {
        setVisible(false);
        dismissFloatingMessage();
      }, 10000);
      return () => clearTimeout(timer);
    } else {
      setVisible(false);
    }
  }, [floatingMessage, aminOpen, dismissFloatingMessage]);

  return (
    <AnimatePresence>
      {visible && floatingMessage && (
        <motion.div
          className="amin-floating-msg"
          initial={{ opacity: 0, y: 20, scale: 0.92 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          onClick={() => {
            setVisible(false);
            dismissFloatingMessage();
          }}
        >
          <div className="amin-floating-msg-content">{floatingMessage}</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
