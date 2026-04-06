'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';
import { reportScreenContext } from '@/lib/screenContext';
import { WikiPageList } from '@/components/wiki/WikiPageList';
import { WikiGraph } from '@/components/wiki/WikiGraph';

export default function WikiHomePage() {
  useEffect(() => {
    reportScreenContext({
      route: '/wiki',
      page_title: 'Knowledge Wiki',
      document: null,
      ui_state: {},
    });
  }, []);

  return (
    <motion.div className="wiki-home" {...fadeUp}>
      <WikiPageList />
      <WikiGraph />
    </motion.div>
  );
}
