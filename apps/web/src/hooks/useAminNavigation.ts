'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAminContext } from '@/components/amin/AminProvider';

export function useAminNavigation() {
  const router = useRouter();
  const { injectMessage } = useAminContext();

  useEffect(() => {
    const handleAminNavigation = (event: Event) => {
      const customEvent = event as CustomEvent<{
        path?: string;
        message?: string;
      }>;
      const path = customEvent.detail?.path;
      const message = customEvent.detail?.message?.trim();

      if (!path) return;

      if (message) {
        injectMessage('assistant', message);
      }

      window.setTimeout(() => router.push(path), 400);
    };

    window.addEventListener(
      'amin:navigate',
      handleAminNavigation as EventListener
    );

    return () =>
      window.removeEventListener(
        'amin:navigate',
        handleAminNavigation as EventListener
      );
  }, [injectMessage, router]);
}
