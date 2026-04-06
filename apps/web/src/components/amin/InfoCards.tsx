'use client';

import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useNavigation } from '@/components/NavigationLoader';

/* ─── Shared card wrapper ──────────────────────────────────────────── */

interface CardShellProps {
  icon?: React.ReactNode;
  title?: string;
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
}

function CardShell({
  icon,
  title,
  className,
  children,
  onClick,
}: CardShellProps) {
  const shared = {
    className: `info-card${className ? ` ${className}` : ''}`,
    initial: { opacity: 0, y: 12, scale: 0.97 } as const,
    animate: { opacity: 1, y: 0, scale: 1 } as const,
    exit: { opacity: 0, y: -8, scale: 0.97 } as const,
    transition: { duration: 0.25, ease: [0.2, 0.8, 0.2, 1] },
  };

  const inner = (
    <>
      {(icon || title) && (
        <div className="info-card-header">
          {icon && <span className="info-card-icon">{icon}</span>}
          {title && <span className="info-card-title">{title}</span>}
        </div>
      )}
      <div className="info-card-body">{children}</div>
    </>
  );

  if (onClick) {
    return (
      <motion.button
        {...shared}
        onClick={onClick}
        type="button"
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
      >
        {inner}
      </motion.button>
    );
  }

  return <motion.div {...shared}>{inner}</motion.div>;
}

/* ─── MessageCard: renders markdown content from Amin ──────────────── */

interface MessageCardProps {
  content: string;
  timestamp?: string;
}

export function MessageCard({ content }: MessageCardProps) {
  return (
    <CardShell icon={<AminIcon />} className="info-card-message">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </CardShell>
  );
}

/* ─── UserQueryCard: shows what the user asked ─────────────────────── */

interface UserQueryCardProps {
  content: string;
}

export function UserQueryCard({ content }: UserQueryCardProps) {
  return (
    <motion.div
      className="info-card info-card-user"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="info-card-body">{content}</div>
    </motion.div>
  );
}

/* ─── StatusCard: shows tool execution / thinking status ───────────── */

interface StatusCardProps {
  tool: string;
  status: 'running' | 'complete' | 'error' | 'pending_confirmation';
  summary?: string;
}

export function StatusCard({ tool, status, summary }: StatusCardProps) {
  const statusIcon =
    status === 'running' ? (
      <SpinnerIcon />
    ) : status === 'complete' ? (
      <CheckIcon />
    ) : status === 'error' ? (
      <ErrorIcon />
    ) : (
      <AlertIcon />
    );

  const friendlyName = tool
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  return (
    <CardShell
      icon={statusIcon}
      title={friendlyName}
      className={`info-card-status info-card-status-${status}`}
    >
      {summary && <p className="info-card-summary">{summary}</p>}
      {status === 'running' && (
        <div className="info-card-progress">
          <div className="info-card-progress-bar" />
        </div>
      )}
    </CardShell>
  );
}

/* ─── LinkCard: navigable card ─────────────────────────────────────── */

interface LinkCardProps {
  title: string;
  description?: string;
  href: string;
  icon?: React.ReactNode;
}

export function LinkCard({ title, description, href, icon }: LinkCardProps) {
  const { navigateTo } = useNavigation();
  return (
    <CardShell
      icon={icon ?? <LinkIcon />}
      title={title}
      className="info-card-link"
      onClick={() => navigateTo(href)}
    >
      {description && <p className="info-card-description">{description}</p>}
      <span className="info-card-go">
        Open
        <ArrowIcon />
      </span>
    </CardShell>
  );
}

/* ─── ResearchCard: expandable research result ─────────────────────── */

interface ResearchCardProps {
  title: string;
  excerpt: string;
  source?: string;
}

export function ResearchCard({ title, excerpt, source }: ResearchCardProps) {
  return (
    <CardShell
      icon={<SearchIcon />}
      title={title}
      className="info-card-research"
    >
      <p className="info-card-excerpt">{excerpt}</p>
      {source && <span className="info-card-source">{source}</span>}
    </CardShell>
  );
}

/* ─── ActionCard: card with confirm/deny buttons ───────────────────── */

interface ActionCardProps {
  title: string;
  description: string;
  riskLevel?: string;
  onConfirm?: () => void;
  onDeny?: () => void;
}

export function ActionCard({
  title,
  description,
  riskLevel,
  onConfirm,
  onDeny,
}: ActionCardProps) {
  return (
    <CardShell
      icon={<AlertIcon />}
      title={title}
      className={`info-card-action${riskLevel === 'high' ? ' info-card-action-high' : ''}`}
    >
      <p className="info-card-description">{description}</p>
      <div className="info-card-actions">
        {onDeny && (
          <button className="info-card-btn info-card-btn-deny" onClick={onDeny}>
            Deny
          </button>
        )}
        {onConfirm && (
          <button
            className="info-card-btn info-card-btn-confirm"
            onClick={onConfirm}
          >
            Approve
          </button>
        )}
      </div>
    </CardShell>
  );
}

/* ─── StreamingCard: live streaming content ─────────────────────────── */

interface StreamingCardProps {
  content: string;
}

export function StreamingCard({ content }: StreamingCardProps) {
  return (
    <CardShell icon={<AminIcon />} className="info-card-streaming">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      <span className="info-card-cursor">{'\u258a'}</span>
    </CardShell>
  );
}

/* ─── Inline SVG icons ─────────────────────────────────────────────── */

function AminIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M8 14s1.5 2 4 2 4-2 4-2" />
      <line x1="9" y1="9" x2="9.01" y2="9" />
      <line x1="15" y1="9" x2="15.01" y2="9" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="info-icon-spin"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--status-success, #22c55e)"
      strokeWidth="2"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--status-danger, #f87171)"
      strokeWidth="2"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="rgba(255,255,255,0.85)"
      strokeWidth="2"
    >
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
      <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12 5 19 12 12 19" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}
