'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient, MemberWithUser, type Organization } from '@/lib/apiClient';
import { useAuth } from '@/lib/AuthContext';
import { useNavigation } from '@/components/NavigationLoader';
import { motion, AnimatePresence } from 'framer-motion';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

export default function MembersPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const { navigateTo } = useNavigation();

  const [members, setMembers] = useState<MemberWithUser[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [showInviteForm, setShowInviteForm] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteFullName, setInviteFullName] = useState('');
  const [inviteRole, setInviteRole] = useState<'ADMIN' | 'EDITOR' | 'VIEWER'>(
    'VIEWER'
  );
  const [inviteInitialPassword, setInviteInitialPassword] = useState('');
  const [inviting, setInviting] = useState(false);

  const [showOrgForm, setShowOrgForm] = useState(false);
  const [orgName, setOrgName] = useState('');
  const [orgDescription, setOrgDescription] = useState('');
  const [creatingOrg, setCreatingOrg] = useState(false);

  const [expandedOrg, setExpandedOrg] = useState<string | null>(null);
  const [updatingRoleId, setUpdatingRoleId] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const isAdmin = user?.role === 'ADMIN';
  const workspaceId = user?.workspace_id;

  const fetchMembers = useCallback(async () => {
    if (!workspaceId) return;
    try {
      setLoading(true);
      setError(null);
      const membersList = await apiClient.listMembers(workspaceId);
      setMembers(membersList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load members');
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  const fetchOrganizations = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const orgs = await apiClient.listOrganizations(workspaceId);
      setOrganizations(orgs);
    } catch {
      // Organizations may not exist yet
    }
  }, [workspaceId]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated && workspaceId) {
      fetchMembers();
      fetchOrganizations();
    }
  }, [isAuthenticated, workspaceId, fetchMembers, fetchOrganizations]);

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || !inviteEmail) return;
    try {
      setInviting(true);
      setError(null);
      await apiClient.addMember(workspaceId, {
        email: inviteEmail,
        full_name: inviteFullName || undefined,
        role: inviteRole,
        initial_password: inviteInitialPassword || undefined,
      });
      setSuccess(`Successfully invited ${inviteEmail} as ${inviteRole}`);
      setInviteEmail('');
      setInviteFullName('');
      setInviteInitialPassword('');
      setInviteRole('VIEWER');
      setShowInviteForm(false);
      await fetchMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invite member');
    } finally {
      setInviting(false);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId || !orgName) return;
    try {
      setCreatingOrg(true);
      setError(null);
      await apiClient.createOrganization(workspaceId, {
        name: orgName,
        description: orgDescription || undefined,
      });
      setSuccess(`Organization "${orgName}" created`);
      setOrgName('');
      setOrgDescription('');
      setShowOrgForm(false);
      await fetchOrganizations();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create organization'
      );
    } finally {
      setCreatingOrg(false);
    }
  };

  const handleDeleteOrg = async (orgId: string, orgNameStr: string) => {
    if (!workspaceId) return;
    try {
      setError(null);
      await apiClient.deleteOrganization(workspaceId, orgId);
      setSuccess(`Organization "${orgNameStr}" deleted`);
      await fetchOrganizations();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to delete organization'
      );
    }
  };

  const handleRoleChange = async (
    membershipId: string,
    newRole: 'ADMIN' | 'EDITOR' | 'VIEWER'
  ) => {
    if (!workspaceId) return;
    try {
      setUpdatingRoleId(membershipId);
      setError(null);
      await apiClient.updateMemberRole(workspaceId, membershipId, newRole);
      setSuccess('Role updated successfully');
      await fetchMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role');
    } finally {
      setUpdatingRoleId(null);
    }
  };

  const handleRemove = async (membershipId: string, email: string) => {
    if (!workspaceId) return;
    try {
      setRemovingId(membershipId);
      setError(null);
      await apiClient.removeMember(workspaceId, membershipId);
      setSuccess(`Successfully removed ${email} from workspace`);
      await fetchMembers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove member');
    } finally {
      setRemovingId(null);
    }
  };

  const getRoleBadgeClass = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return 'badge badge-admin';
      case 'EDITOR':
        return 'badge badge-editor';
      default:
        return 'badge badge-viewer';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (authLoading) {
    return (
      <div className="loading">
        <span className="spinner" />
        <span style={{ marginLeft: 'var(--space-3)' }}>Loading...</span>
      </div>
    );
  }

  return (
    <motion.div {...fadeUp}>
      <div className="page-header">
        <div className="page-header-row">
          <div>
            <h1 className="page-title">Members & Organizations</h1>
            <p className="page-subtitle">
              Manage team access, organizations, and permissions
            </p>
          </div>
          {isAdmin && (
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className={`btn ${showOrgForm ? 'btn-outline' : 'btn-primary'}`}
                onClick={() => {
                  setShowOrgForm(!showOrgForm);
                  setShowInviteForm(false);
                }}
                style={{ fontSize: '0.8125rem' }}
              >
                {showOrgForm ? 'Cancel' : 'New Organization'}
              </button>
              <button
                className={`btn ${showInviteForm ? 'btn-outline' : 'btn-primary'}`}
                onClick={() => {
                  setShowInviteForm(!showInviteForm);
                  setShowOrgForm(false);
                }}
                style={{ fontSize: '0.8125rem' }}
              >
                {showInviteForm ? 'Cancel' : 'Add Member'}
              </button>
            </div>
          )}
        </div>
      </div>

      {success && <div className="alert alert-success mb-4">{success}</div>}
      {error && <div className="alert alert-error mb-4">{error}</div>}

      {/* Create Organization Form */}
      {showOrgForm && isAdmin && (
        <div className="card mb-4">
          <div className="card-header">
            <h3 className="card-title">Create Organization</h3>
          </div>
          <form onSubmit={handleCreateOrg}>
            <div className="grid grid-2" style={{ gap: '1rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="orgName" className="form-label">
                  Name <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  id="orgName"
                  type="text"
                  className="form-input"
                  value={orgName}
                  onChange={e => setOrgName(e.target.value)}
                  placeholder="Acme Legal LLC"
                  required
                  disabled={creatingOrg}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="orgDesc" className="form-label">
                  Description
                </label>
                <input
                  id="orgDesc"
                  type="text"
                  className="form-input"
                  value={orgDescription}
                  onChange={e => setOrgDescription(e.target.value)}
                  placeholder="Optional description"
                  disabled={creatingOrg}
                />
              </div>
            </div>
            <div style={{ marginTop: '1rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={creatingOrg || !orgName}
              >
                {creatingOrg ? 'Creating...' : 'Create Organization'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Invite Member Form */}
      {showInviteForm && isAdmin && (
        <div className="card mb-4">
          <div className="card-header">
            <h3 className="card-title">Invite New Member</h3>
          </div>
          <form onSubmit={handleInvite}>
            <div className="grid grid-3" style={{ gap: '1rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="inviteEmail" className="form-label">
                  Email <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input
                  id="inviteEmail"
                  type="email"
                  className="form-input"
                  value={inviteEmail}
                  onChange={e => setInviteEmail(e.target.value)}
                  placeholder="user@company.com"
                  required
                  disabled={inviting}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="inviteFullName" className="form-label">
                  Full Name
                </label>
                <input
                  id="inviteFullName"
                  type="text"
                  className="form-input"
                  value={inviteFullName}
                  onChange={e => setInviteFullName(e.target.value)}
                  placeholder="John Doe (optional)"
                  disabled={inviting}
                />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="inviteRole" className="form-label">
                  Role <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <select
                  id="inviteRole"
                  className="form-select"
                  value={inviteRole}
                  onChange={e =>
                    setInviteRole(
                      e.target.value as 'ADMIN' | 'EDITOR' | 'VIEWER'
                    )
                  }
                  disabled={inviting}
                >
                  <option value="VIEWER">Viewer</option>
                  <option value="EDITOR">Editor</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
            </div>
            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label htmlFor="inviteInitialPassword" className="form-label">
                Initial password (new users only)
              </label>
              <input
                id="inviteInitialPassword"
                type="password"
                className="form-input"
                style={{ maxWidth: '320px' }}
                value={inviteInitialPassword}
                onChange={e => setInviteInitialPassword(e.target.value)}
                placeholder="Min. 8 characters"
                minLength={8}
                disabled={inviting}
                autoComplete="new-password"
              />
            </div>
            <div style={{ marginTop: '1rem' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={inviting || !inviteEmail}
              >
                {inviting ? 'Adding...' : 'Add Member'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Organizations Section */}
      {organizations.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h2
            style={{
              fontSize: 16,
              fontWeight: 600,
              marginBottom: 12,
              color: 'var(--text-primary)',
            }}
          >
            Organizations
          </h2>
          <div style={{ display: 'grid', gap: 12 }}>
            {organizations.map(org => (
              <div
                key={org.id}
                className="card"
                style={{ padding: 0, overflow: 'hidden' }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    cursor: 'pointer',
                    background:
                      expandedOrg === org.id
                        ? 'rgba(255,255,255,0.02)'
                        : 'transparent',
                  }}
                  onClick={() =>
                    setExpandedOrg(expandedOrg === org.id ? null : org.id)
                  }
                >
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: 12 }}
                  >
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        background: 'rgba(212,160,23,0.1)',
                        border: '1px solid rgba(212,160,23,0.2)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 14,
                        fontWeight: 700,
                        color: 'rgba(212,160,23,0.9)',
                      }}
                    >
                      {org.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>
                        {org.name}
                      </div>
                      {org.description && (
                        <div
                          style={{
                            fontSize: 12,
                            color: 'var(--text-secondary)',
                            marginTop: 2,
                          }}
                        >
                          {org.description}
                        </div>
                      )}
                    </div>
                  </div>
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: 12 }}
                  >
                    <span
                      style={{ fontSize: 12, color: 'var(--text-secondary)' }}
                    >
                      {org.member_count} member
                      {org.member_count !== 1 ? 's' : ''}
                    </span>
                    {isAdmin && (
                      <button
                        className="btn btn-sm"
                        style={{
                          color: '#ef4444',
                          border: '1px solid #ef4444',
                          background: 'transparent',
                          fontSize: 11,
                        }}
                        onClick={e => {
                          e.stopPropagation();
                          handleDeleteOrg(org.id, org.name);
                        }}
                      >
                        Delete
                      </button>
                    )}
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      style={{
                        transform:
                          expandedOrg === org.id
                            ? 'rotate(180deg)'
                            : 'rotate(0)',
                        transition: 'transform 0.2s',
                        opacity: 0.5,
                      }}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                </div>
                <AnimatePresence>
                  {expandedOrg === org.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      style={{
                        overflow: 'hidden',
                        borderTop:
                          '1px solid var(--glass-border, rgba(255,255,255,0.07))',
                      }}
                    >
                      <div
                        style={{
                          padding: '12px 16px',
                          fontSize: 13,
                          color: 'var(--text-secondary)',
                        }}
                      >
                        <p style={{ marginBottom: 8 }}>
                          {org.master_user_id
                            ? `Master User: ${org.master_user_id}`
                            : 'No master user assigned'}
                        </p>
                        <p>
                          Members can be managed via the workspace member table
                          below.
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Members Table */}
      <h2
        style={{
          fontSize: 16,
          fontWeight: 600,
          marginBottom: 12,
          color: 'var(--text-primary)',
        }}
      >
        All Members
      </h2>

      {loading ? (
        <div className="loading">Loading members...</div>
      ) : members.length === 0 ? (
        <div className="card">
          <p
            className="text-muted"
            style={{ textAlign: 'center', padding: '2rem 0' }}
          >
            No members found in this workspace.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Joined</th>
                  {isAdmin && <th style={{ width: '180px' }}>Actions</th>}
                </tr>
              </thead>
              <motion.tbody
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
              >
                {members.map(member => {
                  const isSelf = member.user_id === user?.user_id;
                  const isUpdating = updatingRoleId === member.id;
                  const isRemoving = removingId === member.id;

                  return (
                    <motion.tr variants={staggerItem} key={member.id}>
                      <td>
                        <div>
                          <div className="font-medium">
                            {member.full_name || member.email || 'Unknown'}
                            {isSelf && (
                              <span
                                className="text-xs text-muted"
                                style={{ marginLeft: '0.5rem' }}
                              >
                                (you)
                              </span>
                            )}
                          </div>
                          {member.full_name && member.email && (
                            <div className="text-sm text-muted">
                              {member.email}
                            </div>
                          )}
                        </div>
                      </td>
                      <td>
                        {isAdmin && !isSelf ? (
                          <select
                            className="form-select"
                            value={member.role}
                            onChange={e =>
                              handleRoleChange(
                                member.id,
                                e.target.value as 'ADMIN' | 'EDITOR' | 'VIEWER'
                              )
                            }
                            disabled={isUpdating}
                            style={{
                              width: 'auto',
                              minWidth: '120px',
                              padding: 'var(--space-2) var(--space-3)',
                              fontSize: 'var(--text-sm)',
                            }}
                          >
                            <option value="VIEWER">Viewer</option>
                            <option value="EDITOR">Editor</option>
                            <option value="ADMIN">Admin</option>
                          </select>
                        ) : (
                          <span className={getRoleBadgeClass(member.role)}>
                            {member.role}
                          </span>
                        )}
                      </td>
                      <td>
                        {member.is_active ? (
                          <span className="badge badge-success">Active</span>
                        ) : (
                          <span className="badge badge-warning">Inactive</span>
                        )}
                      </td>
                      <td className="text-sm text-muted">
                        {formatDate(member.created_at)}
                      </td>
                      {isAdmin && (
                        <td>
                          <div
                            style={{
                              display: 'flex',
                              gap: 6,
                              alignItems: 'center',
                            }}
                          >
                            <button
                              className="btn btn-sm"
                              style={{
                                color: 'var(--amin-accent, #d4a017)',
                                border: '1px solid var(--amin-accent, #d4a017)',
                                background: 'transparent',
                                fontSize: '0.75rem',
                              }}
                              onClick={() =>
                                navigateTo(`/members/${member.user_id}`)
                              }
                            >
                              Soul
                            </button>
                            {!isSelf && (
                              <button
                                className="btn btn-sm"
                                style={{
                                  color: '#ef4444',
                                  border: '1px solid #ef4444',
                                  background: 'transparent',
                                  fontSize: '0.75rem',
                                }}
                                onClick={() =>
                                  handleRemove(
                                    member.id,
                                    member.email || 'this member'
                                  )
                                }
                                disabled={isRemoving}
                              >
                                {isRemoving ? '...' : 'Remove'}
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </motion.tr>
                  );
                })}
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
            {members.length} member{members.length !== 1 ? 's' : ''} in
            workspace
          </div>
        </div>
      )}

      {!isAdmin && (
        <div
          className="card mt-4"
          style={{
            background: 'rgba(59, 130, 246, 0.05)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
          }}
        >
          <p style={{ margin: 0, color: '#3b82f6' }}>
            <strong>Note:</strong> Only administrators can invite, modify, or
            remove members. Contact your workspace admin if you need to make
            changes.
          </p>
        </div>
      )}
    </motion.div>
  );
}
