'use client';

import React from 'react';

export interface AlertProps {
  variant?: 'success' | 'error' | 'warning' | 'info' | 'neutral';
  title?: string;
  children: React.ReactNode;
  className?: string;
  onDismiss?: () => void;
}

export function Alert({
  variant = 'info',
  title,
  children,
  className = '',
  onDismiss,
}: AlertProps) {
  const classes = ['alert', `alert-${variant}`, className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} role="alert">
      <div className="alert-content">
        {title && <div className="alert-title">{title}</div>}
        <div>{children}</div>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="banner-dismiss"
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}

// Banner component for full-width contextual messages
export interface BannerProps {
  variant?: 'info' | 'warning' | 'success' | 'neutral';
  children: React.ReactNode;
  className?: string;
  onDismiss?: () => void;
}

export function Banner({
  variant = 'info',
  children,
  className = '',
  onDismiss,
}: BannerProps) {
  const classes = ['banner', `banner-${variant}`, className]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} role="status">
      <span>{children}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="banner-dismiss"
          aria-label="Dismiss"
        >
          ✕
        </button>
      )}
    </div>
  );
}
