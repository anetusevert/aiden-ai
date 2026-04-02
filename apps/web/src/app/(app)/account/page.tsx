'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/AuthContext';
import { UserAvatar } from '@/components/UserAvatar';
import { motion } from 'framer-motion';
import { fadeUp } from '@/lib/motion';

function getRoleBadgeClass(role: string) {
  switch (role) {
    case 'ADMIN':
      return 'account-menu-role account-menu-role-admin';
    case 'EDITOR':
      return 'account-menu-role account-menu-role-editor';
    default:
      return 'account-menu-role account-menu-role-viewer';
  }
}

export default function AccountPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout, logoutAll } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return <div className="loading">Loading...</div>;
  }

  if (!user) {
    return null;
  }

  return (
    <motion.div {...fadeUp}>
      <div className="page-header">
        <h1 className="page-title">Account</h1>
        <p className="page-subtitle">Manage your profile and preferences</p>
      </div>

      <div style={{ maxWidth: '640px' }}>
        {/* Profile hero */}
        <div className="card mb-4">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-5)',
              padding: 'var(--space-6)',
            }}
          >
            <div style={{ position: 'relative' }}>
              <UserAvatar user={user} size="xl" />
              <button
                className="btn btn-ghost btn-sm"
                style={{
                  position: 'absolute',
                  bottom: -4,
                  right: -4,
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--glass-border)',
                }}
                title="Upload photo (coming soon)"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                  <circle cx="12" cy="13" r="4" />
                </svg>
              </button>
            </div>
            <div>
              <h2
                style={{
                  fontSize: 'var(--text-2xl)',
                  fontWeight: 'var(--font-semibold)',
                  color: 'var(--text-primary)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                {user.full_name || 'User'}
              </h2>
              <div
                style={{
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-muted)',
                  marginBottom: 'var(--space-2)',
                }}
              >
                {user.email}
              </div>
              <span className={getRoleBadgeClass(user.role)}>{user.role}</span>
            </div>
          </div>
        </div>

        {/* Profile information */}
        <div className="card mb-4">
          <div className="card-header">
            <h3 className="card-title">Profile Information</h3>
          </div>

          <div className="form-group">
            <label className="form-label">Full Name</label>
            <p style={{ color: 'var(--text-primary)' }}>
              {user.full_name || 'Not set'}
            </p>
          </div>

          <div className="form-group">
            <label className="form-label">Email</label>
            <p style={{ color: 'var(--text-primary)' }}>
              {user.email || 'N/A'}
            </p>
          </div>

          <div className="form-group">
            <label className="form-label">Role</label>
            <span className="badge badge-info">{user.role}</span>
          </div>

          <div className="form-group">
            <label className="form-label">User ID</label>
            <code className="mono" style={{ fontSize: 'var(--text-xs)' }}>
              {user.user_id}
            </code>
          </div>
        </div>

        {/* Permissions */}
        <div className="card mb-4">
          <div className="card-header">
            <h3 className="card-title">Permissions</h3>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 'var(--space-4)',
              padding: 'var(--space-4) var(--space-5)',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-muted)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                View
              </div>
              <span className="badge badge-success">Yes</span>
            </div>
            <div>
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-muted)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                Edit
              </div>
              <span
                className={`badge ${user.role === 'ADMIN' || user.role === 'EDITOR' ? 'badge-success' : 'badge-error'}`}
              >
                {user.role === 'ADMIN' || user.role === 'EDITOR' ? 'Yes' : 'No'}
              </span>
            </div>
            <div>
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-muted)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                Manage
              </div>
              <span
                className={`badge ${user.role === 'ADMIN' ? 'badge-success' : 'badge-error'}`}
              >
                {user.role === 'ADMIN' ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </div>

        {/* Security */}
        <div className="card mb-4">
          <div className="card-header">
            <h3 className="card-title">Security</h3>
          </div>

          <div className="form-group">
            <label className="form-label">Authentication</label>
            <span className="badge badge-success">
              Secure Cookie (httpOnly)
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              gap: 'var(--space-3)',
              padding: '0 var(--space-5) var(--space-5)',
            }}
          >
            <button
              onClick={logout}
              className="btn btn-outline"
              style={{ flex: 1 }}
            >
              Sign Out
            </button>
            <button
              onClick={logoutAll}
              className="btn btn-outline"
              style={{ flex: 1 }}
              title="Sign out from all devices"
            >
              Sign Out Everywhere
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
