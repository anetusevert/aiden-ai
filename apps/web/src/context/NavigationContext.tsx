'use client';

import {
  createContext,
  useCallback,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from 'react';
import { usePathname } from 'next/navigation';

export type NavSection =
  | 'home'
  | 'clients'
  | 'cases'
  | 'workflows'
  | 'documents'
  | 'intelligence'
  | 'admin';

interface NavContextValue {
  activeSection: NavSection | null;
  panelOpen: boolean;
  collapsePanel: () => void;
  togglePanel: () => void;
}

const ROUTE_SECTION_MAP: Array<{ prefix: string; section: NavSection }> = [
  { prefix: '/dashboard', section: 'home' },
  { prefix: '/home', section: 'home' },
  { prefix: '/clients', section: 'clients' },
  { prefix: '/cases', section: 'cases' },
  { prefix: '/workflows', section: 'workflows' },
  { prefix: '/documents', section: 'documents' },
  { prefix: '/news', section: 'intelligence' },
  { prefix: '/wiki', section: 'intelligence' },
  { prefix: '/research', section: 'intelligence' },
  { prefix: '/global-legal', section: 'intelligence' },
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
  collapsePanel: () => {},
  togglePanel: () => {},
});

export function useNav() {
  return useContext(NavigationCtx);
}

export function NavigationProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [activeSection, setActiveSection] = useState<NavSection | null>(
    () => sectionFromPath(pathname) ?? 'home'
  );
  const [panelOpen, setPanelOpen] = useState(() => {
    const initial = sectionFromPath(pathname) ?? 'home';
    return initial !== 'home';
  });

  useEffect(() => {
    const detected = sectionFromPath(pathname);
    if (detected && detected !== activeSection) {
      setActiveSection(detected);
      setPanelOpen(detected !== 'home');
    }
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const collapsePanel = useCallback(() => setPanelOpen(false), []);
  const togglePanel = useCallback(() => setPanelOpen(prev => !prev), []);

  return (
    <NavigationCtx.Provider
      value={{ activeSection, panelOpen, collapsePanel, togglePanel }}
    >
      {children}
    </NavigationCtx.Provider>
  );
}
