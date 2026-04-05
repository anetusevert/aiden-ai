'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { reportScreenContext, useCurrentScreenContext } from '@/lib/screenContext';

export function useScreenContext() {
  const pathname = usePathname();
  const current = useCurrentScreenContext();

  useEffect(() => {
    const handle = window.setTimeout(() => {
      reportScreenContext({
        route: pathname || '/',
        page_title: document.title || 'Workspace',
        document: current.document,
        ui_state: current.ui_state ?? {},
      });
    }, 300);

    return () => window.clearTimeout(handle);
  }, [pathname, current.document, current.ui_state]);
}
