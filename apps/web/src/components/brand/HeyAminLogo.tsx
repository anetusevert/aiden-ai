'use client';

import Image from 'next/image';

interface HeyAminLogoProps {
  variant: 'full' | 'mark';
  size?: number;
  className?: string;
}

const DEFAULT_SIZE = { full: 120, mark: 40 } as const;

const LOGO_SRC = {
  full: '/brand/heyamin-logo-full.png',
  mark: '/brand/ha-mark-tight.png',
} as const;

export function HeyAminLogo({ variant, size, className }: HeyAminLogoProps) {
  const resolvedSize = size ?? DEFAULT_SIZE[variant];
  const width = variant === 'full' ? resolvedSize : 289;
  const height = variant === 'full' ? Math.round(resolvedSize * 0.5) : 197;

  return (
    <Image
      src={LOGO_SRC[variant]}
      alt="HeyAmin"
      width={width}
      height={height}
      className={className}
      priority
      style={{
        width: resolvedSize,
        height: 'auto',
        objectFit: 'contain',
        display: 'block',
        flexShrink: 0,
      }}
    />
  );
}
