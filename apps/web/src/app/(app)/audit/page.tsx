'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, AuditLogEntry } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { motion } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

export default function AuditPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();

  const [entries, setEntries] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [actionFilter, setActionFilter] = useState('');
  const [workspaceFilter, setWorkspaceFilter] = useState('');
  const [limit] = useState(50);

  const isAdmin = user?.role === 'ADMIN';

  const fetchAuditLogs = useCallback(async () => {
    if (!isAdmin) return;

    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getAuditLogs(
        limit,
        0,
        actionFilter || undefined,
        workspaceFilter || undefined
      );
      setEntries(response.items);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load audit logs'
      );
    } finally {
      setLoading(false);
    }
  }, [isAdmin, limit, actionFilter, workspaceFilter]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
      return;
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    // Pre-fill workspace filter with current workspace
    if (user?.workspace_id && !workspaceFilter) {
      setWorkspaceFilter(user.workspace_id);
    }
  }, [user, workspaceFilter]);

  useEffect(() => {
    if (isAuthenticated && isAdmin) {
      fetchAuditLogs();
    }
  }, [isAuthenticated, isAdmin, fetchAuditLogs]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, { bg: string; color: string }> = {
      success: { bg: 'rgba(34, 197, 94, 0.1)', color: '#22c55e' },
      failure: { bg: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' },
      pending: { bg: 'rgba(234, 179, 8, 0.1)', color: '#eab308' },
    };
    const style = colors[status] || colors.pending;

    return (
      <span
        style={{
          display: 'inline-block',
          padding: '0.25rem 0.5rem',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          background: style.bg,
          color: style.color,
        }}
      >
        {status}
      </span>
    );
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAuditLogs();
  };

  if (authLoading) {
    return <div className="loading">Loading...</div>;
  }

  // Admin-only gate
  if (!isAdmin) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Audit Log</h1>
          <p className="page-subtitle">System activity and access logs</p>
        </div>
        <div className="alert alert-warning" style={{ maxWidth: '500px' }}>
          <strong>Admin Only</strong>
          <p style={{ marginTop: '0.5rem', marginBottom: 0 }}>
            The audit log is only accessible to users with ADMIN role. Your
            current role is <strong>{user?.role || 'unknown'}</strong>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      <div className="page-header">
        <h1 className="page-title">Audit Log</h1>
        <p className="page-subtitle">System activity and access logs</p>
      </div>

      {/* Filters */}
      <div className="card mb-4">
        <form onSubmit={handleSearch}>
          <div className="grid grid-2" style={{ gap: '1rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="actionFilter" className="form-label">
                Action (contains)
              </label>
              <input
                id="actionFilter"
                type="text"
                className="form-input"
                value={actionFilter}
                onChange={e => setActionFilter(e.target.value)}
                placeholder="e.g., document.upload, auth.login"
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="workspaceFilter" className="form-label">
                Workspace ID
              </label>
              <input
                id="workspaceFilter"
                type="text"
                className="form-input"
                value={workspaceFilter}
                onChange={e => setWorkspaceFilter(e.target.value)}
                placeholder="Workspace UUID"
              />
            </div>
          </div>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => {
                setActionFilter('');
                setWorkspaceFilter(user?.workspace_id || '');
              }}
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      {error && <div className="alert alert-error mb-4">{error}</div>}

      {loading ? (
        <div className="loading">Loading audit logs...</div>
      ) : entries.length === 0 ? (
        <div className="card">
          <p
            className="text-muted"
            style={{ textAlign: 'center', padding: '2rem 0' }}
          >
            No audit log entries found matching your filters.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Resource</th>
                  <th>Request ID</th>
                </tr>
              </thead>
              <motion.tbody
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {entries.map(entry => (
                  <motion.tr variants={staggerItem} key={entry.id}>
                    <td className="text-sm" style={{ whiteSpace: 'nowrap' }}>
                      {formatTimestamp(entry.timestamp)}
                    </td>
                    <td>
                      <code
                        style={{
                          fontSize: '0.8125rem',
                          background: 'rgba(0,0,0,0.05)',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                        }}
                      >
                        {entry.action}
                      </code>
                    </td>
                    <td>{getStatusBadge(entry.status)}</td>
                    <td>
                      {entry.resource_type && (
                        <span>
                          <span className="badge badge-muted">
                            {entry.resource_type}
                          </span>
                          {entry.resource_id && (
                            <code
                              className="text-sm"
                              style={{
                                marginLeft: '0.5rem',
                                fontSize: '0.75rem',
                              }}
                            >
                              {entry.resource_id.slice(0, 8)}...
                            </code>
                          )}
                        </span>
                      )}
                      {!entry.resource_type && (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td>
                      {entry.request_id ? (
                        <code
                          style={{
                            fontSize: '0.75rem',
                            background: 'rgba(0,0,0,0.05)',
                            padding: '0.125rem 0.375rem',
                            borderRadius: '3px',
                          }}
                        >
                          {entry.request_id.slice(0, 8)}...
                        </code>
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                  </motion.tr>
                ))}
              </motion.tbody>
            </table>
          </div>
          <div
            style={{
              padding: '0.75rem 1rem',
              background: 'rgba(0,0,0,0.02)',
              borderTop: '1px solid var(--border)',
              fontSize: '0.875rem',
              color: 'var(--muted)',
            }}
          >
            Showing {entries.length} entries (limit: {limit})
          </div>
        </div>
      )}
    </motion.div>
  );
}
