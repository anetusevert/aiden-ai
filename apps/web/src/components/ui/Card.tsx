import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  flush?: boolean;
  compact?: boolean;
}

export function Card({
  children,
  className = '',
  flush = false,
  compact = false,
}: CardProps) {
  const classes = [
    'card',
    flush ? 'card-flush' : '',
    compact ? 'card-compact' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <div className={classes}>{children}</div>;
}

export interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
  action?: React.ReactNode;
}

export function CardHeader({
  children,
  className = '',
  action,
}: CardHeaderProps) {
  if (action) {
    return (
      <div
        className={`card-header flex items-center justify-between ${className}`}
      >
        <div>{children}</div>
        <div>{action}</div>
      </div>
    );
  }
  return <div className={`card-header ${className}`}>{children}</div>;
}

export interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
  subtitle?: string;
}

export function CardTitle({
  children,
  className = '',
  subtitle,
}: CardTitleProps) {
  return (
    <>
      <h3 className={`card-title ${className}`}>{children}</h3>
      {subtitle && <p className="card-subtitle">{subtitle}</p>}
    </>
  );
}

export function CardBody({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`card-body ${className}`}>{children}</div>;
}

export function CardFooter({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`card-footer ${className}`}>{children}</div>;
}
