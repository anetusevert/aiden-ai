"""Tests for multi-tenancy isolation and RBAC."""

import pytest
from httpx import AsyncClient


class TestTenantIsolation:
    """Tests for tenant isolation."""

    @pytest.mark.asyncio
    async def test_missing_tenant_header_returns_400(
        self,
        async_client: AsyncClient,
        tenant_factory,
        user_factory,
    ):
        """Endpoints requiring tenant header return 400 when missing."""
        tenant = await tenant_factory(name="Test Tenant")
        await user_factory(tenant, email="user@test.com")

        # Try to list workspaces without X-Tenant-Id header
        response = await async_client.get(f"/tenants/{tenant.id}/workspaces")
        assert response.status_code == 400
        assert "X-Tenant-Id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_invalid_uuid_header_returns_400(
        self,
        async_client: AsyncClient,
        tenant_factory,
    ):
        """Invalid UUID in header returns 400."""
        tenant = await tenant_factory(name="Test Tenant")

        response = await async_client.get(
            f"/tenants/{tenant.id}/workspaces",
            headers={"X-Tenant-Id": "not-a-valid-uuid"},
        )
        assert response.status_code == 400
        assert "Invalid UUID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_nonexistent_tenant_returns_404(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Non-existent tenant ID returns 404."""
        fake_tenant_id = "00000000-0000-0000-0000-000000000000"
        fake_user_id = "00000000-0000-0000-0000-000000000001"

        response = await async_client.get(
            f"/tenants/{fake_tenant_id}/workspaces",
            headers={
                "X-Tenant-Id": fake_tenant_id,
                "X-User-Id": fake_user_id,
            },
        )
        assert response.status_code == 404
        assert "Tenant not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_workspaces(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
    ):
        """Tenant A cannot access Tenant B's workspaces."""
        # Create two tenants
        tenant_a = await tenant_factory(name="Tenant A")
        tenant_b = await tenant_factory(name="Tenant B")

        # Create users in each tenant
        user_a = await user_factory(tenant_a, email="user_a@test.com")
        await user_factory(tenant_b, email="user_b@test.com")

        # Create workspace in Tenant B
        await workspace_factory(tenant_b, name="Tenant B Workspace")

        # Try to access Tenant B workspaces using Tenant A's header
        # but with Tenant B's path - should get 403 (mismatch)
        response = await async_client.get(
            f"/tenants/{tenant_b.id}/workspaces",
            headers={
                "X-Tenant-Id": tenant_a.id,
                "X-User-Id": user_a.id,
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_tenant_can_only_see_own_workspaces(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
    ):
        """Each tenant can only see their own workspaces."""
        # Create two tenants with workspaces
        tenant_a = await tenant_factory(name="Tenant A")
        tenant_b = await tenant_factory(name="Tenant B")

        user_a = await user_factory(tenant_a, email="user_a@test.com")
        user_b = await user_factory(tenant_b, email="user_b@test.com")

        await workspace_factory(tenant_a, name="Workspace A1")
        await workspace_factory(tenant_a, name="Workspace A2")
        await workspace_factory(tenant_b, name="Workspace B1")

        # Tenant A lists their workspaces
        response = await async_client.get(
            f"/tenants/{tenant_a.id}/workspaces",
            headers={
                "X-Tenant-Id": tenant_a.id,
                "X-User-Id": user_a.id,
            },
        )
        assert response.status_code == 200
        workspaces = response.json()
        assert len(workspaces) == 2
        workspace_names = {w["name"] for w in workspaces}
        assert workspace_names == {"Workspace A1", "Workspace A2"}

        # Tenant B lists their workspaces
        response = await async_client.get(
            f"/tenants/{tenant_b.id}/workspaces",
            headers={
                "X-Tenant-Id": tenant_b.id,
                "X-User-Id": user_b.id,
            },
        )
        assert response.status_code == 200
        workspaces = response.json()
        assert len(workspaces) == 1
        assert workspaces[0]["name"] == "Workspace B1"


class TestWorkspaceIsolation:
    """Tests for workspace isolation."""

    @pytest.mark.asyncio
    async def test_missing_workspace_header_returns_400(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Workspace-scoped endpoints require X-Workspace-Id header."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="user@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Try to list memberships without X-Workspace-Id header
        response = await async_client.get(
            f"/workspaces/{workspace.id}/memberships",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 400
        assert "X-Workspace-Id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_workspace_not_belonging_to_tenant_returns_403(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Workspace from different tenant returns 403."""
        # Create two tenants
        tenant_a = await tenant_factory(name="Tenant A")
        tenant_b = await tenant_factory(name="Tenant B")

        # Create user in tenant A
        user_a = await user_factory(tenant_a, email="user_a@example.com")

        # Create workspace in Tenant B
        workspace_b = await workspace_factory(tenant_b, name="Workspace B")

        # Create user and membership in tenant B
        user_b = await user_factory(tenant_b, email="user_b@example.com")
        await membership_factory(workspace_b, user_b, role="ADMIN")

        # Try to access Tenant B's workspace using Tenant A's header
        response = await async_client.get(
            f"/workspaces/{workspace_b.id}/memberships",
            headers={
                "X-Tenant-Id": tenant_a.id,
                "X-Workspace-Id": workspace_b.id,
                "X-User-Id": user_a.id,
            },
        )
        assert response.status_code == 403
        assert "does not belong to tenant" in response.json()["detail"]


class TestRBAC:
    """Tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_admin_can_create_membership(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """ADMIN role can create new memberships."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        admin_user = await user_factory(tenant, email="admin@example.com")
        new_user = await user_factory(tenant, email="newuser@example.com")

        # Give admin user ADMIN role
        await membership_factory(workspace, admin_user, role="ADMIN")

        # Admin creates membership for new user
        response = await async_client.post(
            f"/workspaces/{workspace.id}/memberships",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": admin_user.id,
            },
            json={"user_id": new_user.id, "role": "VIEWER"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == new_user.id
        assert data["role"] == "VIEWER"

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_membership(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """VIEWER role cannot create new memberships."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        viewer_user = await user_factory(tenant, email="viewer@example.com")
        new_user = await user_factory(tenant, email="newuser@example.com")

        # Give user VIEWER role
        await membership_factory(workspace, viewer_user, role="VIEWER")

        # Viewer tries to create membership
        response = await async_client.post(
            f"/workspaces/{workspace.id}/memberships",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": viewer_user.id,
            },
            json={"user_id": new_user.id, "role": "VIEWER"},
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_cannot_create_membership(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """EDITOR role cannot create new memberships."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        editor_user = await user_factory(tenant, email="editor@example.com")
        new_user = await user_factory(tenant, email="newuser@example.com")

        # Give user EDITOR role
        await membership_factory(workspace, editor_user, role="EDITOR")

        # Editor tries to create membership
        response = await async_client.post(
            f"/workspaces/{workspace.id}/memberships",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": editor_user.id,
            },
            json={"user_id": new_user.id, "role": "VIEWER"},
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_any_member_can_list_memberships(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Any workspace member can list memberships."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        viewer_user = await user_factory(tenant, email="viewer@example.com")
        admin_user = await user_factory(tenant, email="admin@example.com")

        await membership_factory(workspace, viewer_user, role="VIEWER")
        await membership_factory(workspace, admin_user, role="ADMIN")

        # Viewer can list memberships
        response = await async_client.get(
            f"/workspaces/{workspace.id}/memberships",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": viewer_user.id,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_non_member_cannot_list_memberships(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
    ):
        """Non-members cannot list workspace memberships."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        non_member = await user_factory(tenant, email="nonmember@example.com")

        # Non-member tries to list memberships
        response = await async_client.get(
            f"/workspaces/{workspace.id}/memberships",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": non_member.id,
            },
        )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


class TestTenantEndpoints:
    """Tests for tenant-level endpoints."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, async_client: AsyncClient, clean_db):
        """Create a new tenant."""
        response = await async_client.post(
            "/tenants",
            json={
                "name": "New Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_name"] == "New Tenant"
        assert "tenant_id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_workspace_requires_admin(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Creating workspace requires ADMIN role in an existing workspace."""
        tenant = await tenant_factory(name="Test Tenant")
        existing_workspace = await workspace_factory(tenant, name="Existing Workspace")
        admin_user = await user_factory(tenant, email="admin@example.com")
        await membership_factory(existing_workspace, admin_user, role="ADMIN")

        response = await async_client.post(
            f"/tenants/{tenant.id}/workspaces",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": existing_workspace.id,
                "X-User-Id": admin_user.id,
            },
            json={
                "name": "New Workspace",
                "workspace_type": "IN_HOUSE",
                "jurisdiction_profile": "UAE_DEFAULT",
                "default_language": "en",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Workspace"
        assert data["tenant_id"] == tenant.id

    @pytest.mark.asyncio
    async def test_create_user_requires_admin(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Creating user requires ADMIN role."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        admin_user = await user_factory(tenant, email="admin@example.com")
        await membership_factory(workspace, admin_user, role="ADMIN")

        response = await async_client.post(
            f"/tenants/{tenant.id}/users",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": admin_user.id,
            },
            json={
                "email": "newuser@example.com",
                "full_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["tenant_id"] == tenant.id

    @pytest.mark.asyncio
    async def test_duplicate_workspace_name_returns_409(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Duplicate workspace name in same tenant returns 409."""
        tenant = await tenant_factory(name="Test Tenant")
        existing_workspace = await workspace_factory(tenant, name="Duplicate Name")
        admin_user = await user_factory(tenant, email="admin@example.com")
        await membership_factory(existing_workspace, admin_user, role="ADMIN")

        response = await async_client.post(
            f"/tenants/{tenant.id}/workspaces",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": existing_workspace.id,
                "X-User-Id": admin_user.id,
            },
            json={
                "name": "Duplicate Name",
                "workspace_type": "IN_HOUSE",
                "jurisdiction_profile": "UAE_DEFAULT",
                "default_language": "en",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_duplicate_user_email_returns_409(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Duplicate user email in same tenant returns 409."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        admin_user = await user_factory(tenant, email="admin@example.com")
        await membership_factory(workspace, admin_user, role="ADMIN")
        await user_factory(tenant, email="existing@example.com")

        response = await async_client.post(
            f"/tenants/{tenant.id}/users",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": admin_user.id,
            },
            json={
                "email": "existing@example.com",
                "full_name": "Duplicate User",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestHealthEndpoint:
    """Tests for health endpoint (no auth required)."""

    @pytest.mark.asyncio
    async def test_health_no_headers_required(self, async_client: AsyncClient):
        """Health endpoint works without any headers."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
