'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/AuthContext';
import { apiClient, TenantCreateWithBootstrap } from '@/lib/apiClient';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

type TenantRow = {
  id: string;
  name: string;
  primary_jurisdiction: string;
  data_residency_policy: string;
  created_at: string;
};

export default function OperatorOrganisationsPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const [name, setName] = useState('');
  const [primaryJurisdiction, setPrimaryJurisdiction] = useState<
    'UAE' | 'KSA' | 'DIFC' | 'ADGM'
  >('UAE');
  const [dataResidency, setDataResidency] = useState<'UAE' | 'KSA' | 'GCC'>(
    'UAE'
  );
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [workspaceName, setWorkspaceName] = useState('Main');

  const isPlatformAdmin = user?.is_platform_admin === true;

  const load = useCallback(async () => {
    if (!isPlatformAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const list = await apiClient.operatorListTenants();
      setTenants(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load organisations');
    } finally {
      setLoading(false);
    }
  }, [isPlatformAdmin]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isPlatformAdmin) load();
  }, [isPlatformAdmin, load]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isPlatformAdmin) return;
    setCreating(true);
    setError(null);
    const payload: TenantCreateWithBootstrap = {
      name,
      primary_jurisdiction: primaryJurisdiction,
      data_residency_policy: dataResidency,
      bootstrap: {
        admin_user: {
          email: adminEmail,
          password: adminPassword,
        },
        workspace: {
          name: workspaceName,
          workspace_type: 'IN_HOUSE',
          jurisdiction_profile: 'UAE_DEFAULT',
          default_language: 'en',
        },
      },
    };
    try {
      await apiClient.operatorCreateTenant(payload);
      setName('');
      setAdminEmail('');
      setAdminPassword('');
      setWorkspaceName('Main');
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
        <h1 className="page-title">Organisations</h1>
        <p className="page-subtitle">
          Create and list organisations (platform operator).
        </p>
      </div>

      {error && (
        <div className="alert alert-error mb-4" role="alert">
          {error}
        </div>
      )}

      <div className="card mb-4">
        <div className="card-header">
          <h2 className="card-title">Create organisation</h2>
        </div>
        <form onSubmit={handleCreate} className="card-body">
          <div className="grid grid-2" style={{ gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Name</label>
              <input
                className="form-input"
                value={name}
                onChange={e => setName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Workspace</label>
              <input
                className="form-input"
                value={workspaceName}
                onChange={e => setWorkspaceName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Jurisdiction</label>
              <select
                className="form-select"
                value={primaryJurisdiction}
                onChange={e =>
                  setPrimaryJurisdiction(
                    e.target.value as typeof primaryJurisdiction
                  )
                }
              >
                <option value="UAE">UAE</option>
                <option value="KSA">KSA</option>
                <option value="DIFC">DIFC</option>
                <option value="ADGM">ADGM</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Data residency</label>
              <select
                className="form-select"
                value={dataResidency}
                onChange={e =>
                  setDataResidency(e.target.value as typeof dataResidency)
                }
              >
                <option value="UAE">UAE</option>
                <option value="KSA">KSA</option>
                <option value="GCC">GCC</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Admin email</label>
              <input
                className="form-input"
                type="email"
                value={adminEmail}
                onChange={e => setAdminEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label className="form-label">Admin password</label>
              <input
                className="form-input"
                type="password"
                value={adminPassword}
                onChange={e => setAdminPassword(e.target.value)}
                minLength={8}
                required
                autoComplete="new-password"
              />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-primary mt-4"
            disabled={creating}
          >
            {creating ? 'Creating…' : 'Create'}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">All organisations</h2>
        </div>
        {loading ? (
          <p className="card-body text-muted">Loading…</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>ID</th>
                  <th>Jurisdiction</th>
                  <th>Created</th>
                </tr>
              </thead>
              <motion.tbody
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {tenants.map(t => (
                  <motion.tr variants={staggerItem} key={t.id}>
                    <td>{t.name}</td>
                    <td className="mono" style={{ fontSize: '0.8rem' }}>
                      {t.id}
                    </td>
                    <td>{t.primary_jurisdiction}</td>
                    <td>{new Date(t.created_at).toLocaleString()}</td>
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
