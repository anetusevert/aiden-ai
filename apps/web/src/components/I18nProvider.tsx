'use client';

import { NextIntlClientProvider } from 'next-intl';
import { useAuth } from '@/lib/AuthContext';
import { getMessages } from '@/lib/i18nMessages';

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const { appLanguage } = useAuth();
  const messages = getMessages(appLanguage);
  return (
    <NextIntlClientProvider locale={appLanguage} messages={messages}>
      {children}
    </NextIntlClientProvider>
  );
}
