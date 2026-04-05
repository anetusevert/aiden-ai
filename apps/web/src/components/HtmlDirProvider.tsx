'use client';

import { useEffect } from 'react';
import { useAuth } from '@/lib/AuthContext';

const RTL_LOCALES = new Set(['ar', 'ur']);

export function HtmlDirProvider() {
  const { appLanguage } = useAuth();

  useEffect(() => {
    const isRtl = RTL_LOCALES.has(appLanguage);
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
    document.documentElement.lang = appLanguage || 'en';
  }, [appLanguage]);

  return null;
}
