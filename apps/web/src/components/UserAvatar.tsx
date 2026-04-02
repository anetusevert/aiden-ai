'use client';

import { useMemo } from 'react';

export type AvatarSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

interface UserAvatarProps {
  user: {
    full_name?: string | null;
    email?: string | null;
    avatar_url?: string | null;
    user_id?: string;
  };
  size?: AvatarSize;
  showRing?: boolean;
  onClick?: () => void;
  className?: string;
}

const sizeMap: Record<AvatarSize, number> = {
  xs: 24,
  sm: 32,
  md: 40,
  lg: 64,
  xl: 96,
};

const fontSizeMap: Record<AvatarSize, string> = {
  xs: '0.625rem',
  sm: '0.75rem',
  md: '0.875rem',
  lg: '1.25rem',
  xl: '1.75rem',
};

const AVATAR_GRADIENTS = [
  'linear-gradient(135deg, #1e3a5f 0%, #2d4a73 100%)',
  'linear-gradient(135deg, #4a1942 0%, #6b3fa0 100%)',
  'linear-gradient(135deg, #1a4731 0%, #2d6a4f 100%)',
  'linear-gradient(135deg, #5c2d0e 0%, #8b5e3c 100%)',
  'linear-gradient(135deg, #1e3a5f 0%, #3a6ea5 100%)',
  'linear-gradient(135deg, #4a1d6b 0%, #7c3aed 100%)',
  'linear-gradient(135deg, #0e4429 0%, #196f3d 100%)',
  'linear-gradient(135deg, #6b3fa0 0%, #9b59b6 100%)',
];

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function getInitials(name?: string | null, email?: string | null): string {
  if (name) {
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
  }
  if (email) {
    return email[0].toUpperCase();
  }
  return '?';
}

export function UserAvatar({
  user,
  size = 'md',
  showRing = false,
  onClick,
  className = '',
}: UserAvatarProps) {
  const px = sizeMap[size];
  const fontSize = fontSizeMap[size];

  const initials = useMemo(
    () => getInitials(user.full_name, user.email),
    [user.full_name, user.email]
  );

  const gradient = useMemo(() => {
    const seed = user.user_id || user.email || 'default';
    const idx = hashString(seed) % AVATAR_GRADIENTS.length;
    return AVATAR_GRADIENTS[idx];
  }, [user.user_id, user.email]);

  const hasPhoto = !!user.avatar_url;
  const isClickable = !!onClick;

  return (
    <button
      type="button"
      className={`user-avatar user-avatar-${size} ${showRing ? 'user-avatar-ring' : ''} ${isClickable ? 'user-avatar-clickable' : ''} ${className}`}
      style={{
        width: px,
        height: px,
        minWidth: px,
        minHeight: px,
      }}
      onClick={onClick}
      tabIndex={isClickable ? 0 : -1}
      aria-label={user.full_name || user.email || 'User avatar'}
    >
      {hasPhoto ? (
        <img
          src={user.avatar_url!}
          alt={user.full_name || 'User'}
          className="user-avatar-img"
          width={px}
          height={px}
        />
      ) : (
        <span
          className="user-avatar-initials"
          style={{ background: gradient, fontSize }}
        >
          {initials}
        </span>
      )}
    </button>
  );
}
