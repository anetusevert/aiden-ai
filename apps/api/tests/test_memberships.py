"""Integration tests for workspace member management."""

import pytest
from httpx import AsyncClient

from tests.helpers import bootstrap_and_login


@pytest.mark.asyncio
async def test_admin_can_list_members(async_client: AsyncClient):
    """Admin can list workspace members."""
    # Bootstrap and login
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # List members
    response = await async_client.get(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
    )
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 1  # Bootstrap admin only
    assert members[0]["email"] == "admin@test.com"
    assert members[0]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_admin_can_invite_new_user(async_client: AsyncClient):
    """Admin can invite a new user by email (creates user if not exists)."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Invite new member
    response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={
            "email": "newuser@test.com",
            "full_name": "New User",
            "role": "EDITOR",
        },
    )
    assert response.status_code == 201
    member = response.json()
    assert member["email"] == "newuser@test.com"
    assert member["full_name"] == "New User"
    assert member["role"] == "EDITOR"

    # Verify member appears in list
    response = await async_client.get(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
    )
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2
    emails = [m["email"] for m in members]
    assert "admin@test.com" in emails
    assert "newuser@test.com" in emails


@pytest.mark.asyncio
async def test_admin_can_invite_existing_user(async_client: AsyncClient):
    """Admin can add an existing tenant user to workspace."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Create user in tenant first
    user_response = await async_client.post(
        f"/tenants/{data['tenant_id']}/users",
        headers=headers,
        json={"email": "existing@test.com", "full_name": "Existing User"},
    )
    assert user_response.status_code == 201

    # Invite existing user to workspace
    response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={
            "email": "existing@test.com",
            "role": "VIEWER",
        },
    )
    assert response.status_code == 201
    member = response.json()
    assert member["email"] == "existing@test.com"
    assert member["role"] == "VIEWER"


@pytest.mark.asyncio
async def test_invited_member_can_access_clients(async_client: AsyncClient):
    """Invited members should inherit org access in the default workspace."""
    data, token = await bootstrap_and_login(async_client)
    admin_headers = {"Authorization": f"Bearer {token}"}

    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=admin_headers,
        json={
            "email": "editor@test.com",
            "full_name": "Editor User",
            "role": "EDITOR",
        },
    )
    assert invite_response.status_code == 201

    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": "editor@test.com",
        },
    )
    assert login_response.status_code == 200
    editor_token = login_response.cookies.get("access_token")
    assert editor_token

    clients_response = await async_client.get(
        "/api/v1/clients",
        headers={"Authorization": f"Bearer {editor_token}"},
    )
    assert clients_response.status_code == 200
    payload = clients_response.json()
    assert payload["items"] == []
    assert payload["total"] == 0


