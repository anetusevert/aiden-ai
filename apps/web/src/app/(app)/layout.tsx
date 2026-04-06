'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { apiClient } from '@/lib/apiClient';
import { Rail1 } from '@/components/nav/Rail1';
import { TopBar } from '@/components/TopBar';
import { DevModeBanner } from '@/components/DevModeBanner';
import { StubProviderBanner } from '@/components/StubProviderBanner';
import { AminInfoPanel } from '@/components/amin/AminInfoPanel';
import { AminMinimized } from '@/components/amin/AminMinimized';
import { AminProvider, useAminContext } from '@/components/amin/AminProvider';
import EntrySequence from '@/components/shell/EntrySequence';
import {
  NavigationLoaderProvider,
  useNavigation,
} from '@/components/NavigationLoader';
import { NavigationProvider } from '@/context/NavigationContext';
import { AnimatePresence } from 'framer-motion';
import { I18nProvider } from '@/components/I18nProvider';
import { useScreenContext } from '@/hooks/useScreenContext';
import { useTranslations } from 'next-intl';

function AppShellLoading() {
  const t = useTranslations('common');
  return (
    <div className="app-loading">
      <div className="app-loading-content">
        <span className="spinner spinner-lg" />
        <p>{t('loading')}</p>
      </div>
    </div>
  );
}

function AppShellInner() {
  const { aminOpen } = useAminContext();
  const { navigateTo } = useNavigation();
  useScreenContext();

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<{ docId?: string }>;
      const docId = customEvent.detail?.docId;
      if (docId) {
        navigateTo(`/documents/${docId}`);
      }
    };

    window.addEventListener('document_created', handler as EventListener);
    return () =>
      window.removeEventListener('document_created', handler as EventListener);
  }, [navigateTo]);

  return (
    <>
      <AnimatePresence>{aminOpen && <AminInfoPanel />}</AnimatePresence>
      <AminMinimized />
    </>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [showEntry, setShowEntry] = useState(false);

  useEffect(() => {
    if (!sessionStorage.getItem('amin-entry-seen')) {
      setShowEntry(true);
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    apiClient.getMySoul().catch(() => {});
  }, [isAuthenticated]);

  const handleEntryComplete = useCallback(() => {
    sessionStorage.setItem('amin-entry-seen', '1');
    setShowEntry(false);
  }, []);

  if (isLoading) {
    return (
      <I18nProvider>
        <AppShellLoading />
      </I18nProvider>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <EntrySequence visible={showEntry} onComplete={handleEntryComplete} />
      <I18nProvider>
        <NavigationLoaderProvider>
          <NavigationProvider>
            <AminProvider>
              <div
                className="ha-shell app-shell"
                style={
                  showEntry ? { opacity: 0, pointerEvents: 'none' } : undefined
                }
              >
                <DevModeBanner />
                <StubProviderBanner />
                <Rail1 />
                <main className="ha-main">
                  <TopBar />
                  <div className="app-content">{children}</div>
                </main>
                <AppShellInner />
              </div>
            </AminProvider>
          </NavigationProvider>
        </NavigationLoaderProvider>
      </I18nProvider>
    </>
  );
}
