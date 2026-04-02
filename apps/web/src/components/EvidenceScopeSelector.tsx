'use client';

/**
 * Evidence Scope Selector Component
 *
 * An enterprise-grade dropdown for selecting evidence retrieval scope:
 * - Workspace documents (default)
 * - Global law library
 * - Both
 *
 * Persists selection per workspace in localStorage.
 */

import { useState, useEffect } from 'react';
import type { EvidenceScope } from '@/lib/apiClient';

// LocalStorage key prefix
const STORAGE_KEY_PREFIX = 'aiden_evidence_scope_';

interface EvidenceScopeSelectorProps {
  /** Current workspace ID for persistence */
  workspaceId: string;
  /** Callback when scope changes */
  onScopeChange: (scope: EvidenceScope) => void;
  /** Initial scope (defaults to 'workspace') */
  initialScope?: EvidenceScope;
  /** Whether to show as compact dropdown */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

const SCOPE_OPTIONS: {
  value: EvidenceScope;
  label: string;
  description: string;
}[] = [
  {
    value: 'workspace',
    label: 'Workspace Documents',
    description: 'Search only your workspace documents',
  },
  {
    value: 'global',
    label: 'Global Law Library',
    description: 'Search only the global legal corpus',
  },
  {
    value: 'both',
    label: 'Both Sources',
    description: 'Search workspace and global law library',
  },
];

function getStorageKey(workspaceId: string): string {
  return `${STORAGE_KEY_PREFIX}${workspaceId}`;
}

function loadSavedScope(workspaceId: string): EvidenceScope {
  if (typeof window === 'undefined') return 'workspace';
  try {
    const saved = localStorage.getItem(getStorageKey(workspaceId));
    if (saved === 'global' || saved === 'both' || saved === 'workspace') {
      return saved;
    }
  } catch {
    // localStorage might be unavailable
  }
  return 'workspace';
}

function saveScopeToStorage(workspaceId: string, scope: EvidenceScope): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(getStorageKey(workspaceId), scope);
  } catch {
    // localStorage might be unavailable
  }
}

export function EvidenceScopeSelector({
  workspaceId,
  onScopeChange,
  initialScope,
  compact = false,
  className = '',
}: EvidenceScopeSelectorProps) {
  const [scope, setScope] = useState<EvidenceScope>(
    initialScope || loadSavedScope(workspaceId)
  );
  const [isOpen, setIsOpen] = useState(false);

  // Load saved scope on mount
  useEffect(() => {
    if (!initialScope) {
      const saved = loadSavedScope(workspaceId);
      setScope(saved);
      onScopeChange(saved);
    }
  }, [workspaceId, initialScope, onScopeChange]);

  const handleScopeChange = (newScope: EvidenceScope) => {
    setScope(newScope);
    saveScopeToStorage(workspaceId, newScope);
    onScopeChange(newScope);
    setIsOpen(false);
  };

  const currentOption =
    SCOPE_OPTIONS.find(opt => opt.value === scope) || SCOPE_OPTIONS[0];

  if (compact) {
    return (
      <div className={`relative ${className}`}>
        <select
          value={scope}
          onChange={e => handleScopeChange(e.target.value as EvidenceScope)}
          className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          aria-label="Evidence scope"
        >
          {SCOPE_OPTIONS.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        Evidence Sources
      </label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-full cursor-pointer rounded-md border border-gray-300 bg-white py-2 pl-3 pr-10 text-left shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:text-sm"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="block truncate">{currentOption.label}</span>
        <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
          <svg
            className={`h-5 w-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </span>
      </button>

      {isOpen && (
        <ul
          className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm"
          role="listbox"
        >
          {SCOPE_OPTIONS.map(option => (
            <li
              key={option.value}
              className={`relative cursor-pointer select-none py-2 pl-3 pr-9 hover:bg-gray-100 ${
                scope === option.value ? 'bg-blue-50' : ''
              }`}
              onClick={() => handleScopeChange(option.value)}
              role="option"
              aria-selected={scope === option.value}
            >
              <div className="flex flex-col">
                <span
                  className={`block truncate ${
                    scope === option.value
                      ? 'font-semibold text-blue-600'
                      : 'font-normal'
                  }`}
                >
                  {option.label}
                </span>
                <span className="block truncate text-xs text-gray-500">
                  {option.description}
                </span>
              </div>
              {scope === option.value && (
                <span className="absolute inset-y-0 right-0 flex items-center pr-4 text-blue-600">
                  <svg
                    className="h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * Advanced Settings Panel that includes Evidence Scope Selector
 *
 * Shows as a collapsible "Advanced" section in workflow forms.
 */
interface AdvancedSettingsPanelProps {
  workspaceId: string;
  evidenceScope: EvidenceScope;
  onEvidenceScopeChange: (scope: EvidenceScope) => void;
  className?: string;
}

export function AdvancedSettingsPanel({
  workspaceId,
  evidenceScope,
  onEvidenceScopeChange,
  className = '',
}: AdvancedSettingsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`border-t border-gray-200 pt-4 ${className}`}>
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between text-sm font-medium text-gray-700 hover:text-gray-900"
      >
        <span>Advanced Settings</span>
        <svg
          className={`h-5 w-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          <EvidenceScopeSelector
            workspaceId={workspaceId}
            onScopeChange={onEvidenceScopeChange}
            initialScope={evidenceScope}
          />
        </div>
      )}
    </div>
  );
}

export default EvidenceScopeSelector;
