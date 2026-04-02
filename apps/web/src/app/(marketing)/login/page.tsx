'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { apiClient } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, isLoading } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (searchParams.get('reason') === 'session_expired') {
      setSessionExpired(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/documents');
    }
  }, [isAuthenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiClient.login({ email, password });
      await login();
      router.push('/documents');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="ha-login-page">
        <p style={{ color: '#9a9ba2', fontSize: '0.875rem' }}>Loading...</p>
      </div>
    );
  }

  return (
    <div className="ha-login-page">
      <div className="ha-login-glow" aria-hidden />

      <motion.div
        className="ha-login-card"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="ha-login-brand">
          <span className="ha-login-wordmark">
            Hey<span className="ha-login-wordmark-accent">Amin</span>
          </span>
        </div>

        <h1 className="ha-login-title">Welcome back</h1>
        <p className="ha-login-sub">
          Sign in to continue to{' '}
          <span className="ha-accent">HeyAmin Cloud</span>
        </p>

        {sessionExpired && (
          <p
            className="ha-login-error"
            role="alert"
            style={{ marginBottom: '1rem' }}
          >
            Your session expired. Please sign in again.
          </p>
        )}

        <form onSubmit={handleSubmit} className="ha-form">
          <div className="ha-field">
            <label htmlFor="ha-email">Email address</label>
            <input
              id="ha-email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>

          <div className="ha-field">
            <label htmlFor="ha-password">Password</label>
            <input
              id="ha-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="ha-login-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" className="ha-btn-submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Continue'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '1.75rem' }}>
          <Link href="/" className="ha-login-footer-link">
            &larr; Back to home
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
