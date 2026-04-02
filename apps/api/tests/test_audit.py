"""Integration tests for audit logging functionality.

These tests verify:
1. Successful /auth/dev-login creates an audit log row
2. Successful creation of workspace/user/membership writes audit rows
3. Unauthorized access attempts write a fail audit row
4. /audit endpoint returns tenant-scoped rows only
5. /audit endpoint enforces ADMIN role
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AuditLog, Tenant, User, Workspace, WorkspaceMembership
from src.utils.jwt import create_access_token


@pytest.fixture
async def clean_audit_logs(clean_db: AsyncSession) -> AsyncSession:
    """Ensure audit_logs table is clean before test."""
    await clean_db.execute(text("DELETE FROM audit_logs"))
    await clean_db.commit()
    return clean_db


@pytest.fixture
async def bootstrapped_tenant(clean_audit_logs: AsyncSession) -> dict:
    """Create a fully bootstrapped tenant with workspace, admin user, and membership."""
    db = clean_audit_logs
    
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        primary_jurisdiction="UAE",
        data_residency_policy="UAE",
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    # Create workspace
    workspace = Workspace(
        tenant_id=tenant.id,
        name="Test Workspace",
        workspace_type="IN_HOUSE",
        jurisdiction_profile="UAE_DEFAULT",
        default_language="en",
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    
    # Create admin user
    admin_user = User(
        tenant_id=tenant.id,
        email="admin@test.com",
        full_name="Admin User",
    )
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    
    # Create admin membership
    membership = WorkspaceMembership(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        user_id=admin_user.id,
        role="ADMIN",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    
    # Create JWT token
    token = create_access_token(
        user_id=admin_user.id,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        role="ADMIN",
        email=admin_user.email,
    )
    
    return {
        "tenant": tenant,
        "workspace": workspace,
        "admin_user": admin_user,
        "membership": membership,
        "token": token,
        "db": db,
    }


@pytest.fixture
async def viewer_user(bootstrapped_tenant: dict) -> dict:
    """Create a viewer user in the same tenant."""
    db = bootstrapped_tenant["db"]
    tenant = bootstrapped_tenant["tenant"]
    workspace = bootstrapped_tenant["workspace"]
    
    # Create viewer user
    viewer = User(
        tenant_id=tenant.id,
        email="viewer@test.com",
        full_name="Viewer User",
    )
    db.add(viewer)
    await db.commit()
    await db.refresh(viewer)
    
    # Create viewer membership
    membership = WorkspaceMembership(
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        user_id=viewer.id,
        role="VIEWER",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    
    # Create JWT token for viewer
    token = create_access_token(
        user_id=viewer.id,
        tenant_id=tenant.id,
        workspace_id=workspace.id,
        role="VIEWER",
        email=viewer.email,
    )
    
    return {
        **bootstrapped_tenant,
        "viewer": viewer,
        "viewer_membership": membership,
        "viewer_token": token,
    }


class TestDevLoginAuditLogging:
    """Tests for audit logging on /auth/dev-login endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_successful_dev_login_creates_audit_log(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that successful dev-login creates an audit log entry."""
        tenant = bootstrapped_tenant["tenant"]
        workspace = bootstrapped_tenant["workspace"]
        admin_user = bootstrapped_tenant["admin_user"]
        db = bootstrapped_tenant["db"]
        
        # Perform dev-login
        response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": tenant.id,
                "workspace_id": workspace.id,
                "email": admin_user.email,
            },
        )
        
        assert response.status_code == 200
        assert response.cookies.get("access_token")
        
        # Verify audit log was created
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "auth.dev_login",
                AuditLog.tenant_id == tenant.id,
                AuditLog.status == "success",
            )
        )
        audit_log = result.scalar_one_or_none()
        
        assert audit_log is not None
        assert audit_log.user_id == admin_user.id
        assert audit_log.workspace_id == workspace.id
        assert audit_log.request_id is not None
        assert audit_log.meta is not None
        assert audit_log.meta.get("email") == admin_user.email

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_failed_dev_login_creates_fail_audit_log(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that failed dev-login creates a fail audit log entry."""
        tenant = bootstrapped_tenant["tenant"]
        workspace = bootstrapped_tenant["workspace"]
        db = bootstrapped_tenant["db"]
        
        # Perform dev-login with invalid email
        response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": tenant.id,
                "workspace_id": workspace.id,
                "email": "nonexistent@test.com",
            },
        )
        
        assert response.status_code == 401
        
        # Verify fail audit log was created
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "auth.dev_login",
                AuditLog.tenant_id == tenant.id,
                AuditLog.status == "fail",
            )
        )
        audit_log = result.scalar_one_or_none()
        
        assert audit_log is not None
        assert audit_log.meta is not None
        assert audit_log.meta.get("reason") == "user_not_found"