@pytest.mark.asyncio
async def test_admin_can_update_member_role(async_client: AsyncClient):
    """Admin can change a member's role."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add a new member
    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "editor@test.com", "role": "EDITOR"},
    )
    assert invite_response.status_code == 201
    member_id = invite_response.json()["id"]

    # Update role from EDITOR to VIEWER
    response = await async_client.patch(
        f"/workspaces/{data['workspace_id']}/members/{member_id}",
        headers=headers,
        json={"role": "VIEWER"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["role"] == "VIEWER"


@pytest.mark.asyncio
async def test_admin_can_remove_member(async_client: AsyncClient):
    """Admin can remove a member from workspace."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add a new member
    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "toremove@test.com", "role": "VIEWER"},
    )
    assert invite_response.status_code == 201
    member_id = invite_response.json()["id"]

    # Remove member
    response = await async_client.delete(
        f"/workspaces/{data['workspace_id']}/members/{member_id}",
        headers=headers,
    )
    assert response.status_code == 204

    # Verify member is gone
    list_response = await async_client.get(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
    )
    members = list_response.json()
    assert len(members) == 1
    assert members[0]["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_non_admin_cannot_invite(async_client: AsyncClient):
    """Non-admin users cannot invite members."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add an editor
    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "editor@test.com", "role": "EDITOR"},
    )
    assert invite_response.status_code == 201

    # Login as editor
    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": "editor@test.com",
        },
    )
    assert login_response.status_code == 200
    editor_token = login_response.cookies.get("access_token")
    assert editor_token
    editor_headers = {"Authorization": f"Bearer {editor_token}"}

    # Editor tries to invite - should fail
    response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=editor_headers,
        json={"email": "another@test.com", "role": "VIEWER"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_update_role(async_client: AsyncClient):
    """Non-admin users cannot update member roles."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add an editor
    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "editor@test.com", "role": "EDITOR"},
    )
    editor_member_id = invite_response.json()["id"]

    # Login as editor
    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": "editor@test.com",
        },
    )
    editor_token = login_response.cookies.get("access_token")
    assert editor_token
    editor_headers = {"Authorization": f"Bearer {editor_token}"}

    # Editor tries to update their own role - should fail
    response = await async_client.patch(
        f"/workspaces/{data['workspace_id']}/members/{editor_member_id}",
        headers=editor_headers,
        json={"role": "ADMIN"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_remove_member(async_client: AsyncClient):
    """Non-admin users cannot remove members."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add editor and viewer
    await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "editor@test.com", "role": "EDITOR"},
    )
    viewer_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "viewer@test.com", "role": "VIEWER"},
    )
    viewer_member_id = viewer_response.json()["id"]

    # Login as editor
    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": "editor@test.com",
        },
    )
    editor_token = login_response.cookies.get("access_token")
    assert editor_token
    editor_headers = {"Authorization": f"Bearer {editor_token}"}

    # Editor tries to remove viewer - should fail
    response = await async_client.delete(
        f"/workspaces/{data['workspace_id']}/members/{viewer_member_id}",
        headers=editor_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_remove_last_admin(async_client: AsyncClient):
    """Cannot remove the last admin from workspace."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Get admin's membership ID
    list_response = await async_client.get(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
    )
    admin_member = list_response.json()[0]
    admin_member_id = admin_member["id"]

    # Try to remove self (last admin) - should fail
    response = await async_client.delete(
        f"/workspaces/{data['workspace_id']}/members/{admin_member_id}",
        headers=headers,
    )
    assert response.status_code == 400
    assert "last admin" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_demote_last_admin(async_client: AsyncClient):
    """Cannot demote the last admin to a lower role."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Get admin's membership ID
    list_response = await async_client.get(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
    )
    admin_member = list_response.json()[0]
    admin_member_id = admin_member["id"]

    # Try to demote self to EDITOR - should fail
    response = await async_client.patch(
        f"/workspaces/{data['workspace_id']}/members/{admin_member_id}",
        headers=headers,
        json={"role": "EDITOR"},
    )
    assert response.status_code == 400
    assert "last admin" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_can_remove_admin_if_not_last(async_client: AsyncClient):
    """Can remove an admin if another admin exists."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add another admin
    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "admin2@test.com", "role": "ADMIN"},
    )
    admin2_member_id = invite_response.json()["id"]

    # Can now remove the second admin
    response = await async_client.delete(
        f"/workspaces/{data['workspace_id']}/members/{admin2_member_id}",
        headers=headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_tenant_isolation_cannot_access_other_tenant(async_client: AsyncClient):
    """Cannot access memberships from another tenant's workspace."""
    # Bootstrap first tenant
    data1, token1 = await bootstrap_and_login(
        async_client, admin_email="admin1@tenant1.com", tenant_name="Tenant 1"
    )
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Bootstrap second tenant
    data2, token2 = await bootstrap_and_login(
        async_client, admin_email="admin2@tenant2.com", tenant_name="Tenant 2"
    )
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Tenant 1 tries to access Tenant 2's workspace members - should fail
    response = await async_client.get(
        f"/workspaces/{data2['workspace_id']}/members",
        headers=headers1,
    )
    # Should get 403 (workspace mismatch with token's workspace_id)
    assert response.status_code == 403

    # Tenant 2 tries to access Tenant 1's workspace members - should fail
    response = await async_client.get(
        f"/workspaces/{data1['workspace_id']}/members",
        headers=headers2,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_invite_fails(async_client: AsyncClient):
    """Cannot invite the same user twice."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # First invite - should succeed
    response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "dupe@test.com", "role": "VIEWER"},
    )
    assert response.status_code == 201

    # Second invite - should fail with 409
    response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "dupe@test.com", "role": "EDITOR"},
    )
    assert response.status_code == 409
    assert "already a member" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_audit_logs_created_for_member_operations(async_client: AsyncClient):
    """Audit logs are created for add/update/remove operations."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add member
    invite_response = await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "audited@test.com", "role": "VIEWER"},
    )
    member_id = invite_response.json()["id"]

    # Update role
    await async_client.patch(
        f"/workspaces/{data['workspace_id']}/members/{member_id}",
        headers=headers,
        json={"role": "EDITOR"},
    )

    # Remove member
    await async_client.delete(
        f"/workspaces/{data['workspace_id']}/members/{member_id}",
        headers=headers,
    )

    # Check audit logs
    audit_response = await async_client.get(
        "/audit",
        headers=headers,
    )
    assert audit_response.status_code == 200
    logs = audit_response.json()["items"]

    # Find our member operations
    actions = [log["action"] for log in logs]
    assert "workspace.member.add" in actions
    assert "workspace.member.role.update" in actions
    assert "workspace.member.remove" in actions


@pytest.mark.asyncio
async def test_viewer_can_list_members(async_client: AsyncClient):
    """Viewer role can list members (transparency)."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}

    # Add a viewer
    await async_client.post(
        f"/workspaces/{data['workspace_id']}/members",
        headers=headers,
        json={"email": "viewer@test.com", "role": "VIEWER"},
    )

    # Login as viewer
    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": "viewer@test.com",
        },
    )
    viewer_token = login_response.cookies.get("access_token")
    assert viewer_token
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # Viewer can list members
    response = await async_client.get(
        f"/workspaces/{data['workspace_id']}/members",
        headers=viewer_headers,
    )
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2


@pytest.mark.asyncio
async def test_membership_not_found_returns_404(async_client: AsyncClient):
    """Operations on non-existent membership return 404."""
    data, token = await bootstrap_and_login(async_client)
    headers = {"Authorization": f"Bearer {token}"}
    fake_id = "00000000-0000-0000-0000-000000000000"

    # Update non-existent
    response = await async_client.patch(
        f"/workspaces/{data['workspace_id']}/members/{fake_id}",
        headers=headers,
        json={"role": "EDITOR"},
    )
    assert response.status_code == 404

    # Delete non-existent
    response = await async_client.delete(
        f"/workspaces/{data['workspace_id']}/members/{fake_id}",
        headers=headers,
    )
    assert response.status_code == 404
