'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import { useEffect, useState } from 'react';

export function MarketingHeader() {
  const { isAuthenticated } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`ha-header${scrolled ? ' scrolled' : ''}`}>
      <Link href="/" className="ha-logo-lockup">
        <HeyAminLogo variant="mark" size={36} />
        <span className="ha-logo-wordmark">HeyAmin</span>
      </Link>

      <div className="ha-header-nav">
        <div className="ha-header-nav-links">
          <a href="#platform" className="ha-header-nav-link">
            Platform
          </a>
          <a href="#research" className="ha-header-nav-link">
            Research
          </a>
          <a href="#security" className="ha-header-nav-link">
            Security
          </a>
          <a href="#about" className="ha-header-nav-link">
            About
          </a>
        </div>

        <div className="ha-header-actions">
          {isAuthenticated ? (
            <Link href="/home" className="ha-btn-primary ha-btn-sm">
              Open App
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="ha-btn-ghost"
                style={{ height: 36, fontSize: 13 }}
              >
                Sign in
              </Link>
              <Link href="/login" className="ha-btn-primary ha-btn-sm">
                Request Access
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
