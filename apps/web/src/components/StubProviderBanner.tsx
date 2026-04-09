'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/AuthContext';

const DISMISS_KEY = 'aiden_stub_banner_dismissed';

interface LLMStatus {
  provider: string;
  model: string;
  configured_provider: string;
  api_key_set: boolean;
  environment: string;
  is_fallback: boolean;
}

/**
 * Stub Provider indicator banner.
 *
 * Displays when the backend is using the Stub LLM provider, which produces
 * generic/deterministic answers instead of real LLM outputs.
 */
export function StubProviderBanner() {
  const { user } = useAuth();
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [visible, setVisible] = useState(false);
  const [mounted, setMounted] = useState(false);
  const canManageLlmSettings =
    user?.role === 'ADMIN' || user?.is_platform_admin === true;

  useEffect(() => {
    setMounted(true);

    if (!canManageLlmSettings) {
      setVisible(false);
      return;
    }

    const dismissed = sessionStorage.getItem(DISMISS_KEY);
    if (dismissed) {
      return;
    }

    const fetchStatus = async () => {
      try {
        const baseUrl =
          process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/llm/status`);

        if (!response.ok) {
          return;
        }

        const status: LLMStatus = await response.json();
        setLlmStatus(status);

        if (status.provider === 'stub') {
          setVisible(true);
        }
      } catch {
        // Silently fail - endpoint might not be available
      }
    };

    fetchStatus();
  }, [canManageLlmSettings]);

  const handleDismiss = () => {
    setVisible(false);
    sessionStorage.setItem(DISMISS_KEY, 'true');
  };

  if (!mounted || !canManageLlmSettings || !visible || !llmStatus) {
    return null;
  }

  const message = llmStatus.is_fallback
    ? 'LLM provider unavailable. Using placeholder responses for testing.'
    : 'Using placeholder LLM responses. Configure your LLM provider for production use.';

  return (
    <div className="system-banner system-banner-info">
      <div className="system-banner-content">
        <span className="system-banner-text">
          <strong>Test Mode</strong>
          <span className="system-banner-separator">—</span>
          {message}
        </span>
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
