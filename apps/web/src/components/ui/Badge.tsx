import React from 'react';

export interface BadgeProps {
  variant?:
    | 'success'
    | 'warning'
    | 'error'
    | 'info'
    | 'muted'
    | 'admin'
    | 'editor'
    | 'viewer'
    | 'global-law'
    | 'default';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  children: React.ReactNode;
}

export function Badge({
  variant = 'muted',
  size = 'md',
  className = '',
  children,
}: BadgeProps) {
  const sizeClass = size !== 'md' ? `badge-${size}` : '';
  const classes = ['badge', `badge-${variant}`, sizeClass, className]
    .filter(Boolean)
    .join(' ');

  return <span className={classes}>{children}</span>;
}

// Role badge with automatic variant selection
export interface RoleBadgeProps {
  role: 'ADMIN' | 'EDITOR' | 'VIEWER' | string;
  size?: 'sm' | 'md' | 'lg';
}

export function RoleBadge({ role, size = 'md' }: RoleBadgeProps) {
  const variant =
    role === 'ADMIN' ? 'admin' : role === 'EDITOR' ? 'editor' : 'viewer';
  return (
    <Badge variant={variant} size={size}>
      {role}
    </Badge>
  );
}

// Status badge with automatic variant selection
export interface StatusBadgeProps {
  status: 'indexed' | 'pending' | 'failed' | 'processing' | string;
  size?: 'sm' | 'md' | 'lg';
}

export function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const variantMap: Record<string, BadgeProps['variant']> = {
    indexed: 'success',
    completed: 'success',
    success: 'success',
    pending: 'warning',
    processing: 'info',
    failed: 'error',
    error: 'error',
  };
  const variant = variantMap[status.toLowerCase()] || 'muted';
  return (
    <Badge variant={variant} size={size}>
      {status}
    </Badge>
  );
}

// ============================================================================
// Source Type Badge - Distinguishes global law from workspace documents
// ============================================================================

export type SourceType = 'workspace_document' | 'global_legal';

export interface SourceTypeBadgeProps {
  sourceType: SourceType;
  /** Optional jurisdiction to display (e.g., "KSA", "UAE") */
  jurisdiction?: string;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Badge that visually distinguishes evidence sources.
 *
 * - Global Law: Blue badge with jurisdiction (e.g., "GLOBAL LAW — KSA")
 * - Workspace Document: Gray badge for clarity
 *
 * This ensures users can never confuse global legal sources with workspace documents.
 */
export function SourceTypeBadge({
  sourceType,
  jurisdiction,
  size = 'sm',
}: SourceTypeBadgeProps) {
  if (sourceType === 'global_legal') {
    const label = jurisdiction ? `GLOBAL LAW — ${jurisdiction}` : 'GLOBAL LAW';
    return (
      <Badge
        variant="global-law"
        size={size}
        className="source-type-badge source-type-global"
      >
        <span className="source-type-icon">⚖️</span>
        {label}
      </Badge>
    );
  }

  // Workspace documents get a subtle badge for explicit clarity
  return (
    <Badge
      variant="default"
      size={size}
      className="source-type-badge source-type-workspace"
    >
      <span className="source-type-icon">📄</span>
      WORKSPACE
    </Badge>
  );
}