class TestWorkspaceCreationAuditLogging:
    """Tests for audit logging on workspace creation."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_successful_workspace_creation_creates_audit_log(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that successful workspace creation creates an audit log entry."""
        tenant = bootstrapped_tenant["tenant"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # Create a new workspace
        response = await async_client.post(
            f"/tenants/{tenant.id}/workspaces",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "New Workspace",
                "workspace_type": "LAW_FIRM",
                "jurisdiction_profile": "UAE_DEFAULT",
                "default_language": "en",
            },
        )
        
        assert response.status_code == 201
        new_workspace_id = response.json()["id"]
        
        # Verify audit log was created
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "workspace.create",
                AuditLog.tenant_id == tenant.id,
                AuditLog.status == "success",
            )
        )
        audit_log = result.scalar_one_or_none()
        
        assert audit_log is not None
        assert audit_log.resource_type == "workspace"
        assert audit_log.resource_id == new_workspace_id
        assert audit_log.meta is not None
        assert audit_log.meta.get("workspace_name") == "New Workspace"


class TestUserCreationAuditLogging:
    """Tests for audit logging on user creation."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_successful_user_creation_creates_audit_log(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that successful user creation creates an audit log entry."""
        tenant = bootstrapped_tenant["tenant"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # Create a new user
        response = await async_client.post(
            f"/tenants/{tenant.id}/users",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newuser@test.com",
                "full_name": "New User",
            },
        )
        
        assert response.status_code == 201
        new_user_id = response.json()["id"]
        
        # Verify audit log was created
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "user.create",
                AuditLog.tenant_id == tenant.id,
                AuditLog.status == "success",
            )
        )
        audit_log = result.scalar_one_or_none()
        
        assert audit_log is not None
        assert audit_log.resource_type == "user"
        assert audit_log.resource_id == new_user_id
        assert audit_log.meta is not None
        assert audit_log.meta.get("email") == "newuser@test.com"


class TestMembershipCreationAuditLogging:
    """Tests for audit logging on membership creation."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_successful_membership_creation_creates_audit_log(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that successful membership creation creates an audit log entry."""
        tenant = bootstrapped_tenant["tenant"]
        workspace = bootstrapped_tenant["workspace"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # First create a user to add as member
        new_user = User(
            tenant_id=tenant.id,
            email="newmember@test.com",
            full_name="New Member",
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Add the user as a member
        response = await async_client.post(
            f"/workspaces/{workspace.id}/memberships",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": new_user.id,
                "role": "EDITOR",
            },
        )
        
        assert response.status_code == 201
        
        # Verify audit log was created
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "membership.create",
                AuditLog.tenant_id == tenant.id,
                AuditLog.status == "success",
            )
        )
        audit_log = result.scalar_one_or_none()
        
        assert audit_log is not None
        assert audit_log.resource_type == "membership"
        assert audit_log.meta is not None
        assert audit_log.meta.get("target_user_id") == new_user.id
        assert audit_log.meta.get("role") == "EDITOR"


