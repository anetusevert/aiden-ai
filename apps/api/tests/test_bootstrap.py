"""Tests for bootstrap flow and privilege escalation prevention."""

import pytest
from httpx import AsyncClient

from tests.helpers import bootstrap_and_login


class TestBootstrap:
    """Tests for tenant bootstrap functionality."""

    @pytest.mark.asyncio
    async def test_bootstrap_creates_all_entities(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Bootstrap creates tenant + workspace + user + admin membership."""
        response = await async_client.post(
            "/tenants",
            json={
                "name": "Bootstrapped Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {
                        "email": "admin@bootstrapped.com",
                        "full_name": "Admin User",
                        "password": "Testpass123",
                    },
                    "workspace": {
                        "name": "Main Workspace",
                        "workspace_type": "IN_HOUSE",
                        "jurisdiction_profile": "UAE_DEFAULT",
                        "default_language": "en",
                    },
                },
            },
        )
        assert response.status_code == 201
        data = response.json()

        # Verify all entities were created
        assert data["tenant_id"] is not None
        assert data["tenant_name"] == "Bootstrapped Tenant"
        assert data["workspace_id"] is not None
        assert data["workspace_name"] == "Main Workspace"
        assert data["admin_user_id"] is not None
        assert data["admin_user_email"] == "admin@bootstrapped.com"
        assert data["created_at"] is not None

    @pytest.mark.asyncio
    async def test_bootstrap_allows_subsequent_operations(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """After bootstrap, can use returned IDs for subsequent operations."""
        # Bootstrap tenant
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Operational Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {
                        "email": "admin@operational.com",
                        "full_name": "Admin",
                        "password": "Testpass123",
                    },
                    "workspace": {
                        "name": "Operations",
                        "workspace_type": "IN_HOUSE",
                        "jurisdiction_profile": "UAE_DEFAULT",
                        "default_language": "en",
                    },
                },
            },
        )
        assert bootstrap_response.status_code == 201
        bootstrap_data = bootstrap_response.json()

        tenant_id = bootstrap_data["tenant_id"]
        workspace_id = bootstrap_data["workspace_id"]
        admin_user_id = bootstrap_data["admin_user_id"]

        # List workspaces using bootstrap headers
        list_response = await async_client.get(
            f"/tenants/{tenant_id}/workspaces",
            headers={
                "X-Tenant-Id": tenant_id,
                "X-User-Id": admin_user_id,
            },
        )
        assert list_response.status_code == 200
        workspaces = list_response.json()
        assert len(workspaces) == 1
        assert workspaces[0]["name"] == "Operations"

        # List memberships using bootstrap headers
        membership_response = await async_client.get(
            f"/workspaces/{workspace_id}/memberships",
            headers={
                "X-Tenant-Id": tenant_id,
                "X-Workspace-Id": workspace_id,
                "X-User-Id": admin_user_id,
            },
        )
        assert membership_response.status_code == 200
        memberships = membership_response.json()
        assert len(memberships) == 1
        assert memberships[0]["role"] == "ADMIN"
        assert memberships[0]["user_id"] == admin_user_id

    @pytest.mark.asyncio
    async def test_bootstrap_admin_can_create_new_user(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Bootstrapped admin can create new users."""
        # Bootstrap tenant
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "User Creation Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@usercreation.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        assert bootstrap_response.status_code == 201
        data = bootstrap_response.json()

        # Create new user
        create_user_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={
                "email": "newuser@usercreation.com",
                "full_name": "New User",
            },
        )
        assert create_user_response.status_code == 201
        new_user = create_user_response.json()
        assert new_user["email"] == "newuser@usercreation.com"

    @pytest.mark.asyncio
    async def test_bootstrap_admin_can_create_new_workspace(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Bootstrapped admin can create new workspaces."""
        # Bootstrap tenant
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Workspace Creation Tenant",
                "primary_jurisdiction": "DIFC",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@workspacecreation.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        assert bootstrap_response.status_code == 201
        data = bootstrap_response.json()

        # Create new workspace
        create_ws_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/workspaces",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={
                "name": "Second Workspace",
                "workspace_type": "LAW_FIRM",
                "jurisdiction_profile": "DIFC_DEFAULT",
                "default_language": "en",
            },
        )
        assert create_ws_response.status_code == 201
        new_ws = create_ws_response.json()
        assert new_ws["name"] == "Second Workspace"

    @pytest.mark.asyncio
    async def test_tenant_creation_without_bootstrap(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Tenant can be created without bootstrap payload."""
        response = await async_client.post(
            "/tenants",
            json={
                "name": "Simple Tenant",
                "primary_jurisdiction": "KSA",
                "data_residency_policy": "KSA",
            },
        )
        assert response.status_code == 201
        data = response.json()

        assert data["tenant_id"] is not None
        assert data["tenant_name"] == "Simple Tenant"
        # No bootstrap entities created
        assert data["workspace_id"] is None
        assert data["admin_user_id"] is None

    @pytest.mark.asyncio
    async def test_bootstrap_admin_can_access_clients_api(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Bootstrap should provision enough org access for client routes."""
        data, token = await bootstrap_and_login(async_client)
        response = await async_client.get(
            "/api/v1/clients",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"] == []
        assert payload["total"] == 0

    @pytest.mark.asyncio
    async def test_clients_api_self_heals_missing_org_membership(
        self,
        async_client: AsyncClient,
        clean_db,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Legacy workspace-only users should regain access through auto-heal."""
        tenant = await tenant_factory(name="Legacy Tenant")
        workspace = await workspace_factory(tenant, name="Legacy Workspace")
        user = await user_factory(tenant, email="legacy-admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": tenant.id,
                "workspace_id": workspace.id,
                "email": user.email,
            },
        )
        assert login_response.status_code == 200
        token = login_response.cookies.get("access_token")
        assert token

        response = await async_client.get(
            "/api/v1/clients",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["items"] == []
        assert payload["total"] == 0


class TestPrivilegeEscalation:
    """Tests for privilege escalation prevention."""

    @pytest.mark.asyncio
    async def test_user_from_tenant_a_cannot_use_tenant_b_header(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """User from Tenant A cannot use Tenant B's X-Tenant-Id header."""
        # Create two tenants with bootstrap
        response_a = await async_client.post(
            "/tenants",
            json={
                "name": "Tenant A",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@tenanta.com"},
                    "workspace": {"name": "WS A"},
                },
            },
        )
        assert response_a.status_code == 201
        tenant_a = response_a.json()

        response_b = await async_client.post(
            "/tenants",
            json={
                "name": "Tenant B",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@tenantb.com"},
                    "workspace": {"name": "WS B"},
                },
            },
        )
        assert response_b.status_code == 201
        tenant_b = response_b.json()

        # Try to use Tenant A's user with Tenant B's header
        response = await async_client.get(
            f"/tenants/{tenant_b['tenant_id']}/workspaces",
            headers={
                "X-Tenant-Id": tenant_b["tenant_id"],
                "X-User-Id": tenant_a["admin_user_id"],  # User from Tenant A!
            },
        )
        assert response.status_code == 403
        assert "does not belong to tenant" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_user_cannot_access_workspace_they_are_not_member_of(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """User cannot access workspace they're not a member of."""
        # Bootstrap tenant with admin
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Multi-WS Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@multiws.com"},
                    "workspace": {"name": "WS 1"},
                },
            },
        )
        assert bootstrap_response.status_code == 201
        data = bootstrap_response.json()

        # Create second user (not a member of any workspace yet)
        create_user_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={"email": "nonmember@multiws.com"},
        )
        assert create_user_response.status_code == 201
        non_member = create_user_response.json()

        # Non-member tries to access workspace memberships
        response = await async_client.get(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": non_member["id"],  # User not in workspace
            },
        )
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_inactive_user_cannot_access(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        clean_db,
    ):
        """Inactive user cannot access any endpoints."""
        tenant = await tenant_factory(name="Inactive User Tenant")
        workspace = await workspace_factory(tenant, name="Test WS")
        user = await user_factory(tenant, email="inactive@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Deactivate user directly in DB
        user.is_active = False
        await clean_db.commit()

        # Inactive user tries to access
        response = await async_client.get(
            f"/tenants/{tenant.id}/workspaces",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_cross_tenant_workspace_access_blocked(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Cannot access workspace from different tenant."""
        # Create two tenants
        response_a = await async_client.post(
            "/tenants",
            json={
                "name": "Tenant A",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@a.com"},
                    "workspace": {"name": "WS A"},
                },
            },
        )
        tenant_a = response_a.json()

        response_b = await async_client.post(
            "/tenants",
            json={
                "name": "Tenant B",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@b.com"},
                    "workspace": {"name": "WS B"},
                },
            },
        )
        tenant_b = response_b.json()

        # Try to access Tenant B's workspace using Tenant A's header
        response = await async_client.get(
            f"/workspaces/{tenant_b['workspace_id']}/memberships",
            headers={
                "X-Tenant-Id": tenant_a["tenant_id"],  # Wrong tenant!
                "X-Workspace-Id": tenant_b["workspace_id"],
                "X-User-Id": tenant_a["admin_user_id"],
            },
        )
        # Should fail - workspace doesn't belong to Tenant A
        assert response.status_code == 403


class TestMissingHeaders:
    """Tests for missing header validation."""

    @pytest.mark.asyncio
    async def test_missing_tenant_header_returns_400(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Missing X-Tenant-Id header returns 400."""
        response = await async_client.get(
            "/tenants/00000000-0000-0000-0000-000000000000/workspaces"
        )
        assert response.status_code == 400
        assert "X-Tenant-Id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_user_header_returns_400(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Missing X-User-Id header returns 400 for protected endpoints."""
        # Bootstrap a tenant first
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Header Test Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@headertest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap_response.json()

        # Try to list workspaces without X-User-Id
        response = await async_client.get(
            f"/tenants/{data['tenant_id']}/workspaces",
            headers={"X-Tenant-Id": data["tenant_id"]},
            # Missing X-User-Id!
        )
        assert response.status_code == 400
        assert "X-User-Id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_missing_workspace_header_returns_400(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Missing X-Workspace-Id header returns 400 for workspace endpoints."""
        # Bootstrap a tenant
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "WS Header Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@wsheader.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap_response.json()

        # Try to list memberships without X-Workspace-Id
        response = await async_client.get(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-User-Id": data["admin_user_id"],
                # Missing X-Workspace-Id!
            },
        )
        assert response.status_code == 400
        assert "X-Workspace-Id" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_tenant_creation_no_headers_required(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """POST /tenants does not require any headers."""
        response = await async_client.post(
            "/tenants",
            json={
                "name": "No Headers Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
            },
        )
        assert response.status_code == 201


class TestRBACWithBootstrap:
    """Tests for RBAC using bootstrapped tenants."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_user(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """VIEWER role cannot create users."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "RBAC Test Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@rbac.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Create a viewer user
        viewer_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={"email": "viewer@rbac.com"},
        )
        viewer = viewer_response.json()

        # Add viewer to workspace with VIEWER role
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={"user_id": viewer["id"], "role": "VIEWER"},
        )

        # Viewer tries to create a user
        response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": viewer["id"],  # Viewer trying to create user
            },
            json={"email": "shouldfail@rbac.com"},
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_cannot_add_membership(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """EDITOR role cannot add workspace memberships."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Editor RBAC Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@editorbac.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Create an editor user
        editor_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={"email": "editor@editorbac.com"},
        )
        editor = editor_response.json()

        # Add editor to workspace with EDITOR role
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={"user_id": editor["id"], "role": "EDITOR"},
        )

        # Create another user to try to add
        another_user = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": data["admin_user_id"],
            },
            json={"email": "another@editorbac.com"},
        )
        another = another_user.json()

        # Editor tries to add another user
        response = await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={
                "X-Tenant-Id": data["tenant_id"],
                "X-Workspace-Id": data["workspace_id"],
                "X-User-Id": editor["id"],  # Editor trying to add
            },
            json={"user_id": another["id"], "role": "VIEWER"},
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]
