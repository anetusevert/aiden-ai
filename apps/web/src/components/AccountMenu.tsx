'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/AuthContext';
import { clearSession } from '@/lib/apiClient';
import { useNavigation } from '@/components/NavigationLoader';
import { UserAvatar } from './UserAvatar';
import {
  DropdownMenu,
  DropdownItem,
  DropdownDivider,
  DropdownSection,
} from './ui/DropdownMenu';

function getRoleBadgeClass(role: string) {
  switch (role) {
    case 'ADMIN':
      return 'account-menu-role account-menu-role-admin';
    case 'EDITOR':
      return 'account-menu-role account-menu-role-editor';
    default:
      return 'account-menu-role account-menu-role-viewer';
  }
}

export function AccountMenu() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const pathname = usePathname();
  const tNav = useTranslations('nav');
  const tCommon = useTranslations('common');
  const { user, logout } = useAuth();
  const { navigateTo } = useNavigation();

  if (!user) return null;

  const handleLogout = async () => {
    setOpen(false);
    await logout();
    router.push('/');
  };

  const handleSwitchWorkspace = () => {
    setOpen(false);
    clearSession();
    router.push('/login');
  };

  const navigate = (href: string) => {
    setOpen(false);
    navigateTo(href);
  };

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  return (
    <DropdownMenu
      open={open}
      onClose={() => setOpen(false)}
      align="right"
      trigger={
        <UserAvatar
          user={user}
          size="md"
          showRing={open}
          onClick={() => setOpen(!open)}
        />
      }
    >
      {/* User identity header */}
      <div className="account-menu-header">
        <UserAvatar user={user} size="lg" />
        <div className="account-menu-identity">
          <div className="account-menu-name">
            {user.full_name || tCommon('user')}
          </div>
          <div className="account-menu-email">{user.email}</div>
          <span className={getRoleBadgeClass(user.role)}>
            {user.role === 'ADMIN'
              ? tCommon('admin')
              : user.role === 'EDITOR'
                ? tCommon('editor')
                : user.role === 'VIEWER'
                  ? tCommon('viewer')
                  : user.role}
          </span>
        </div>
      </div>

      <DropdownDivider />

      <DropdownSection>
        <DropdownItem
          icon={<AccountIcon />}
          label={tNav('myAccount')}
          onClick={() => navigate('/account')}
          active={
            isActive('/account') &&
            !pathname.startsWith('/account/twin') &&
            !pathname.startsWith('/account/amin')
          }
        />
        <DropdownItem
          icon={<AminSettingsIcon />}
          label={tNav('myAmin')}
          onClick={() => navigate('/account/amin')}
          active={isActive('/account/amin')}
        />
      </DropdownSection>

      <DropdownDivider />

      <DropdownSection>
        <DropdownItem
          icon={<SwitchIcon />}
          label={tNav('switchWorkspace')}
          onClick={handleSwitchWorkspace}
        />
        <DropdownItem
          icon={<LogoutIcon />}
          label={tNav('signOut')}
          onClick={handleLogout}
          danger
        />
      </DropdownSection>
    </DropdownMenu>
  );
}

function AccountIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function AminSettingsIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <line x1="4" y1="6" x2="20" y2="6" />
      <circle cx="9" cy="6" r="2" fill="currentColor" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <circle cx="15" cy="12" r="2" fill="currentColor" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="11" cy="18" r="2" fill="currentColor" />
    </svg>
  );
}

function SwitchIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <polyline points="16,3 21,3 21,8" />
      <line x1="4" y1="20" x2="21" y2="3" />
      <polyline points="21,16 21,21 16,21" />
      <line x1="15" y1="15" x2="21" y2="21" />
      <line x1="4" y1="4" x2="9" y2="9" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16,17 21,12 16,7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
