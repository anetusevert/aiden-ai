'use client';

import {
  AminAvatarV2,
  type AvatarSize,
  type AvatarState,
} from './AminAvatarV2';

interface AminAvatarProps {
  size?: 'sm' | 'md' | 'lg';
  status?: 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';
}

const sizeRemap: Record<string, AvatarSize> = {
  sm: 'small',
  md: 'medium',
  lg: 'full',
};

export function AminAvatar({ size = 'md', status = 'idle' }: AminAvatarProps) {
  return (
    <AminAvatarV2
      size={sizeRemap[size] ?? 'medium'}
      state={status as AvatarState}
      showRing={size !== 'sm'}
    />
  );
}
