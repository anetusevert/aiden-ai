'use client';

import { useState, useEffect } from 'react';
import { getStoredToken } from '@/lib/apiClient';

const DISMISS_KEY = 'aiden_dev_banner_dismissed';

/**
 * Development environment indicator banner.
 *
 * Displays when JWT is stored in localStorage to indicate
 * this is a development/testing environment.
 *
 * Can be dismissed for the current session.
 */
export function DevModeBanner() {
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);

    // Check if token exists and banner wasn't dismissed this session
    const token = getStoredToken();
    const dismissed = sessionStorage.getItem(DISMISS_KEY);

    if (token && !dismissed) {
      setVisible(true);
    }
  }, []);

  const handleDismiss = () => {
    setVisible(false);
    sessionStorage.setItem(DISMISS_KEY, 'true');
  };

  if (!mounted || !visible) {
    return null;
  }

  return (
    <div className="system-banner system-banner-warning">
      <div className="system-banner-content">
        <span className="system-banner-text">
          <strong>Development Environment</strong>
          <span className="system-banner-separator">—</span>
          Session tokens are stored locally for development purposes.
        </span>
        <a href="/account" className="system-banner-link">
          View Session Details
        </a>
      </div>
      <button
        onClick={handleDismiss}
        className="system-banner-dismiss"
        aria-label="Dismiss"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M1 1L13 13M1 13L13 1" />
        </svg>
      </button>
    </div>
  );
}
