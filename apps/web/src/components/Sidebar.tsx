'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { useSidebarWorkflows } from '@/hooks/useSidebarWorkflows';
import { navRailContainer, navRailItem } from '@/lib/motion';
import type { SoulDetail } from '@/lib/apiClient';
import type {
  WorkflowDefinition,
  WorkflowCategory,
} from '@/lib/workflowRegistry';
import type {
  ScoredWorkflow,
  ContinueWorkflow,
  WorkflowGroup,
} from '@/hooks/useSidebarWorkflows';

interface SidebarProps {
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
  soul: SoulDetail | null;
}

// ============================================================================
// Category icons — small visual identifier per workflow category
// ============================================================================

const CATEGORY_ICONS: Record<WorkflowCategory, React.ReactNode> = {
  litigation: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
    </svg>
  ),
  corporate: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
    </svg>
  ),
  compliance: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  employment: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  arbitration: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </svg>
  ),
  enforcement: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12,6 12,12 16,14" />
    </svg>
  ),
  research: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  management: (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <path d="M12 20V10" />
      <path d="M18 20V4" />
      <path d="M6 20v-4" />
    </svg>
  ),
};

// Static reference items (not part of the dynamic workflow registry)
const referenceItems = [
  {
    href: '/global-legal',
    label: 'Global Legal Library',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    ),
  },
];

