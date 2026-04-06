'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { getClientApiBaseUrl } from '@/lib/api';
import { motionTokens } from '@/lib/motion';
import { HeyAminLogo } from '@/components/brand/HeyAminLogo';
import { useTranslations } from 'next-intl';

type ConnectionStatus = 'checking' | 'online' | 'offline';

function isNetworkError(err: unknown): boolean {
  if (err instanceof TypeError && err.message.includes('fetch')) return true;
  if (err instanceof Error) {
    const msg = err.message.toLowerCase();
    return (
      msg.includes('failed to fetch') ||
      msg.includes('network') ||
      msg.includes('econnrefused') ||
      msg.includes('load failed')
    );
  }
  return false;
}

const errorMotion = {
  initial: { opacity: 0, y: -8, height: 0 },
  animate: { opacity: 1, y: 0, height: 'auto' },
  exit: { opacity: 0, y: -8, height: 0 },
  transition: { duration: 0.25, ease: motionTokens.ease },
};

function LoginSuspenseFallback() {
  const t = useTranslations('common');
  return (
    <div className="ha-login-page">
      <p style={{ color: '#9a9ba2', fontSize: '0.875rem' }}>{t('loading')}</p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginSuspenseFallback />}>
      <LoginPageInner />
    </Suspense>
  );
}

function LoginPageInner() {
  const t = useTranslations('common');
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, isLoading } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isConnectionError, setIsConnectionError] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('checking');

  const checkHealth = useCallback(async () => {
    try {
      const baseUrl = getClientApiBaseUrl();
      const resp = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });
      setConnectionStatus(resp.ok ? 'online' : 'offline');
    } catch {
      setConnectionStatus('offline');
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  useEffect(() => {
    if (searchParams.get('reason') === 'session_expired') {
      setSessionExpired(true);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push('/home');
    }
  }, [isAuthenticated, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsConnectionError(false);
    setLoading(true);
    try {
      await apiClient.login({ email, password });
      await login();
      router.push('/home');
    } catch (err) {
      if (isNetworkError(err)) {
        setIsConnectionError(true);
        setConnectionStatus('offline');
        setError(t('cannotReachServer'));
      } else {
        setIsConnectionError(false);
        setError(err instanceof Error ? err.message : t('authFailed'));
      }
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="ha-login-page">
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{ color: '#9a9ba2', fontSize: '0.875rem' }}
        >
          {t('loading')}
        </motion.p>
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
          <HeyAminLogo variant="mark" size={64} />
        </div>

        <h1 className="ha-login-title">{t('welcomeBack')}</h1>
        <p className="ha-login-sub">
          {t('signInTo')} <span className="ha-accent">{t('heyaminCloud')}</span>
        </p>

        {/* Connection status indicator */}
        <div className="ha-connection-status">
          <span
            className={`ha-connection-dot ha-connection-dot--${connectionStatus}`}
          />
          <span>
            {connectionStatus === 'checking'
              ? t('checkingServer')
              : connectionStatus === 'online'
                ? t('serverConnected')
                : t('serverUnavailable')}
          </span>
        </div>

        <AnimatePresence mode="wait">
          {sessionExpired && (
            <motion.p
              key="session-expired"
              className="ha-login-error"
              role="alert"
              style={{ marginBottom: '1rem' }}
              {...errorMotion}
            >
              Your session expired. Please sign in again.
            </motion.p>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="ha-form">
          <div className="ha-field">
            <label htmlFor="ha-email">{t('emailAddress')}</label>
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
            <label htmlFor="ha-password">{t('password')}</label>
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

          <AnimatePresence mode="wait">
            {error && (
              <motion.div
                key={isConnectionError ? 'conn-error' : 'auth-error'}
                {...errorMotion}
              >
                {isConnectionError ? (
                  <div className="ha-login-warning" role="alert">
                    <p style={{ margin: '0 0 0.375rem', fontWeight: 500 }}>
                      {error}
                    </p>
                    <p
                      style={{ margin: 0, fontSize: '0.75rem', opacity: 0.85 }}
                    >
                      Expected at <code>{getClientApiBaseUrl()}</code>
                    </p>
                  </div>
                ) : (
                  <p className="ha-login-error" role="alert">
                    {error}
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          <button type="submit" className="ha-btn-submit" disabled={loading}>
            {loading ? t('signingIn') : t('continue')}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '1.75rem' }}>
          <Link href="/" className="ha-login-footer-link">
            {t('backToHome')}
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
