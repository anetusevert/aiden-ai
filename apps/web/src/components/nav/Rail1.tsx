'use client';

import { useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';
import { useNav, type NavSection } from '@/context/NavigationContext';
import { UserAvatar } from '@/components/UserAvatar';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import { AminAvatar } from '@/components/amin/AminAvatar';
import { useAminAvatarState } from '@/hooks/useAminAvatarState';

interface NavIconDef {
  id: NavSection;
  label: string;
  icon: React.ReactNode;
  adminOnly?: boolean;
  directRoute?: string;
}

const NAV_ICONS: NavIconDef[] = [
  {
    id: 'home',
    label: 'Home',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9,22 9,12 15,12 15,22" />
      </svg>
    ),
  },
  {
    id: 'workflows',
    label: 'Workflows',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M7 3h8l4 4v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V6a3 3 0 0 1 3-3Z" />
        <path d="M15 3v5h5" />
        <path d="M9 13h6" />
        <path d="M9 17h6" />
      </svg>
    ),
  },
  {
    id: 'intelligence',
    label: 'Legal Intelligence',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M5 6.5A2.5 2.5 0 0 1 7.5 4H20v13.5A2.5 2.5 0 0 1 17.5 20H7a3 3 0 0 1-3-3V6.5Z" />
        <path d="M8 8h8" />
        <path d="M8 12h8" />
        <path d="M8 16h5" />
      </svg>
    ),
  },
  {
    id: 'knowledge',
    label: 'Knowledge Base',
    adminOnly: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4.03 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
      </svg>
    ),
  },
  {
    id: 'admin',
    label: 'Admin',
    adminOnly: true,
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    ),
  },
];

const SETTINGS_ICON: NavIconDef = {
  id: 'home' as NavSection,
  label: 'My Amin',
  directRoute: '/account/amin',
  icon: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <line x1="4" y1="6" x2="20" y2="6" />
      <circle cx="9" cy="6" r="2" fill="currentColor" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <circle cx="15" cy="12" r="2" fill="currentColor" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="11" cy="18" r="2" fill="currentColor" />
    </svg>
  ),
};

export function Rail1() {
  const pathname = usePathname();
  const { user } = useAuth();
  const { navigateTo } = useNavigation();
  const { activeSection, panelOpen, selectSection } = useNav();

  const aminAvatarState = useAminAvatarState();
  const isAdmin = user?.role === 'ADMIN';

  const handleIconClick = useCallback(
    (def: NavIconDef) => {
      if (def.directRoute) {
        navigateTo(def.directRoute);
        return;
      }
      if (def.id === 'home' && activeSection === 'home' && panelOpen) {
        navigateTo('/home');
        return;
      }
      selectSection(def.id);
    },
    [activeSection, panelOpen, selectSection, navigateTo]
  );

  const isIconActive = (id: NavSection) => {
    if (panelOpen && activeSection === id) return true;
    if (!panelOpen) {
      const sectionRoutes: Record<NavSection, string[]> = {
        home: ['/home'],
        workflows: ['/workflows'],
        documents: ['/documents'],
        intelligence: ['/news', '/global-legal'],
        knowledge: ['/operator/knowledge-base'],
        admin: ['/operator', '/members', '/audit'],
      };
      return sectionRoutes[id]?.some(
        r => pathname === r || pathname.startsWith(r + '/')
      );
    }
    return false;
  };

  return (
    <div className="rail1">
      {/* Logo */}
      <div className="rail1-top">
        <motion.button
          className="rail1-logo-heyamin"
          onClick={() => navigateTo('/home')}
          type="button"
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.95 }}
        >
          <HeyAminLogo variant="mark" size={32} />
        </motion.button>
        <div className="rail1-logo-divider" />
      </div>

      {/* Main nav icons */}
      <nav className="rail1-nav">
        {NAV_ICONS.filter(def => !def.adminOnly || isAdmin).map(def => (
          <button
            key={def.id}
            className={`rail1-icon${isIconActive(def.id) ? ' rail1-icon-active' : ''}`}
            onClick={() => handleIconClick(def)}
            type="button"
          >
            {def.icon}
            <span className="rail1-tooltip">{def.label}</span>
          </button>
        ))}
      </nav>

      {/* Bottom pinned */}
      <div className="rail1-bottom">
        <button
          className="rail1-icon"
          onClick={() => handleIconClick(SETTINGS_ICON)}
          type="button"
        >
          {SETTINGS_ICON.icon}
          <span className="rail1-tooltip">{SETTINGS_ICON.label}</span>
        </button>

        <div style={{ padding: '4px 0' }}>
          <AminAvatar size={32} state={aminAvatarState} showWaveform={false} />
        </div>

        {user && (
          <Link
            href="/account"
            className="rail1-avatar"
            onClick={e => {
              e.preventDefault();
              navigateTo('/account');
            }}
          >
            <UserAvatar user={user} size="xs" />
            <span className="rail1-tooltip">Account</span>
          </Link>
        )}
      </div>
    </div>
  );
}
