'use client';

import { type ReactNode } from 'react';

/**
 * Local shim for next-intl.
 * Returns the translation key as-is (dot-notation path).
 * Strips the namespace prefix for readability:
 *   "sidebar.dashboard" → "dashboard" → title-cased → "Dashboard"
 */
function humanize(key: string): string {
  const last = key.includes('.') ? key.split('.').pop()! : key;
  return last
    .replace(/([A-Z])/g, ' $1')
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .trim();
}

export function useTranslations(_namespace?: string) {
  return (key: string, _values?: Record<string, unknown>) => humanize(key);
}

export function NextIntlClientProvider({
  children,
}: {
  locale?: string;
  messages?: Record<string, unknown>;
  children: ReactNode;
}) {
  return <>{children}</>;
}

export default { useTranslations, NextIntlClientProvider };
