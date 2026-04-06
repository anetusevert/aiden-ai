'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { apiClient, type SoulDetail } from '@/lib/apiClient';
import { Rail1 } from '@/components/nav/Rail1';
import { Rail2Panel } from '@/components/nav/Rail2Panel';
import { TopBar } from '@/components/TopBar';
import { DevModeBanner } from '@/components/DevModeBanner';
import { StubProviderBanner } from '@/components/StubProviderBanner';
import { AminInfoPanel } from '@/components/amin/AminInfoPanel';
import { AminMinimized } from '@/components/amin/AminMinimized';
import { AminFloatingMessage } from '@/components/amin/AminFloatingMessage';
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
import { setActiveCaseContext } from '@/lib/screenContext';

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

    const navHandler = (event: Event) => {
      const customEvent = event as CustomEvent<{ path?: string }>;
      const path = customEvent.detail?.path;
      if (path) navigateTo(path);
    };

    window.addEventListener('document_created', handler as EventListener);
    window.addEventListener('amin-navigate', navHandler as EventListener);
    return () => {
      window.removeEventListener('document_created', handler as EventListener);
      window.removeEventListener('amin-navigate', navHandler as EventListener);
    };
  }, [navigateTo]);

  return (
    <>
      <AnimatePresence>{aminOpen && <AminInfoPanel />}</AnimatePresence>
      <AminFloatingMessage />
      <AminMinimized />
    </>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [showEntry, setShowEntry] = useState(false);
  const [soul, setSoul] = useState<SoulDetail | null>(null);

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
    apiClient
      .getMySoul()
      .then(s => setSoul(s))
      .catch(() => {});
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetch('/api/v1/cases/active', { credentials: 'include' })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        if (data)
          setActiveCaseContext({
            case_id: data.case_id,
            case_title: data.case_title,
            client_name: data.client_name,
            practice_area: data.practice_area,
          });
        else setActiveCaseContext(null);
      })
      .catch(() => setActiveCaseContext(null));
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
                <Rail2Panel soul={soul} />
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
