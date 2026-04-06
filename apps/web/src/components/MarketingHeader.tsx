'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';

export function MarketingHeader() {
  const { isAuthenticated } = useAuth();

  return (
    <header className="ha-header">
      <Link
        href="/"
        className="ha-logo"
        style={{ display: 'inline-flex', alignItems: 'center' }}
      >
        <HeyAminLogo variant="full" size={120} />
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
