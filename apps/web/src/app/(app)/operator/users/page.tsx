'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import { apiClient, OperatorUserRow } from '@/lib/apiClient';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

export default function OperatorUsersPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [rows, setRows] = useState<OperatorUserRow[]>([]);
  const [search, setSearch] = useState('');
  const [tenantFilter, setTenantFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newTenantId, setNewTenantId] = useState('');
  const [creating, setCreating] = useState(false);

  const isPlatformAdmin = user?.is_platform_admin === true;

  const load = useCallback(async () => {
    if (!isPlatformAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const list = await apiClient.operatorListUsers({
        search: search || undefined,
        tenant_id: tenantFilter || undefined,
      });
      setRows(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, [isPlatformAdmin, search, tenantFilter]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isPlatformAdmin) load();
  }, [isPlatformAdmin, load]);

  const toggleActive = async (u: OperatorUserRow) => {
    try {
      await apiClient.operatorPatchUser(u.id, { is_active: !u.is_active });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    }
  };

  const togglePlatform = async (u: OperatorUserRow) => {
    try {
      await apiClient.operatorPatchUser(u.id, {
        is_platform_admin: !(u.is_platform_admin === true),
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTenantId.trim()) {
      setError('Tenant ID required');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await apiClient.operatorCreateUser(newTenantId.trim(), {
        email: newEmail,
        password: newPassword,
      });
      setNewEmail('');
      setNewPassword('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    } finally {
      setCreating(false);
    }
  };

  if (authLoading || !isAuthenticated) {
    return <div className="page-container">Loading…</div>;
  }

  if (!isPlatformAdmin) {
    return (
      <div className="page-container">
        <p className="text-muted">Platform operator access required.</p>
        <Link href="/documents">Back to app</Link>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp} className="page-container">
      <div className="page-header">
        <h1 className="page-title">Users</h1>
        <p className="page-subtitle">
          Cross-organisation user directory (platform operator).
        </p>
      </div>

      {error && (
        <div className="alert alert-error mb-4" role="alert">
          {error}
        </div>
      )}

      <div className="card mb-4">
        <div className="card-header">
          <h2 className="card-title">Filters</h2>
        </div>
        <div
          className="card-body"
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '1rem',
            alignItems: 'flex-end',
          }}
        >
          <div
            className="form-group"
            style={{ marginBottom: 0, minWidth: '200px' }}
          >
            <label className="form-label">Search</label>
            <input
              className="form-input"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Email or name"
            />
          </div>
          <div
            className="form-group"
            style={{ marginBottom: 0, minWidth: '260px' }}
          >
            <label className="form-label">Tenant ID</label>
            <input
              className="form-input mono"
              value={tenantFilter}
              onChange={e => setTenantFilter(e.target.value)}
              placeholder="Optional filter"
            />
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => load()}
          >
            Apply
          </button>
        </div>
      </div>

      <div className="card mb-4">
        <div className="card-header">
          <h2 className="card-title">Create user in tenant</h2>
        </div>
        <form onSubmit={handleCreate} className="card-body">
          <div className="grid grid-3" style={{ gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Tenant ID</label>
              <input
                className="form-input mono"
                value={newTenantId}
                onChange={e => setNewTenantId(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input
                className="form-input"
                type="email"
                value={newEmail}
                onChange={e => setNewEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                className="form-input"
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-primary mt-4"
            disabled={creating}
          >
            {creating ? 'Creating…' : 'Create user'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Users</h2>
        </div>
        {loading ? (
          <p className="card-body text-muted">Loading…</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Tenant</th>
                  <th>Active</th>
                  <th>Platform admin</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <motion.tbody
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {rows.map(r => (
                  <motion.tr variants={staggerItem} key={r.id}>
                    <td>{r.email}</td>
                    <td className="mono" style={{ fontSize: '0.75rem' }}>
                      {r.tenant_id}
                    </td>
                    <td>{r.is_active ? 'Yes' : 'No'}</td>
                    <td>{r.is_platform_admin ? 'Yes' : 'No'}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        style={{ marginRight: '0.5rem' }}
                        onClick={() => toggleActive(r)}
                      >
                        Toggle active
                      </button>
                      <button
                        type="button"
                        className="btn btn-sm btn-secondary"
                        onClick={() => togglePlatform(r)}
                      >
                        Toggle platform admin
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </motion.tbody>
            </table>
          </div>
        )}
      </div>
    </motion.div>
  );
}
