"""Tests for Policy Engine v1.

Tests cover:
1. Tenant isolation - tenant A cannot access tenant B policy profiles
2. Create policy profile + set default behavior works
3. Attach policy to workspace and resolve returns that policy
4. Deny behavior - resolving a workflow not in allowlist returns denied
5. Admin enforcement - non-admin cannot create/update/attach
"""

import pytest
from httpx import AsyncClient


class TestPolicyProfileTenantIsolation:
    """Tests for tenant isolation in policy profiles."""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_access_tenant_b_policy_profiles(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Tenant A cannot see or modify Tenant B's policy profiles."""
        # Create two tenants
        tenant_a = await tenant_factory(name="Tenant A")
        tenant_b = await tenant_factory(name="Tenant B")

        # Create workspaces and users
        workspace_a = await workspace_factory(tenant_a, name="Workspace A")
        workspace_b = await workspace_factory(tenant_b, name="Workspace B")

        user_a = await user_factory(tenant_a, email="admin_a@test.com")
        user_b = await user_factory(tenant_b, email="admin_b@test.com")

        await membership_factory(workspace_a, user_a, role="ADMIN")
        await membership_factory(workspace_b, user_b, role="ADMIN")

        # Create policy profile in Tenant B
        policy_b = await policy_profile_factory(
            tenant_b, name="Tenant B Policy", is_default=True
        )

        # Tenant A lists policies - should not see Tenant B's policies
        response = await async_client.get(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant_a.id,
                "X-Workspace-Id": workspace_a.id,
                "X-User-Id": user_a.id,
            },
        )
        assert response.status_code == 200
        policies = response.json()
        assert len(policies) == 0  # Tenant A has no policies

        # Tenant B lists policies - should see their policy
        response = await async_client.get(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant_b.id,
                "X-Workspace-Id": workspace_b.id,
                "X-User-Id": user_b.id,
            },
        )
        assert response.status_code == 200
        policies = response.json()
        assert len(policies) == 1
        assert policies[0]["id"] == policy_b.id

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_update_tenant_b_policy(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Tenant A cannot update Tenant B's policy profiles."""
        tenant_a = await tenant_factory(name="Tenant A")
        tenant_b = await tenant_factory(name="Tenant B")

        workspace_a = await workspace_factory(tenant_a, name="Workspace A")
        workspace_b = await workspace_factory(tenant_b, name="Workspace B")

        user_a = await user_factory(tenant_a, email="admin_a@test.com")
        await user_factory(tenant_b, email="admin_b@test.com")

        await membership_factory(workspace_a, user_a, role="ADMIN")

        # Create policy in Tenant B
        policy_b = await policy_profile_factory(tenant_b, name="Tenant B Policy")

        # Tenant A tries to update Tenant B's policy - should fail with 404
        response = await async_client.patch(
            f"/policy-profiles/{policy_b.id}",
            headers={
                "X-Tenant-Id": tenant_a.id,
                "X-Workspace-Id": workspace_a.id,
                "X-User-Id": user_a.id,
            },
            json={"name": "Hacked Policy"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_attach_tenant_b_policy_to_workspace(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Tenant A cannot attach Tenant B's policy to their workspace."""
        tenant_a = await tenant_factory(name="Tenant A")
        tenant_b = await tenant_factory(name="Tenant B")

        workspace_a = await workspace_factory(tenant_a, name="Workspace A")

        user_a = await user_factory(tenant_a, email="admin_a@test.com")

        await membership_factory(workspace_a, user_a, role="ADMIN")

        # Create policy in Tenant B
        policy_b = await policy_profile_factory(tenant_b, name="Tenant B Policy")

        # Tenant A tries to attach Tenant B's policy - should fail with 403
        response = await async_client.post(
            f"/workspaces/{workspace_a.id}/policy-profile",
            headers={
                "X-Tenant-Id": tenant_a.id,
                "X-Workspace-Id": workspace_a.id,
                "X-User-Id": user_a.id,
            },
            json={"policy_profile_id": policy_b.id},
        )
        assert response.status_code == 403
        assert "does not belong" in response.json()["detail"]


class TestPolicyProfileCRUD:
    """Tests for policy profile CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_policy_profile(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """ADMIN can create a policy profile."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        response = await async_client.post(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={
                "name": "Standard Policy",
                "description": "Default policy for all workspaces",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en", "ar"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE", "DIFC", "ADGM"],
                    "feature_flags": {"law_firm_mode": False},
                    "retrieval": {"max_chunks": 12},
                    "generation": {"require_citations": True},
                },
                "is_default": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Standard Policy"
        assert data["is_default"] is True
        assert data["tenant_id"] == tenant.id
        assert "CONTRACT_REVIEW_V1" in data["config"]["allowed_workflows"]

    @pytest.mark.asyncio
    async def test_create_policy_profile_duplicate_name_fails(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Creating a policy profile with duplicate name fails."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Create existing policy
        await policy_profile_factory(tenant, name="Existing Policy")

        # Try to create with same name
        response = await async_client.post(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={
                "name": "Existing Policy",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                    "feature_flags": {},
                    "retrieval": {"max_chunks": 12},
                    "generation": {"require_citations": True},
                },
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_policy_profiles(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """ADMIN can list policy profiles."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        await policy_profile_factory(tenant, name="Policy 1")
        await policy_profile_factory(tenant, name="Policy 2")

        response = await async_client.get(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        policies = response.json()
        assert len(policies) == 2
        names = {p["name"] for p in policies}
        assert names == {"Policy 1", "Policy 2"}

    @pytest.mark.asyncio
    async def test_update_policy_profile(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """ADMIN can update a policy profile."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        policy = await policy_profile_factory(tenant, name="Original Policy")

        response = await async_client.patch(
            f"/policy-profiles/{policy.id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={
                "name": "Updated Policy",
                "description": "New description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Policy"
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_set_default_unsets_previous_default(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Setting a policy as default unsets the previous default."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Create first policy as default
        policy1 = await policy_profile_factory(
            tenant, name="Policy 1", is_default=True
        )
        await policy_profile_factory(tenant, name="Policy 2", is_default=False)

        # Update policy2 to be default
        response = await async_client.post(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={
                "name": "Policy 3",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                    "feature_flags": {},
                    "retrieval": {"max_chunks": 12},
                    "generation": {"require_citations": True},
                },
                "is_default": True,
            },
        )
        assert response.status_code == 201

        # List and check defaults
        response = await async_client.get(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        policies = response.json()
        defaults = [p for p in policies if p["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "Policy 3"


class TestPolicyAttachment:
    """Tests for attaching policies to workspaces."""

    @pytest.mark.asyncio
    async def test_attach_policy_to_workspace(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """ADMIN can attach a policy profile to a workspace."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        policy = await policy_profile_factory(tenant, name="Test Policy")

        response = await async_client.post(
            f"/workspaces/{workspace.id}/policy-profile",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={"policy_profile_id": policy.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["policy_profile_id"] == policy.id


class TestPolicyResolver:
    """Tests for policy resolution."""

    @pytest.mark.asyncio
    async def test_resolve_returns_workspace_policy(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
        clean_db,
    ):
        """Resolver returns workspace-attached policy when set."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Create tenant default policy
        await policy_profile_factory(
            tenant, name="Default Policy", is_default=True
        )

        # Create and attach workspace-specific policy
        workspace_policy = await policy_profile_factory(
            tenant,
            name="Workspace Policy",
            config={
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        # Attach to workspace via direct DB update
        workspace.policy_profile_id = workspace_policy.id
        clean_db.add(workspace)
        await clean_db.commit()

        response = await async_client.get(
            "/policy/resolve",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["policy_profile_id"] == workspace_policy.id
        assert data["policy_profile_name"] == "Workspace Policy"
        assert data["source"] == "workspace"

    @pytest.mark.asyncio
    async def test_resolve_falls_back_to_tenant_default(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Resolver falls back to tenant default when workspace has no policy."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Create only tenant default policy
        default_policy = await policy_profile_factory(
            tenant, name="Tenant Default", is_default=True
        )

        response = await async_client.get(
            "/policy/resolve",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["policy_profile_id"] == default_policy.id
        assert data["source"] == "tenant_default"

    @pytest.mark.asyncio
    async def test_resolve_returns_builtin_default_when_no_policies(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Resolver returns builtin default when no policies exist."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        response = await async_client.get(
            "/policy/resolve",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["policy_profile_id"] is None
        assert data["source"] == "builtin_default"
        assert "Built-in Default" in data["policy_profile_name"]

    @pytest.mark.asyncio
    async def test_resolve_denies_workflow_not_in_allowlist(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Resolver denies workflow not in allowed_workflows list."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Create policy with specific workflows allowed
        await policy_profile_factory(
            tenant,
            name="Restrictive Policy",
            is_default=True,
            config={
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        # Try to resolve with disallowed workflow
        response = await async_client.get(
            "/policy/resolve?workflow_name=UNAUTHORIZED_WORKFLOW",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_allowed"] is False
        assert "UNAUTHORIZED_WORKFLOW" in data["workflow_denied_reason"]

    @pytest.mark.asyncio
    async def test_resolve_allows_workflow_in_allowlist(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Resolver allows workflow in allowed_workflows list."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        await policy_profile_factory(
            tenant,
            name="Standard Policy",
            is_default=True,
            config={
                "allowed_workflows": ["CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        response = await async_client.get(
            "/policy/resolve?workflow_name=CONTRACT_REVIEW_V1",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_allowed"] is True
        assert data["workflow_denied_reason"] is None


class TestAdminEnforcement:
    """Tests that non-admins cannot access policy endpoints."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_policy_profile(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """VIEWER cannot create policy profiles."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="viewer@test.com")
        await membership_factory(workspace, user, role="VIEWER")

        response = await async_client.post(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={
                "name": "Unauthorized Policy",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                    "feature_flags": {},
                    "retrieval": {"max_chunks": 12},
                    "generation": {"require_citations": True},
                },
            },
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_cannot_update_policy_profile(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """EDITOR cannot update policy profiles."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="editor@test.com")
        await membership_factory(workspace, user, role="EDITOR")

        policy = await policy_profile_factory(tenant, name="Test Policy")

        response = await async_client.patch(
            f"/policy-profiles/{policy.id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={"name": "Updated by Editor"},
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_viewer_cannot_attach_policy_to_workspace(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """VIEWER cannot attach policy profiles to workspaces."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="viewer@test.com")
        await membership_factory(workspace, user, role="VIEWER")

        policy = await policy_profile_factory(tenant, name="Test Policy")

        response = await async_client.post(
            f"/workspaces/{workspace.id}/policy-profile",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={"policy_profile_id": policy.id},
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_cannot_list_policy_profiles(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """EDITOR cannot list policy profiles."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="editor@test.com")
        await membership_factory(workspace, user, role="EDITOR")

        await policy_profile_factory(tenant, name="Test Policy")

        response = await async_client.get(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_viewer_cannot_resolve_policy(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """VIEWER cannot use the resolve endpoint."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="viewer@test.com")
        await membership_factory(workspace, user, role="VIEWER")

        response = await async_client.get(
            "/policy/resolve",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert response.status_code == 403
        assert "ADMIN" in response.json()["detail"]


class TestAuditLogging:
    """Tests that policy operations are audit logged."""

    @pytest.mark.asyncio
    async def test_create_policy_profile_is_audited(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
    ):
        """Creating a policy profile creates an audit log entry."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        # Create policy
        response = await async_client.post(
            "/policy-profiles",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={
                "name": "Audited Policy",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                    "feature_flags": {},
                    "retrieval": {"max_chunks": 12},
                    "generation": {"require_citations": True},
                },
            },
        )
        assert response.status_code == 201

        # Check audit log
        audit_response = await async_client.get(
            "/audit?action=policy_profile.create",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert audit_response.status_code == 200
        audit_data = audit_response.json()
        assert audit_data["total"] >= 1
        assert any(
            item["action"] == "policy_profile.create"
            and item["status"] == "success"
            for item in audit_data["items"]
        )

    @pytest.mark.asyncio
    async def test_attach_policy_to_workspace_is_audited(
        self,
        async_client: AsyncClient,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
    ):
        """Attaching policy to workspace creates an audit log entry."""
        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        await membership_factory(workspace, user, role="ADMIN")

        policy = await policy_profile_factory(tenant, name="Test Policy")

        # Attach policy
        response = await async_client.post(
            f"/workspaces/{workspace.id}/policy-profile",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
            json={"policy_profile_id": policy.id},
        )
        assert response.status_code == 200

        # Check audit log
        audit_response = await async_client.get(
            "/audit?action=workspace.policy_profile.attach",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-Workspace-Id": workspace.id,
                "X-User-Id": user.id,
            },
        )
        assert audit_response.status_code == 200
        audit_data = audit_response.json()
        assert audit_data["total"] >= 1
        assert any(
            item["action"] == "workspace.policy_profile.attach"
            and item["status"] == "success"
            for item in audit_data["items"]
        )


class TestWorkflowEnforcement:
    """Tests for the require_workflow_allowed enforcement helper."""

    @pytest.mark.asyncio
    async def test_deny_by_default_blocks_workflow(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        clean_db,
    ):
        """Deny-by-default policy (no policy profiles) blocks all workflows."""
        from src.dependencies.auth import RequestContext
        from src.dependencies.policy import require_workflow_allowed
        from fastapi import HTTPException

        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        membership = await membership_factory(workspace, user, role="ADMIN")

        # Create request context
        ctx = RequestContext(
            tenant=tenant,
            user=user,
            workspace=workspace,
            membership=membership,
        )

        # Try to run a workflow with no policy profiles (builtin default denies all)
        import pytest as pt
        with pt.raises(HTTPException) as exc_info:
            await require_workflow_allowed(ctx, "CONTRACT_REVIEW_V1", clean_db)

        assert exc_info.value.status_code == 403
        assert "CONTRACT_REVIEW_V1" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_policy_allowing_workflow_permits_execution(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
        clean_db,
    ):
        """Policy with workflow in allowlist permits execution."""
        from src.dependencies.auth import RequestContext
        from src.dependencies.policy import require_workflow_allowed

        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        membership = await membership_factory(workspace, user, role="ADMIN")

        # Create policy allowing CONTRACT_REVIEW_V1
        await policy_profile_factory(
            tenant,
            name="Permissive Policy",
            is_default=True,
            config={
                "allowed_workflows": ["CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        # Create request context
        ctx = RequestContext(
            tenant=tenant,
            user=user,
            workspace=workspace,
            membership=membership,
        )

        # This should NOT raise - workflow is allowed
        resolved = await require_workflow_allowed(ctx, "CONTRACT_REVIEW_V1", clean_db)

        assert resolved.workflow_allowed is True
        assert resolved.policy_profile_name == "Permissive Policy"
        assert "CONTRACT_REVIEW_V1" in resolved.config.allowed_workflows

    @pytest.mark.asyncio
    async def test_policy_blocking_specific_workflow(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
        clean_db,
    ):
        """Policy that allows some workflows still blocks unlisted ones."""
        from src.dependencies.auth import RequestContext
        from src.dependencies.policy import require_workflow_allowed
        from fastapi import HTTPException

        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        membership = await membership_factory(workspace, user, role="ADMIN")

        # Create policy allowing only CONTRACT_REVIEW_V1
        await policy_profile_factory(
            tenant,
            name="Limited Policy",
            is_default=True,
            config={
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        ctx = RequestContext(
            tenant=tenant,
            user=user,
            workspace=workspace,
            membership=membership,
        )

        # CONTRACT_REVIEW_V1 should be allowed
        resolved = await require_workflow_allowed(ctx, "CONTRACT_REVIEW_V1", clean_db)
        assert resolved.workflow_allowed is True

        # But LEGAL_RESEARCH_V1 should be blocked
        import pytest as pt
        with pt.raises(HTTPException) as exc_info:
            await require_workflow_allowed(ctx, "LEGAL_RESEARCH_V1", clean_db)

        assert exc_info.value.status_code == 403
        assert "LEGAL_RESEARCH_V1" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_workspace_policy_takes_precedence(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        policy_profile_factory,
        clean_db,
    ):
        """Workspace-attached policy takes precedence over tenant default."""
        from src.dependencies.auth import RequestContext
        from src.dependencies.policy import require_workflow_allowed
        from fastapi import HTTPException

        tenant = await tenant_factory(name="Test Tenant")
        workspace = await workspace_factory(tenant, name="Test Workspace")
        user = await user_factory(tenant, email="admin@test.com")
        membership = await membership_factory(workspace, user, role="ADMIN")

        # Create tenant default that allows CONTRACT_REVIEW_V1
        await policy_profile_factory(
            tenant,
            name="Tenant Default",
            is_default=True,
            config={
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        # Create restrictive workspace policy that allows nothing
        restrictive_policy = await policy_profile_factory(
            tenant,
            name="Restrictive Workspace Policy",
            is_default=False,
            config={
                "allowed_workflows": [],  # Denies all
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            },
        )

        # Attach restrictive policy to workspace
        workspace.policy_profile_id = restrictive_policy.id
        clean_db.add(workspace)
        await clean_db.commit()
        await clean_db.refresh(workspace)

        ctx = RequestContext(
            tenant=tenant,
            user=user,
            workspace=workspace,
            membership=membership,
        )

        # Even though tenant default allows CONTRACT_REVIEW_V1,
        # workspace policy should block it
        import pytest as pt
        with pt.raises(HTTPException) as exc_info:
            await require_workflow_allowed(ctx, "CONTRACT_REVIEW_V1", clean_db)

        assert exc_info.value.status_code == 403