const adminItems = [
  {
    href: '/members',
    label: 'Members & Orgs',
    icon: (
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
];

// ============================================================================
// Workflow item icon — small generic icon for workflow entries
// ============================================================================

function WorkflowItemIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
    >
      <polyline points="4,17 10,11 4,5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function ForYouBadge({ reason }: { reason: ScoredWorkflow['reason'] }) {
  if (reason === 'default') return null;
  const labels: Record<string, string> = {
    twin_match: 'AI',
    frequent: 'Used often',
    recent: 'Recent',
  };
  return (
    <span className={`sidebar-badge sidebar-badge-${reason}`}>
      {labels[reason] || ''}
    </span>
  );
}

// ============================================================================
// Component
// ============================================================================

export function Sidebar({
  collapsed,
  onCollapsedChange,
  mobileOpen,
  onMobileClose,
  soul,
}: SidebarProps) {
  const pathname = usePathname();
  const { user, workspaceContext } = useAuth();
  const { forYou, continueItems, allGroups, trackAccess } =
    useSidebarWorkflows(soul);

  // Track which category groups are expanded
  const [expandedGroups, setExpandedGroups] = useState<Set<WorkflowCategory>>(
    new Set()
  );

  const toggleGroup = useCallback((cat: WorkflowCategory) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  // Restore collapse preference
  useEffect(() => {
    const saved = localStorage.getItem('heyamin-sidebar-collapsed');
    if (saved === 'true') onCollapsedChange(true);
  }, [onCollapsedChange]);

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'b') {
        e.preventDefault();
        const next = !collapsed;
        onCollapsedChange(next);
        localStorage.setItem('heyamin-sidebar-collapsed', String(next));
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [collapsed, onCollapsedChange]);

  const toggleCollapse = () => {
    const next = !collapsed;
    onCollapsedChange(next);
    localStorage.setItem('heyamin-sidebar-collapsed', String(next));
  };

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + '/');

  // Track workflow when navigating
  const handleWorkflowClick = (workflow: WorkflowDefinition) => {
    trackAccess(workflow.id);
    onMobileClose();
  };

  // ── Render Helpers ──

  const renderWorkflowLink = (
    workflow: WorkflowDefinition,
    badge?: React.ReactNode
  ) => {
    const active = isActive(workflow.route);
    return (
      <Link
        key={workflow.id}
        href={workflow.route}
        className={`sidebar-link sidebar-workflow-link ${active ? 'sidebar-link-active' : ''}`}
        onClick={() => handleWorkflowClick(workflow)}
        title={collapsed ? workflow.name : workflow.description}
      >
        <span className="sidebar-link-icon">
          <WorkflowItemIcon />
        </span>
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              className="sidebar-link-label"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.15 }}
            >
              {workflow.name}
            </motion.span>
          )}
        </AnimatePresence>
        {!collapsed && badge}
        {active && (
          <motion.div
            className="sidebar-active-indicator"
            layoutId="sidebar-active-indicator"
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
          />
        )}
      </Link>
    );
  };

  const renderStaticLink = (item: {
    href: string;
    label: string;
    icon: React.ReactNode;
  }) => {
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`sidebar-link ${active ? 'sidebar-link-active' : ''}`}
        onClick={onMobileClose}
        title={collapsed ? item.label : undefined}
      >
        <span className="sidebar-link-icon">{item.icon}</span>
        <AnimatePresence>
          {!collapsed && (
            <motion.span
              className="sidebar-link-label"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.15 }}
            >
              {item.label}
            </motion.span>
          )}
        </AnimatePresence>
        {active && (
          <motion.div
            className="sidebar-active-indicator"
            layoutId="sidebar-active-indicator"
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
          />
        )}
      </Link>
    );
  };

  const renderSectionLabel = (label: string) => (
    <AnimatePresence>
      {!collapsed ? (
        <motion.div
          className="sidebar-section-label"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.1 }}
        >
          {label}
        </motion.div>
      ) : (
        <div className="sidebar-section-dot" />
      )}
    </AnimatePresence>
  );

  const renderCategoryGroup = (group: WorkflowGroup) => {
    const isExpanded = expandedGroups.has(group.category.id);
    const visibleWorkflows = isExpanded
      ? group.workflows
      : group.workflows.slice(0, 0);

    return (
      <div key={group.category.id} className="sidebar-category-group">
        <button
          className="sidebar-category-header"
          onClick={() => toggleGroup(group.category.id)}
          title={collapsed ? group.category.name : undefined}
        >
          <span className="sidebar-category-icon">
            {CATEGORY_ICONS[group.category.id]}
          </span>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                className="sidebar-category-name"
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.15 }}
              >
                {group.category.name}
              </motion.span>
            )}
          </AnimatePresence>
          {!collapsed && (
            <span className="sidebar-category-count">
              {group.workflows.length}
            </span>
          )}
          {!collapsed && (
            <svg
              className={`sidebar-category-chevron ${isExpanded ? 'sidebar-category-chevron-open' : ''}`}
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="6,9 12,15 18,9" />
            </svg>
          )}
        </button>

        <AnimatePresence>
          {isExpanded && !collapsed && (
            <motion.div
              className="sidebar-category-items"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: [0.2, 0.8, 0.2, 1] }}
            >
              {group.workflows.map(wf => renderWorkflowLink(wf))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  // ── Time-ago helper for "Continue" section ──
  const timeAgo = (ts: number) => {
    const mins = Math.floor((Date.now() - ts) / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  };

  return (
    <>
      {mobileOpen && (
        <div className="sidebar-overlay" onClick={onMobileClose} />
      )}

      <aside
        className={`sidebar ${collapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'sidebar-open' : ''}`}
      >
        {/* Brand */}
        <div className="sidebar-brand">
          <Link
            href="/documents"
            className="sidebar-logo"
            onClick={onMobileClose}
          >
            {collapsed ? (
              <span
                className="sidebar-logo-mark"
                style={{ color: 'var(--amin-accent, #d4a017)' }}
              >
                H
              </span>
            ) : (
              <>
                <span style={{ fontWeight: 300 }}>Hey</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: 'var(--amin-accent, #d4a017)',
                  }}
                >
                  Amin
                </span>
              </>
            )}
          </Link>
        </div>

        {/* Workspace context */}
        {user && !collapsed && (
          <motion.div
            className="sidebar-workspace"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 }}
          >
            <div className="sidebar-workspace-pill">
              <div className="sidebar-workspace-icon">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                  <polyline points="9,22 9,12 15,12 15,22" />
                </svg>
              </div>
              <span className="sidebar-workspace-name">
                {workspaceContext?.name || 'Workspace'}
              </span>
            </div>
          </motion.div>
        )}

        {/* Navigation — dynamic sections */}
        <nav className="sidebar-nav">
          {/* ── FOR YOU — personalized by twin + usage ── */}
          {forYou.length > 0 && (
            <div className="sidebar-section sidebar-section-foryou">
              {renderSectionLabel('For You')}
              <motion.div
                variants={navRailContainer}
                initial="hidden"
                animate="visible"
              >
                {forYou.map(scored => (
                  <motion.div key={scored.workflow.id} variants={navRailItem}>
                    {renderWorkflowLink(
                      scored.workflow,
                      <ForYouBadge reason={scored.reason} />
                    )}
                  </motion.div>
                ))}
              </motion.div>
            </div>
          )}

          {/* ── CONTINUE — recently accessed ── */}
          {continueItems.length > 0 && !collapsed && (
            <div className="sidebar-section sidebar-section-continue">
              {renderSectionLabel('Continue')}
              <div className="sidebar-continue-list">
                {continueItems.map(item => (
                  <Link
                    key={item.workflow.id}
                    href={item.workflow.route}
                    className={`sidebar-continue-item ${isActive(item.workflow.route) ? 'sidebar-continue-item-active' : ''}`}
                    onClick={() => handleWorkflowClick(item.workflow)}
                  >
                    <span className="sidebar-continue-name">
                      {item.workflow.name}
                    </span>
                    <span className="sidebar-continue-time">
                      {timeAgo(item.lastAccessedAt)}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* ── ALL WORKFLOWS — grouped by category, collapsible ── */}
          <div className="sidebar-section sidebar-section-all">
            {renderSectionLabel('All Workflows')}
            {!collapsed && allGroups.map(renderCategoryGroup)}
            {collapsed && (
              <div className="sidebar-collapsed-categories">
                {allGroups.map(group => (
                  <Link
                    key={group.category.id}
                    href={group.workflows[0]?.route || '/documents'}
                    className="sidebar-collapsed-category-icon"
                    title={group.category.name}
                    onClick={onMobileClose}
                  >
                    {CATEGORY_ICONS[group.category.id]}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* ── REFERENCE — static tools ── */}
          <div className="sidebar-section">
            {renderSectionLabel('Reference')}
            <motion.div
              variants={navRailContainer}
              initial="hidden"
              animate="visible"
            >
              {referenceItems.map(item => (
                <motion.div key={item.href} variants={navRailItem}>
                  {renderStaticLink(item)}
                </motion.div>
              ))}
            </motion.div>
          </div>

          {/* ── ADMIN — role-gated ── */}
          {user?.role === 'ADMIN' && (
            <div className="sidebar-section">
              {renderSectionLabel('Admin')}
              <motion.div
                variants={navRailContainer}
                initial="hidden"
                animate="visible"
              >
                {adminItems.map(item => (
                  <motion.div key={item.href} variants={navRailItem}>
                    {renderStaticLink(item)}
                  </motion.div>
                ))}
              </motion.div>
            </div>
          )}
        </nav>

        {/* Footer — collapse toggle */}
        <div className="sidebar-footer">
          <button
            className="sidebar-collapse-toggle"
            onClick={toggleCollapse}
            title={
              collapsed
                ? 'Expand sidebar (Ctrl+B)'
                : 'Collapse sidebar (Ctrl+B)'
            }
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              style={{
                transform: collapsed ? 'rotate(180deg)' : 'none',
                transition: 'transform 200ms ease',
              }}
            >
              <polyline points="11,17 6,12 11,7" />
              <polyline points="18,17 13,12 18,7" />
            </svg>
            <AnimatePresence>
              {!collapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.1 }}
                  className="sidebar-collapse-label"
                >
                  Collapse
                </motion.span>
              )}
            </AnimatePresence>
          </button>
        </div>
      </aside>
    </>
  );
}