class TestAuditEndpoint:
    """Tests for GET /audit endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_audit_endpoint_returns_tenant_scoped_logs(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that /audit returns only logs for the current tenant."""
        tenant = bootstrapped_tenant["tenant"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # Create an audit log for this tenant
        audit_log = AuditLog(
            tenant_id=tenant.id,
            request_id="test-request-id",
            action="test.action",
            status="success",
        )
        db.add(audit_log)
        
        # Create another tenant with its own audit log
        other_tenant = Tenant(
            name="Other Tenant",
            primary_jurisdiction="KSA",
            data_residency_policy="KSA",
        )
        db.add(other_tenant)
        await db.commit()
        await db.refresh(other_tenant)
        
        other_audit_log = AuditLog(
            tenant_id=other_tenant.id,
            request_id="other-request-id",
            action="other.action",
            status="success",
        )
        db.add(other_audit_log)
        await db.commit()
        
        # Query audit logs
        response = await async_client.get(
            "/audit",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only current tenant's logs are returned
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["tenant_id"] == tenant.id
            assert item["tenant_id"] != other_tenant.id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_audit_endpoint_requires_admin_role(
        self, async_client: AsyncClient, viewer_user: dict
    ) -> None:
        """Test that /audit requires ADMIN role."""
        viewer_token = viewer_user["viewer_token"]
        
        # Try to access audit logs as viewer
        response = await async_client.get(
            "/audit",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_audit_endpoint_filters_by_workspace(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that /audit can filter by workspace_id."""
        tenant = bootstrapped_tenant["tenant"]
        workspace = bootstrapped_tenant["workspace"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # Create audit logs for different workspaces
        log_with_workspace = AuditLog(
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            request_id="workspace-request-id",
            action="test.workspace_action",
            status="success",
        )
        db.add(log_with_workspace)
        
        log_without_workspace = AuditLog(
            tenant_id=tenant.id,
            workspace_id=None,
            request_id="no-workspace-request-id",
            action="test.no_workspace_action",
            status="success",
        )
        db.add(log_without_workspace)
        await db.commit()
        
        # Query with workspace filter
        response = await async_client.get(
            f"/audit?workspace_id={workspace.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only workspace-scoped logs are returned
        for item in data["items"]:
            assert item["workspace_id"] == workspace.id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_audit_endpoint_filters_by_action(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that /audit can filter by action."""
        tenant = bootstrapped_tenant["tenant"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # Create audit logs with different actions
        log1 = AuditLog(
            tenant_id=tenant.id,
            request_id="req-1",
            action="test.action_a",
            status="success",
        )
        db.add(log1)
        
        log2 = AuditLog(
            tenant_id=tenant.id,
            request_id="req-2",
            action="test.action_b",
            status="success",
        )
        db.add(log2)
        await db.commit()
        
        # Query with action filter
        response = await async_client.get(
            "/audit?action=test.action_a",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify only matching action logs are returned
        for item in data["items"]:
            assert item["action"] == "test.action_a"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_audit_endpoint_respects_limit(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that /audit respects the limit parameter."""
        tenant = bootstrapped_tenant["tenant"]
        token = bootstrapped_tenant["token"]
        db = bootstrapped_tenant["db"]
        
        # Create multiple audit logs
        for i in range(10):
            log = AuditLog(
                tenant_id=tenant.id,
                request_id=f"req-{i}",
                action="test.many_logs",
                status="success",
            )
            db.add(log)
        await db.commit()
        
        # Query with limit
        response = await async_client.get(
            "/audit?limit=3",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["items"]) == 3
        assert data["limit"] == 3
        assert data["total"] >= 10


class TestRequestIdMiddleware:
    """Tests for X-Request-Id middleware."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_response_includes_request_id_header(
        self, async_client: AsyncClient
    ) -> None:
        """Test that responses include X-Request-Id header."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-Id" in response.headers
        # Verify it's a valid UUID format
        request_id = response.headers["X-Request-Id"]
        assert len(request_id) == 36  # UUID format

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_provided_request_id_is_echoed(
        self, async_client: AsyncClient
    ) -> None:
        """Test that provided X-Request-Id is echoed in response."""
        custom_request_id = "12345678-1234-1234-1234-123456789012"
        
        response = await async_client.get(
            "/health",
            headers={"X-Request-Id": custom_request_id},
        )
        
        assert response.status_code == 200
        assert response.headers["X-Request-Id"] == custom_request_id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_audit_logs_include_request_id(
        self, async_client: AsyncClient, bootstrapped_tenant: dict
    ) -> None:
        """Test that audit logs include the request ID."""
        tenant = bootstrapped_tenant["tenant"]
        workspace = bootstrapped_tenant["workspace"]
        admin_user = bootstrapped_tenant["admin_user"]
        db = bootstrapped_tenant["db"]
        
        custom_request_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        
        # Perform dev-login with custom request ID
        response = await async_client.post(
            "/auth/dev-login",
            headers={"X-Request-Id": custom_request_id},
            json={
                "tenant_id": tenant.id,
                "workspace_id": workspace.id,
                "email": admin_user.email,
            },
        )
        
        assert response.status_code == 200
        assert response.headers["X-Request-Id"] == custom_request_id
        
        # Verify audit log has the same request ID
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.action == "auth.dev_login",
                AuditLog.request_id == custom_request_id,
            )
        )
        audit_log = result.scalar_one_or_none()
        
        assert audit_log is not None
        assert audit_log.request_id == custom_request_id
