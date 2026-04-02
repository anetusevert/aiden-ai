'use client';

import { useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DropdownMenuProps {
  open: boolean;
  onClose: () => void;
  trigger: React.ReactNode;
  children: React.ReactNode;
  align?: 'left' | 'right';
  className?: string;
}

export function DropdownMenu({
  open,
  onClose,
  trigger,
  children,
  align = 'right',
  className = '',
}: DropdownMenuProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [open, handleKeyDown]);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [open, onClose]);

  return (
    <div ref={containerRef} className={`dropdown-container ${className}`}>
      {trigger}
      <AnimatePresence>
        {open && (
          <motion.div
            className={`dropdown-menu dropdown-menu-${align}`}
            initial={{ opacity: 0, scale: 0.95, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -4 }}
            transition={{ duration: 0.15, ease: [0.2, 0.8, 0.2, 1] }}
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface DropdownItemProps {
  icon?: React.ReactNode;
  label: string;
  onClick?: () => void;
  href?: string;
  active?: boolean;
  danger?: boolean;
  className?: string;
}

export function DropdownItem({
  icon,
  label,
  onClick,
  href,
  active = false,
  danger = false,
  className = '',
}: DropdownItemProps) {
  const classes = `dropdown-item ${active ? 'dropdown-item-active' : ''} ${danger ? 'dropdown-item-danger' : ''} ${className}`;

  if (href) {
    return (
      <a href={href} className={classes} onClick={onClick}>
        {icon && <span className="dropdown-item-icon">{icon}</span>}
        <span className="dropdown-item-label">{label}</span>
      </a>
    );
  }

  return (
    <button type="button" className={classes} onClick={onClick}>
      {icon && <span className="dropdown-item-icon">{icon}</span>}
      <span className="dropdown-item-label">{label}</span>
    </button>
  );
}

export function DropdownDivider() {
  return <div className="dropdown-divider" />;
}

export function DropdownSection({
  label,
  children,
}: {
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="dropdown-section">
      {label && <div className="dropdown-section-label">{label}</div>}
      {children}
    </div>
  );
}
