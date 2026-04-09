'use client';

import type { ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { workflowStepAdvance, workflowStepExit } from '@/lib/motion';

export function StepWorkspace({
  stepKey,
  successFlash = false,
  children,
}: {
  stepKey: string | number;
  successFlash?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      className="workflow-step-workspace"
      data-success-flash={successFlash ? 'true' : 'false'}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={stepKey}
          className="workflow-step-workspace-inner"
          initial={workflowStepAdvance.initial}
          animate={workflowStepAdvance.animate}
          exit={workflowStepExit.exit}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
