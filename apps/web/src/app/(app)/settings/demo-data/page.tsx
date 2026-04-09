'use client';

import { motion } from 'framer-motion';
import { DemoDataManager } from '@/components/admin/DemoDataManager';
import { fadeUp } from '@/lib/motion';

export default function DemoDataPage() {
  return (
    <motion.div
      className="settings-page"
      variants={fadeUp}
      initial="hidden"
      animate="visible"
    >
      <div className="settings-header">
        <h1 className="settings-title">Demo Data</h1>
        <p className="settings-subtitle">
          Manage the presentation dataset for this workspace from a single
          admin-only control surface.
        </p>
      </div>

      <DemoDataManager />
    </motion.div>
  );
}
