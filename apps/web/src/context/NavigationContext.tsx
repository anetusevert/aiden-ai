'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from 'react';
import { usePathname } from 'next/navigation';

export type NavSection =
  | 'home'
  | 'workflows'
  | 'documents'
  | 'intelligence'
  | 'knowledge'
  | 'admin';

export type SidebarState = 'full' | 'compact' | 'immersive';

interface NavState {
  activeSection: NavSection | null;
  panelOpen: boolean;
  sidebarState: SidebarState;
}

interface NavContextValue extends NavState {
  selectSection: (section: NavSection) => void;
  collapsePanel: () => void;
  openPanel: () => void;
  setSidebarState: (state: SidebarState) => void;
}

const STORAGE_KEY = 'ha_nav_state';

function persistState(
  state: Pick<NavState, 'activeSection' | 'panelOpen' | 'sidebarState'>
) {
  try {
    if (state.sidebarState === 'immersive') return;
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        activeSection: state.activeSection,
        panelOpen: state.panelOpen,
        sidebarState: state.sidebarState,
      })
    );
  } catch {}
}

function loadPersistedState(): Partial<NavState> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

const ROUTE_SECTION_MAP: Array<{ prefix: string; section: NavSection }> = [
  { prefix: '/home', section: 'home' },
  { prefix: '/workflows', section: 'workflows' },
  { prefix: '/documents', section: 'documents' },
  { prefix: '/news', section: 'intelligence' },
  { prefix: '/global-legal', section: 'intelligence' },
  { prefix: '/operator/knowledge-base', section: 'knowledge' },
  { prefix: '/operator', section: 'admin' },
  { prefix: '/members', section: 'admin' },
  { prefix: '/audit', section: 'admin' },
];

function sectionFromPath(pathname: string): NavSection | null {
  for (const { prefix, section } of ROUTE_SECTION_MAP) {
    if (pathname === prefix || pathname.startsWith(prefix + '/')) {
      return section;
    }
  }
  return null;
}

const NavigationCtx = createContext<NavContextValue>({
  activeSection: 'home',
  panelOpen: true,
  sidebarState: 'full',
  selectSection: () => {},
  collapsePanel: () => {},
  openPanel: () => {},
  setSidebarState: () => {},
});

export function useNav() {
  return useContext(NavigationCtx);
}

export function NavigationProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  const [state, setState] = useState<NavState>(() => {
    const persisted =
      typeof window !== 'undefined' ? loadPersistedState() : null;
    const isCompact = typeof window !== 'undefined' && window.innerWidth < 1024;

    return {
      activeSection: persisted?.activeSection ?? 'home',
      panelOpen: isCompact ? false : (persisted?.panelOpen ?? true),
      sidebarState: isCompact ? 'compact' : (persisted?.sidebarState ?? 'full'),
    };
  });

  // Responsive: collapse on narrow viewports
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1023px)');
    const handler = (e: MediaQueryListEvent) => {
      if (e.matches) {
        setState(prev => {
          const next = {
            ...prev,
            panelOpen: false,
            sidebarState: 'compact' as const,
          };
          persistState(next);
          return next;
        });
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Sync active section with current route
  useEffect(() => {
    const detected = sectionFromPath(pathname);
    if (detected && detected !== state.activeSection) {
      setState(prev => ({ ...prev, activeSection: detected }));
    }
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectSection = useCallback((section: NavSection) => {
    setState(prev => {
      if (prev.activeSection === section && prev.panelOpen) {
        const next = {
          ...prev,
          panelOpen: false,
          sidebarState: 'compact' as const,
        };
        persistState(next);
        return next;
      }
      const next = {
        ...prev,
        activeSection: section,
        panelOpen: true,
        sidebarState: 'full' as const,
      };
      persistState(next);
      return next;
    });
  }, []);

  const collapsePanel = useCallback(() => {
    setState(prev => {
      const next = {
        ...prev,
        panelOpen: false,
        sidebarState: 'compact' as const,
      };
      persistState(next);
      return next;
    });
  }, []);

  const openPanel = useCallback(() => {
    setState(prev => {
      const next = { ...prev, panelOpen: true, sidebarState: 'full' as const };
      persistState(next);
      return next;
    });
  }, []);

  const setSidebarState = useCallback((s: SidebarState) => {
    setState(prev => {
      const panelOpen = s === 'full';
      const next = { ...prev, sidebarState: s, panelOpen };
      persistState(next);
      return next;
    });
  }, []);

  return (
    <NavigationCtx.Provider
      value={{
        ...state,
        selectSection,
        collapsePanel,
        openPanel,
        setSidebarState,
      }}
    >
      {children}
    </NavigationCtx.Provider>
  );
}
