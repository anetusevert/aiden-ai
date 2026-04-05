'use client';

/* eslint-disable @next/next/no-img-element */

interface HeyAminLogoProps {
  variant: 'full' | 'mark';
  size?: number;
  className?: string;
}

const DEFAULT_SIZE = { full: 140, mark: 32 } as const;

export function HeyAminLogo({
  variant,
  size,
  className,
}: HeyAminLogoProps) {
  const resolvedSize = size ?? DEFAULT_SIZE[variant];

  if (variant === 'mark') {
    return (
      <img
        src="/brand/heyamin-logo-stacked.png"
        alt="HeyAmin"
        className={className}
        style={{
          width: resolvedSize,
          height: resolvedSize,
          objectFit: 'contain',
          display: 'block',
          flexShrink: 0,
        }}
      />
    );
  }

  return (
    <img
      src="/brand/heyamin-logo.png"
      alt="HeyAmin"
      className={className}
      style={{
        width: resolvedSize,
        height: 'auto',
        display: 'block',
      }}
    />
  );
}
