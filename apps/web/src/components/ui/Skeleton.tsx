import React from 'react';

export interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'title' | 'avatar' | 'button' | 'custom';
}

export function Skeleton({
  className = '',
  width,
  height,
  variant = 'text',
}: SkeletonProps) {
  const variantClasses: Record<string, string> = {
    text: 'skeleton-text',
    title: 'skeleton-title',
    avatar: 'skeleton-avatar',
    button: 'skeleton-button',
    custom: '',
  };

  const classes = ['skeleton', variantClasses[variant], className]
    .filter(Boolean)
    .join(' ');

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === 'number' ? `${width}px` : width;
  if (height)
    style.height = typeof height === 'number' ? `${height}px` : height;

  return (
    <div
      className={classes}
      style={Object.keys(style).length ? style : undefined}
    />
  );
}

// Skeleton row for table loading states
export function SkeletonRow({ columns = 4 }: { columns?: number }) {
  return (
    <div className="skeleton-row">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={i} variant="text" width={i === 0 ? '60%' : '80%'} />
      ))}
    </div>
  );
}

// Skeleton table for loading states
export function SkeletonTable({
  rows = 5,
  columns = 4,
}: {
  rows?: number;
  columns?: number;
}) {
  return (
    <div style={{ padding: 'var(--space-4)' }}>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} columns={columns} />
      ))}
    </div>
  );
}

// Loading indicator with spinner
export function LoadingSpinner({
  size = 'md',
  text,
}: {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}) {
  const sizeClass = size !== 'md' ? `spinner-${size}` : '';
  return (
    <div className="loading">
      <span className={`spinner ${sizeClass}`} />
      {text && <span style={{ marginLeft: 'var(--space-3)' }}>{text}</span>}
    </div>
  );
}
