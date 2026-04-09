'use client';

import type { ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { usePathname } from 'next/navigation';
import { workflowPageEnter, workflowPageExit } from '@/lib/motion';

function getWorkflowProgress(pathname: string): number {
  const cleanPath = pathname.split('?')[0];
  const segments = cleanPath.split('/').filter(Boolean);

  if (segments.length <= 1) return 0;
  if (segments.length === 2) return 25;
  if (segments.length === 3) return 60;
  return 100;
}

export default function WorkflowsLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? '/workflows';
  const progress = getWorkflowProgress(pathname);

  return (
    <section className="workflow-route-shell">
      <div className="workflow-route-progress">
        <motion.div
          layoutId="workflow-progress"
          className="workflow-route-progress-bar"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.28, ease: 'easeOut' }}
        />
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={pathname}
          className="workflow-route-page"
          initial={workflowPageEnter.initial}
          animate={workflowPageEnter.animate}
          exit={workflowPageExit.exit}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}
