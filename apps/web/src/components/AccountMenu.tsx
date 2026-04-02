'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { clearSession } from '@/lib/apiClient';
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
  const { user, logout } = useAuth();

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
    router.push(href);
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
          <div className="account-menu-name">{user.full_name || 'User'}</div>
          <div className="account-menu-email">{user.email}</div>
          <span className={getRoleBadgeClass(user.role)}>{user.role}</span>
        </div>
      </div>

      <DropdownDivider />

      <DropdownSection>
        <DropdownItem
          icon={<AccountIcon />}
          label="My Account"
          onClick={() => navigate('/account')}
          active={isActive('/account') && !pathname.startsWith('/account/twin')}
        />
        <DropdownItem
          icon={<AIProfileIcon />}
          label="My AI Profile"
          onClick={() => navigate('/account/twin')}
          active={isActive('/account/twin')}
        />
      </DropdownSection>

      {user.role === 'ADMIN' && (
        <>
          <DropdownDivider />
          <DropdownSection label="Administration">
            <DropdownItem
              icon={<MembersIcon />}
              label="Members"
              onClick={() => navigate('/members')}
              active={isActive('/members')}
            />
            <DropdownItem
              icon={<AuditIcon />}
              label="Audit Log"
              onClick={() => navigate('/audit')}
              active={isActive('/audit')}
            />
          </DropdownSection>
        </>
      )}

      {user.is_platform_admin && (
        <>
          <DropdownDivider />
          <DropdownSection label="Platform Operator">
            <DropdownItem
              icon={<OrgIcon />}
              label="Organisations"
              onClick={() => navigate('/operator/organisations')}
              active={isActive('/operator/organisations')}
            />
            <DropdownItem
              icon={<UsersIcon />}
              label="All Users"
              onClick={() => navigate('/operator/users')}
              active={isActive('/operator/users')}
            />
            <DropdownItem
              icon={<CorpusIcon />}
              label="Legal Corpus"
              onClick={() => navigate('/operator/legal-corpus')}
              active={isActive('/operator/legal-corpus')}
            />
          </DropdownSection>
        </>
      )}

      <DropdownDivider />

      <DropdownSection>
        <DropdownItem
          icon={<SwitchIcon />}
          label="Switch Workspace"
          onClick={handleSwitchWorkspace}
        />
        <DropdownItem
          icon={<LogoutIcon />}
          label="Sign Out"
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

function AIProfileIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function MembersIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function AuditIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14,2 14,8 20,8" />
      <line x1="12" y1="18" x2="12" y2="12" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}

function OrgIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9,22 9,12 15,12 15,22" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function CorpusIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <path d="M8 7h8" />
      <path d="M8 11h8" />
      <path d="M8 15h5" />
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
