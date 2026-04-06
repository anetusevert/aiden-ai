'use client';

interface HeyAminLogoProps {
  variant: 'full' | 'mark';
  size?: number;
  className?: string;
  color?: string;
}

const DEFAULT_SIZE = { full: 140, mark: 32 } as const;

/**
 * HA monogram rendered as an inline SVG.
 * Uses `currentColor` by default so it inherits the parent text color
 * (white on dark surfaces). Pass `color` to override explicitly.
 *
 * - `mark`  – square monogram at `size x size`
 * - `full`  – same monogram at a larger default size (the mark IS the brand)
 */
export function HeyAminLogo({
  variant,
  size,
  className,
  color,
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
      {/* H: top-left block */}
      <rect x="0" y="1" width="10" height="6" />
      {/* H: upper diagonal bar */}
      <polygon points="0,13 17,10 17,14 0,17" />
      {/* H: lower diagonal bar */}
      <polygon points="0,21 17,18 17,22 0,25" />
      {/* A with counter cutout */}
      <path
        fillRule="evenodd"
        d="M18,44 L28,2 H34 L44,44 H37 L35,34 H25 L23,44 Z M28,26 H32 L30,14 Z"
      />
    </svg>
  );
}
