'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { apiClient, type SoulDetail } from '@/lib/apiClient';
import { Sidebar } from '@/components/Sidebar';
import { TopBar } from '@/components/TopBar';
import { DevModeBanner } from '@/components/DevModeBanner';
import { StubProviderBanner } from '@/components/StubProviderBanner';
import { AminPanel } from '@/components/amin/AminPanel';
import { AminMinimized } from '@/components/amin/AminMinimized';
import { AminProvider, useAminContext } from '@/components/amin/AminProvider';
import EntrySequence from '@/components/shell/EntrySequence';
import { AnimatePresence } from 'framer-motion';

function AppShellInner() {
  const { aminOpen } = useAminContext();

  return (
    <>
      {/* Left-side panel (always in DOM, visibility controlled by aminOpen) */}
      <AnimatePresence>{aminOpen && <AminPanel />}</AnimatePresence>

      {/* FAB always visible bottom-right */}
      <AminMinimized />
    </>
  );
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [soul, setSoul] = useState<SoulDetail | null>(null);
  const [showEntry, setShowEntry] = useState(() => {
    if (typeof window === 'undefined') return false;
    return !sessionStorage.getItem('amin-entry-seen');
  });

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  // Fetch soul/twin data for sidebar personalization (non-blocking)
  useEffect(() => {
    if (!isAuthenticated) return;
    apiClient
      .getMySoul()
      .then(setSoul)
      .catch(() => {
        // Soul not available yet — sidebar works without it
      });
  }, [isAuthenticated]);

  const handleEntryComplete = () => {
    sessionStorage.setItem('amin-entry-seen', '1');
    setShowEntry(false);
  };

  const handleCollapsedChange = useCallback((collapsed: boolean) => {
    setSidebarCollapsed(collapsed);
  }, []);

  const handleToggleSidebar = useCallback(() => {
    if (window.innerWidth <= 1024) {
      setMobileOpen(prev => !prev);
    } else {
      setSidebarCollapsed(prev => {
        const next = !prev;
        localStorage.setItem('heyamin-sidebar-collapsed', String(next));
        return next;
      });
    }
  }, []);

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="app-loading-content">
          <span className="spinner spinner-lg" />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <>
      <EntrySequence visible={showEntry} onComplete={handleEntryComplete} />
      <AminProvider>
        <div
          className={`app-shell ${sidebarCollapsed ? 'app-shell-collapsed' : ''}`}
          style={showEntry ? { opacity: 0, pointerEvents: 'none' } : undefined}
        >
          <DevModeBanner />
          <StubProviderBanner />
          <Sidebar
            collapsed={sidebarCollapsed}
            onCollapsedChange={handleCollapsedChange}
            mobileOpen={mobileOpen}
            onMobileClose={() => setMobileOpen(false)}
            soul={soul}
          />
          <main className="app-main">
            <TopBar
              onToggleSidebar={handleToggleSidebar}
              sidebarCollapsed={sidebarCollapsed}
            />
            <div className="app-content">{children}</div>
          </main>
          <AppShellInner />
        </div>
      </AminProvider>
    </>
  );
}
