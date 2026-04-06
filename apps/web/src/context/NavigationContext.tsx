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
  | 'workflows'
  | 'documents'
  | 'intelligence'
  | 'wiki'
  | 'knowledge'
  | 'admin';

interface NavContextValue {
  activeSection: NavSection | null;
  panelOpen: boolean;
  collapsePanel: () => void;
}

const ROUTE_SECTION_MAP: Array<{ prefix: string; section: NavSection }> = [
  { prefix: '/home', section: 'home' },
  { prefix: '/workflows', section: 'workflows' },
  { prefix: '/documents', section: 'documents' },
  { prefix: '/news', section: 'intelligence' },
  { prefix: '/global-legal', section: 'intelligence' },
  { prefix: '/wiki', section: 'wiki' },
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
  collapsePanel: () => {},
});

export function useNav() {
  return useContext(NavigationCtx);
}

export function NavigationProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [activeSection, setActiveSection] = useState<NavSection | null>(
    () => sectionFromPath(pathname) ?? 'home'
  );
  const [panelOpen, setPanelOpen] = useState(true);

  useEffect(() => {
    const detected = sectionFromPath(pathname);
    if (detected && detected !== activeSection) {
      setActiveSection(detected);
    }
  }, [pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const collapsePanel = useCallback(() => setPanelOpen(false), []);

  return (
    <NavigationCtx.Provider value={{ activeSection, panelOpen, collapsePanel }}>
      {children}
    </NavigationCtx.Provider>
  );
}
