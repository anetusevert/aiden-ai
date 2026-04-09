"""Tests for JWT authentication system.

Test Categories:
- Unit tests (TestJWTUtils): No database required, can run standalone
- Integration tests (all others): Require PostgreSQL running

Run unit tests only:
    uv run pytest tests/test_auth.py::TestJWTUtils -v

Run integration tests only:
    uv run pytest -m integration tests/test_auth.py -v
"""

import pytest
from httpx import AsyncClient
from src.config import settings
from src.utils.jwt import create_access_token, decode_access_token


@pytest.mark.integration
class TestDevLogin:
    """Tests for /auth/dev-login endpoint."""

    @pytest.mark.asyncio
    async def test_dev_login_success_returns_cookies(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Dev login with valid credentials sets cookies and returns user info."""
        # Bootstrap tenant first
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Auth Test Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@authtest.com", "full_name": "Admin"},
                    "workspace": {"name": "Main Workspace"},
                },
            },
        )
        assert bootstrap_response.status_code == 201
        data = bootstrap_response.json()

        # Dev login with the created user
        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@authtest.com",
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()

        # Cookie-based auth response
        assert login_data["auth_mode"] == "cookie"
        assert login_data["user_id"] == data["admin_user_id"]
        assert login_data["email"] == "admin@authtest.com"
        assert login_data["role"] == "ADMIN"
        assert "expires_in" in login_data

        # Check cookies are set
        cookies = login_response.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

        # Verify access token cookie contains correct claims
        payload = decode_access_token(cookies["access_token"])
        assert payload.sub == data["admin_user_id"]
        assert payload.tenant_id == data["tenant_id"]
        assert payload.workspace_id == data["workspace_id"]
        assert payload.role == "ADMIN"
        assert payload.email == "admin@authtest.com"
        assert payload.token_type == "access"

    @pytest.mark.asyncio
    async def test_dev_login_fails_user_not_in_tenant(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Dev login fails if user email doesn't exist in tenant."""
        # Bootstrap tenant
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Tenant A",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@tenanta.com"},
                    "workspace": {"name": "Workspace A"},
                },
            },
        )
        data = bootstrap_response.json()

        # Try to login with non-existent email
        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "nonexistent@tenanta.com",
            },
        )
        assert login_response.status_code == 401
        assert "user not found" in login_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_dev_login_fails_user_not_member_of_workspace(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Dev login fails if user is not a member of the workspace."""
        # Bootstrap tenant with admin
        bootstrap_response = await async_client.post(
            "/tenants",
            json={
                "name": "Multi WS Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@multiws.com"},
                    "workspace": {"name": "Workspace 1"},
                },
            },
        )
        data = bootstrap_response.json()

        # Create second user (not added to workspace)
        headers = {
            "X-Tenant-Id": data["tenant_id"],
            "X-Workspace-Id": data["workspace_id"],
            "X-User-Id": data["admin_user_id"],
        }
        # Temporarily switch to headers mode for user creation
        original_mode = settings.auth_mode
        settings.auth_mode = "headers"

        try:
            user_response = await async_client.post(
                f"/tenants/{data['tenant_id']}/users",
                headers=headers,
                json={"email": "nonmember@multiws.com"},
            )
            assert user_response.status_code == 201
        finally:
            settings.auth_mode = original_mode

        # Try to login as the non-member user
        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "nonmember@multiws.com",
            },
        )
        assert login_response.status_code == 401
        assert "not a member" in login_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_dev_login_fails_user_inactive(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        clean_db,
    ):
        """Dev login fails if user is inactive."""
        tenant = await tenant_factory(name="Inactive Test Tenant")
        workspace = await workspace_factory(tenant, name="Test WS")
        user = await user_factory(tenant, email="inactive@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Deactivate user
        user.is_active = False
        await clean_db.commit()

        # Try to login as inactive user
        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": tenant.id,
                "workspace_id": workspace.id,
                "email": "inactive@test.com",
            },
        )
        assert login_response.status_code == 401
        assert "inactive" in login_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_dev_login_fails_invalid_tenant(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Dev login fails if tenant doesn't exist."""
        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": "00000000-0000-0000-0000-000000000000",
                "workspace_id": "00000000-0000-0000-0000-000000000001",
                "email": "test@test.com",
            },
        )
        assert login_response.status_code == 401
        assert "tenant not found" in login_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_dev_login_fails_workspace_wrong_tenant(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Dev login fails if workspace doesn't belong to tenant."""
        # Create two tenants
        tenant_a = await async_client.post(
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
        data_a = tenant_a.json()

        tenant_b = await async_client.post(
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
        data_b = tenant_b.json()

        # Try to login with Tenant A but Workspace B
        login_response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data_a["tenant_id"],
                "workspace_id": data_b["workspace_id"],  # Wrong workspace!
                "email": "admin@a.com",
            },
        )
        assert login_response.status_code == 401
        assert "workspace" in login_response.json()["detail"].lower()


@pytest.mark.integration
class TestAuthMe:
    """Tests for /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_auth_me_returns_user_info(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """GET /auth/me returns current user info from cookie."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Me Test Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {
                        "email": "admin@metest.com",
                        "full_name": "Test Admin",
                        "password": "Testpass123",
                    },
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@metest.com",
            },
        )
        cookies = login.cookies

        # Call /auth/me with cookie
        me_response = await async_client.get(
            "/auth/me",
            cookies={"access_token": cookies["access_token"]},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()

        assert me_data["user_id"] == data["admin_user_id"]
        assert me_data["tenant_id"] == data["tenant_id"]
        assert me_data["workspace_id"] == data["workspace_id"]
        assert me_data["role"] == "ADMIN"
        assert me_data["email"] == "admin@metest.com"
        assert me_data["full_name"] == "Test Admin"
        assert me_data["avatar_url"] is None
        assert me_data["auth_mode"] == "cookie"

    @pytest.mark.asyncio
    async def test_auth_avatar_update_persists(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """PUT /auth/me/avatar persists avatar data for the current user."""
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Avatar Test Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {
                        "email": "admin@avatartest.com",
                        "full_name": "Avatar Admin",
                        "password": "Testpass123",
                    },
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@avatartest.com",
            },
        )
        cookies = {"access_token": login.cookies["access_token"]}
        avatar_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"

        update_response = await async_client.put(
            "/auth/me/avatar",
            cookies=cookies,
            json={"avatar_url": avatar_url},
        )
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["avatar_url"] == avatar_url

        me_response = await async_client.get("/auth/me", cookies=cookies)
        assert me_response.status_code == 200
        assert me_response.json()["avatar_url"] == avatar_url

    @pytest.mark.asyncio
    async def test_auth_me_requires_token(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """GET /auth/me without token returns 401."""
        response = await async_client.get("/auth/me")
        assert response.status_code == 401
        error = response.json()
        assert error["detail"]["error_code"] == "authentication_required"


@pytest.mark.integration
class TestJWTProtectedEndpoints:
    """Tests for JWT-protected endpoints."""

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_token_in_jwt_mode(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Protected endpoints require Bearer token in JWT mode."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Protected Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@protected.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Try to access protected endpoint without token
        response = await async_client.get(
            f"/tenants/{data['tenant_id']}/workspaces",
            # No Authorization header!
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_works_with_valid_cookie(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Protected endpoints work with valid access_token cookie."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Token Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@tokentest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@tokentest.com",
            },
        )
        cookies = login.cookies

        # Access protected endpoint with cookie
        response = await async_client.get(
            f"/workspaces/{data['workspace_id']}/memberships",
            cookies={"access_token": cookies["access_token"]},
        )
        assert response.status_code == 200
        memberships = response.json()
        assert len(memberships) == 1
        assert memberships[0]["role"] == "ADMIN"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Invalid token returns 401 Unauthorized."""
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestRoleEnforcementWithJWT:
    """Tests for role-based access control with JWT."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_user_with_cookie(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """VIEWER role cannot create users (cookie auth)."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "RBAC JWT Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@rbacjwt.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Get admin cookies
        admin_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@rbacjwt.com",
            },
        )
        admin_cookies = {"access_token": admin_login.cookies["access_token"]}

        # Create a viewer user (using admin)
        viewer_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            cookies=admin_cookies,
            json={"email": "viewer@rbacjwt.com"},
        )
        viewer = viewer_response.json()

        # Add viewer to workspace with VIEWER role (using admin)
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            cookies=admin_cookies,
            json={"user_id": viewer["id"], "role": "VIEWER"},
        )

        # Get viewer cookies
        viewer_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "viewer@rbacjwt.com",
            },
        )
        viewer_cookies = {"access_token": viewer_login.cookies["access_token"]}

        # Viewer tries to create a user
        create_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            cookies=viewer_cookies,
            json={"email": "shouldfail@rbacjwt.com"},
        )
        assert create_response.status_code == 403
        assert "ADMIN" in create_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_can_view_memberships_with_cookie(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """EDITOR role can view memberships (cookie auth)."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Editor JWT Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@editorjwt.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Get admin cookies
        admin_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@editorjwt.com",
            },
        )
        admin_cookies = {"access_token": admin_login.cookies["access_token"]}

        # Create an editor user
        editor_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            cookies=admin_cookies,
            json={"email": "editor@editorjwt.com"},
        )
        editor = editor_response.json()

        # Add editor to workspace
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            cookies=admin_cookies,
            json={"user_id": editor["id"], "role": "EDITOR"},
        )

        # Get editor cookies
        editor_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "editor@editorjwt.com",
            },
        )
        editor_cookies = {"access_token": editor_login.cookies["access_token"]}

        # Editor can view memberships
        response = await async_client.get(
            f"/workspaces/{data['workspace_id']}/memberships",
            cookies=editor_cookies,
        )
        assert response.status_code == 200
        assert len(response.json()) == 2  # Admin + Editor


@pytest.mark.integration
class TestHeaderModeCompatibility:
    """Tests for backward-compatible header auth mode."""

    @pytest.mark.asyncio
    async def test_header_mode_works_when_enabled(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Header auth mode works when AUTH_MODE=headers."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Header Mode Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@headermode.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Switch to headers mode temporarily
        original_mode = settings.auth_mode
        settings.auth_mode = "headers"

        try:
            # Access protected endpoint with headers (no token)
            response = await async_client.get(
                f"/workspaces/{data['workspace_id']}/memberships",
                headers={
                    "X-Tenant-Id": data["tenant_id"],
                    "X-Workspace-Id": data["workspace_id"],
                    "X-User-Id": data["admin_user_id"],
                },
            )
            assert response.status_code == 200
        finally:
            settings.auth_mode = original_mode


@pytest.mark.unit
class TestJWTUtils:
    """Unit tests for JWT utility functions.

    These tests do NOT require a database connection.
    Run with: uv run pytest tests/test_auth.py::TestJWTUtils -v
    """

    def test_create_and_decode_token(self):
        """Token can be created and decoded correctly."""
        token = create_access_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
            email="test@example.com",
        )

        payload = decode_access_token(token)
        assert payload.sub == "test-user-id"
        assert payload.tenant_id == "test-tenant-id"
        assert payload.workspace_id == "test-workspace-id"
        assert payload.role == "ADMIN"
        assert payload.email == "test@example.com"

    def test_expired_token_raises_error(self):
        """Expired token raises TokenExpiredError."""
        from datetime import timedelta

        from src.utils.jwt import TokenExpiredError

        # Create token that expires immediately
        token = create_access_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(TokenExpiredError):
            decode_access_token(token)

    def test_invalid_token_raises_error(self):
        """Invalid token raises InvalidTokenError."""
        from src.utils.jwt import InvalidTokenError

        with pytest.raises(InvalidTokenError):
            decode_access_token("invalid.token.here")
