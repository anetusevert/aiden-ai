'use client';

interface HeyAminLogoProps {
  variant: 'full' | 'mark';
  size?: number;
  color?: string;
  className?: string;
}

const DEFAULT_SIZE = { full: 120, mark: 40 } as const;

export function HeyAminLogo({
  variant,
  size,
  color,
  className,
}: HeyAminLogoProps) {
  const resolvedSize = size ?? DEFAULT_SIZE[variant];

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 44"
      fill={color ?? 'currentColor'}
      className={className}
      role="img"
      aria-label="HeyAmin"
      style={{
        width: resolvedSize,
        height: resolvedSize,
        display: 'block',
        flexShrink: 0,
      }}
    >
      <rect x="0" y="1" width="10" height="6" />
      <polygon points="0,13 17,10 17,14 0,17" />
      <polygon points="0,21 17,18 17,22 0,25" />
      <path
        fillRule="evenodd"
        d="M18,44 L28,2 H34 L44,44 H37 L35,34 H25 L23,44 Z M28,26 H32 L30,14 Z"
      />
    </svg>
  );
}
