'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';

export function MarketingHeader() {
  const { isAuthenticated } = useAuth();

  return (
    <header className="ha-header">
      <Link href="/" className="ha-logo">
        Hey<span className="ha-logo-accent">Amin</span>
      </Link>
      <nav>
        {isAuthenticated ? (
          <Link
            href="/documents"
            className="ha-btn-primary"
            style={{ padding: '0.5rem 1.5rem', fontSize: '0.8125rem' }}
          >
            Open App
          </Link>
        ) : (
          <Link href="/login" className="ha-nav-link">
            Sign in
          </Link>
        )}
      </nav>
    </header>
  );
}
