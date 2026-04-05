'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { marketingPageTransition } from '@/lib/motion';

interface MarketingPageTransitionProps {
  pathname: string;
  children: React.ReactNode;
}

export default function MarketingPageTransition({
  pathname,
  children,
}: MarketingPageTransitionProps) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pathname}
        {...marketingPageTransition.enter}
        exit={marketingPageTransition.exit}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
