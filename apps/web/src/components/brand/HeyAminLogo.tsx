'use client';

import Image from 'next/image';

interface HeyAminLogoProps {
  variant: 'full' | 'mark';
  size?: number;
  inverted?: boolean;
  className?: string;
}

const DEFAULT_SIZE = { full: 120, mark: 32 } as const;

const LOGO_SRC = {
  full: '/brand/heyamin-logo-full.png',
  mark: '/brand/heyamin-logo-mark.png',
} as const;

export function HeyAminLogo({
  variant,
  size,
  inverted = false,
  className,
}: HeyAminLogoProps) {
  const resolvedSize = size ?? DEFAULT_SIZE[variant];
  const blendMode = inverted ? 'multiply' : 'screen';

  if (variant === 'mark') {
    return (
      <Image
        src={LOGO_SRC.mark}
        alt="HeyAmin"
        width={resolvedSize}
        height={resolvedSize}
        className={className}
        style={{
          mixBlendMode: blendMode,
          objectFit: 'contain',
          display: 'block',
          flexShrink: 0,
        }}
        priority
      />
    );
  }

  return (
    <Image
      src={LOGO_SRC.full}
      alt="HeyAmin"
      width={resolvedSize}
      height={Math.round(resolvedSize * 0.5)}
      className={className}
      style={{
        mixBlendMode: blendMode,
        objectFit: 'contain',
        display: 'block',
        flexShrink: 0,
        width: resolvedSize,
        height: 'auto',
      }}
      priority
    />
  );
}
