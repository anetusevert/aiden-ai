"""Tests for Global Legal Corpus feature.

Tests cover:
- Access control (platform admin only)
- Legal instrument CRUD
- Version upload and indexing
- Global search
- Audit logging
- Tenant isolation (global corpus is separate)
"""

import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Tenant, User, Workspace, WorkspaceMembership
from src.models.legal_instrument import LegalInstrument
from src.models.legal_instrument_version import LegalInstrumentVersion
from src.models.legal_chunk import LegalChunk
from src.models.legal_chunk_embedding import LegalChunkEmbedding
from src.models.audit_log import AuditLog


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def platform_admin_user(clean_db: AsyncSession, tenant_factory, user_factory):
    """Create a platform admin user."""
    tenant = await tenant_factory()
    user = await user_factory(tenant, email="admin@platform.com")
    user.is_platform_admin = True
    await clean_db.commit()
    await clean_db.refresh(user)
    return user, tenant


@pytest.fixture
async def regular_user(clean_db: AsyncSession, tenant_factory, user_factory, workspace_factory, membership_factory):
    """Create a regular user with workspace membership."""
    tenant = await tenant_factory()
    workspace = await workspace_factory(tenant)
    user = await user_factory(tenant, email="user@example.com")
    membership = await membership_factory(workspace, user, role="ADMIN")
    return user, tenant, workspace, membership


@pytest.fixture
async def platform_admin_with_workspace(clean_db: AsyncSession, tenant_factory, user_factory, workspace_factory, membership_factory):
    """Create a platform admin user with workspace membership (for auth)."""
    tenant = await tenant_factory()
    workspace = await workspace_factory(tenant)
    user = await user_factory(tenant, email="admin@platform.com")
    user.is_platform_admin = True
    await clean_db.commit()
    membership = await membership_factory(workspace, user, role="ADMIN")
    await clean_db.refresh(user)
    return user, tenant, workspace, membership


# =============================================================================
# Access Control Tests
# =============================================================================


class TestAccessControl:
    """Tests for platform admin access control."""

    @pytest.mark.asyncio
    async def test_non_platform_admin_cannot_list_instruments(
        self, async_client: AsyncClient, regular_user
    ):
        """Non-platform admin should get 403 when listing instruments."""
        user, tenant, workspace, _ = regular_user
        response = await async_client.get(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 403
        assert "platform_admin_required" in response.text or "platform administrator" in response.text.lower()

    @pytest.mark.asyncio
    async def test_non_platform_admin_cannot_create_instrument(
        self, async_client: AsyncClient, regular_user
    ):
        """Non-platform admin should get 403 when creating instruments."""
        user, tenant, workspace, _ = regular_user
        response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "Test Law",
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_platform_admin_can_list_instruments(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Platform admin should be able to list instruments."""
        user, tenant, workspace, _ = platform_admin_with_workspace
        response = await async_client.get(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


# =============================================================================
# Legal Instrument CRUD Tests
# =============================================================================


class TestLegalInstrumentCRUD:
    """Tests for legal instrument CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_instrument_without_file(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Platform admin can create an instrument without a file."""
        user, tenant, workspace, _ = platform_admin_with_workspace
        response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "federal_law",
                "title": "Federal Law No. 1 of 2024",
                "title_ar": "القانون الاتحادي رقم 1 لسنة 2024",
                "official_source_url": "https://example.gov.ae/law/1",
                "published_at": "2024-01-15",
                "effective_at": "2024-02-01",
                "status": "active",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["instrument"]["title"] == "Federal Law No. 1 of 2024"
        assert data["instrument"]["jurisdiction"] == "UAE"
        assert data["instrument"]["instrument_type"] == "federal_law"
        assert data["version"] is None  # No file uploaded

    @pytest.mark.asyncio
    async def test_create_instrument_with_file(
        self, async_client: AsyncClient, platform_admin_with_workspace, clean_db: AsyncSession
    ):
        """Platform admin can create an instrument with initial version."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create a simple text file for testing
        file_content = b"This is a test legal document. It contains provisions about contracts and obligations."
        files = {"file": ("test_law.txt", io.BytesIO(file_content), "text/plain")}

        response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "DIFC",
                "instrument_type": "regulation",
                "title": "DIFC Investment Regulation",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["instrument"]["title"] == "DIFC Investment Regulation"
        assert data["version"] is not None
        assert data["version"]["version_label"] == "v1.0"
        assert data["version"]["language"] == "en"
        # Should be indexed after upload
        assert data["version"]["is_indexed"] is True

    @pytest.mark.asyncio
    async def test_get_instrument_detail(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Platform admin can get instrument details with versions."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument first
        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "KSA",
                "instrument_type": "royal_decree",
                "title": "Royal Decree M/1",
            },
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]

        # Get the instrument
        response = await async_client.get(
            f"/global/legal-instruments/{instrument_id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == instrument_id
        assert data["title"] == "Royal Decree M/1"
        assert "versions" in data

    @pytest.mark.asyncio
    async def test_list_instruments_with_filters(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Platform admin can list instruments with filters."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create multiple instruments
        for jurisdiction in ["UAE", "DIFC", "KSA"]:
            await async_client.post(
                "/global/legal-instruments",
                headers={
                    "X-Tenant-Id": tenant.id,
                    "X-User-Id": user.id,
                    "X-Workspace-Id": workspace.id,
                },
                data={
                    "jurisdiction": jurisdiction,
                    "instrument_type": "law",
                    "title": f"{jurisdiction} Law",
                },
            )

        # List all
        response = await async_client.get(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        assert response.json()["total"] == 3

        # Filter by jurisdiction
        response = await async_client.get(
            "/global/legal-instruments?jurisdiction=UAE",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["jurisdiction"] == "UAE"


# =============================================================================
# Version Upload and Indexing Tests
# =============================================================================


class TestVersionUploadAndIndexing:
    """Tests for version upload and indexing."""

    @pytest.mark.asyncio
    async def test_upload_version(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Platform admin can upload a new version to an existing instrument."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create instrument
        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "ADGM",
                "instrument_type": "guideline",
                "title": "ADGM Guidelines",
            },
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]

        # Upload version
        file_content = b"These are the ADGM guidelines for financial services."
        files = {"file": ("guidelines.txt", io.BytesIO(file_content), "text/plain")}

        response = await async_client.post(
            f"/global/legal-instruments/{instrument_id}/versions",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["version"]["version_label"] == "v1.0"
        assert data["version"]["is_indexed"] is True
        assert data["instrument_id"] == instrument_id

    @pytest.mark.asyncio
    async def test_reindex_version(
        self, async_client: AsyncClient, platform_admin_with_workspace, clean_db: AsyncSession
    ):
        """Platform admin can reindex a version."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create instrument with file
        file_content = b"Legal document content for reindexing test."
        files = {"file": ("doc.txt", io.BytesIO(file_content), "text/plain")}

        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "OMAN",
                "instrument_type": "decree",
                "title": "Omani Decree",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]
        version_id = create_response.json()["version"]["id"]

        # Reindex
        response = await async_client.post(
            f"/global/legal-instruments/{instrument_id}/versions/{version_id}/reindex?replace=true",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["instrument_id"] == instrument_id
        assert data["version_id"] == version_id
        assert data["chunks_indexed"] >= 0


# =============================================================================
# Search Tests
# =============================================================================


class TestGlobalLegalSearch:
    """Tests for global legal corpus search."""

    @pytest.mark.asyncio
    async def test_search_requires_auth(self, async_client: AsyncClient):
        """Search endpoint requires authentication."""
        response = await async_client.post(
            "/global/search/chunks",
            json={"query": "test"},
        )
        # Should get 401 or 400 (missing auth)
        assert response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_regular_user_can_search(
        self, async_client: AsyncClient, platform_admin_with_workspace, regular_user
    ):
        """Regular users (not just platform admins) can search the global corpus."""
        admin_user, admin_tenant, admin_workspace, _ = platform_admin_with_workspace
        reg_user, reg_tenant, reg_workspace, _ = regular_user

        # Admin creates an instrument with content
        file_content = b"This document describes contract law and obligations in commercial transactions."
        files = {"file": ("contract_law.txt", io.BytesIO(file_content), "text/plain")}

        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": admin_tenant.id,
                "X-User-Id": admin_user.id,
                "X-Workspace-Id": admin_workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "UAE Contract Law",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )

        # Regular user searches (using tenant context only)
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": reg_tenant.id,
                "X-User-Id": reg_user.id,
                "X-Workspace-Id": reg_workspace.id,
            },
            json={
                "query": "contract obligations",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Search can filter by jurisdiction and instrument type."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create instruments in different jurisdictions
        for jurisdiction in ["UAE", "DIFC"]:
            file_content = f"Legal content for {jurisdiction} regulations.".encode()
            files = {"file": (f"{jurisdiction}_doc.txt", io.BytesIO(file_content), "text/plain")}

            await async_client.post(
                "/global/legal-instruments",
                headers={
                    "X-Tenant-Id": tenant.id,
                    "X-User-Id": user.id,
                    "X-Workspace-Id": workspace.id,
                },
                data={
                    "jurisdiction": jurisdiction,
                    "instrument_type": "regulation",
                    "title": f"{jurisdiction} Regulation",
                    "version_label": "v1.0",
                    "language": "en",
                },
                files=files,
            )

        # Search with jurisdiction filter
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "regulations",
                "limit": 10,
                "jurisdiction": "UAE",
            },
        )
        assert response.status_code == 200


# =============================================================================
# Audit Logging Tests
# =============================================================================


class TestAuditLogging:
    """Tests for audit logging of global legal operations."""

    @pytest.mark.asyncio
    async def test_create_instrument_audit_log(
        self, async_client: AsyncClient, platform_admin_with_workspace, clean_db: AsyncSession
    ):
        """Creating an instrument creates an audit log entry."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "BAHRAIN",
                "instrument_type": "circular",
                "title": "Bahrain Central Bank Circular",
            },
        )

        # Check audit log
        result = await clean_db.execute(
            select(AuditLog).where(AuditLog.action == "global_legal.create")
        )
        audit_log = result.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.status == "success"
        assert audit_log.resource_type == "legal_instrument"

    @pytest.mark.asyncio
    async def test_search_audit_log(
        self, async_client: AsyncClient, platform_admin_with_workspace, clean_db: AsyncSession
    ):
        """Searching the global corpus creates an audit log entry."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "test query",
                "limit": 10,
            },
        )

        # Check audit log
        result = await clean_db.execute(
            select(AuditLog).where(AuditLog.action == "global_legal.search")
        )
        audit_log = result.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.status == "success"


# =============================================================================
# Tenant Isolation Tests
# =============================================================================


class TestTenantIsolation:
    """Tests to ensure global corpus doesn't affect tenant isolation."""

    @pytest.mark.asyncio
    async def test_global_corpus_visible_across_tenants(
        self, async_client: AsyncClient, clean_db: AsyncSession, tenant_factory, user_factory, workspace_factory, membership_factory
    ):
        """Global corpus is visible to users from different tenants."""
        # Create two tenants with users
        tenant1 = await tenant_factory(name="Tenant 1")
        workspace1 = await workspace_factory(tenant1, name="Workspace 1")
        user1 = await user_factory(tenant1, email="user1@tenant1.com")
        user1.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace1, user1)
        await clean_db.refresh(user1)

        tenant2 = await tenant_factory(name="Tenant 2")
        workspace2 = await workspace_factory(tenant2, name="Workspace 2")
        user2 = await user_factory(tenant2, email="user2@tenant2.com")
        await membership_factory(workspace2, user2)

        # User1 (platform admin) creates a global instrument
        file_content = b"Global law content accessible to all."
        files = {"file": ("global_law.txt", io.BytesIO(file_content), "text/plain")}

        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant1.id,
                "X-User-Id": user1.id,
                "X-Workspace-Id": workspace1.id,
            },
            data={
                "jurisdiction": "QATAR",
                "instrument_type": "law",
                "title": "Qatar Global Law",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert create_response.status_code == 201

        # User2 (different tenant) can search and find it
        search_response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant2.id,
                "X-User-Id": user2.id,
                "X-Workspace-Id": workspace2.id,
            },
            json={
                "query": "accessible",
                "limit": 10,
            },
        )
        assert search_response.status_code == 200
        # Results should include the global law (content matching)
        data = search_response.json()
        assert "results" in data

    @pytest.mark.asyncio
    async def test_workspace_documents_separate_from_global(
        self, async_client: AsyncClient, clean_db: AsyncSession, platform_admin_with_workspace
    ):
        """Workspace documents are separate from global corpus."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Search global corpus - should not find workspace documents
        # (This is more of a design verification test)
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "any content",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        # Global search only returns from global corpus, not workspace docs
        data = response.json()
        for result in data.get("results", []):
            assert result["source_type"] == "global_legal"


# =============================================================================
# Policy Enforcement Tests
# =============================================================================


class TestPolicyEnforcement:
    """Tests for policy-aware global legal search.

    Design principle: Global ≠ unrestricted. Policy is still the gate.
    """

    @pytest.mark.asyncio
    async def test_ksa_only_workspace_cannot_retrieve_uae_laws(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        tenant_factory,
        user_factory,
        workspace_factory,
        membership_factory,
    ):
        """KSA-only workspace should not see UAE laws in global search."""
        from src.models.policy_profile import PolicyProfile

        # Create tenant and workspace
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant, email="user@example.com")
        user.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace, user)
        await clean_db.refresh(user)

        # Create a policy profile that only allows KSA jurisdiction
        ksa_only_policy = PolicyProfile(
            tenant_id=tenant.id,
            name="KSA Only Policy",
            description="Only KSA jurisdiction allowed",
            config={
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en", "ar"],
                "allowed_jurisdictions": ["KSA"],  # KSA only!
                "feature_flags": {},
            },
            is_default=False,
        )
        clean_db.add(ksa_only_policy)
        await clean_db.commit()
        await clean_db.refresh(ksa_only_policy)

        # Attach policy to workspace
        workspace.policy_profile_id = ksa_only_policy.id
        await clean_db.commit()

        # Create global instruments in different jurisdictions
        # UAE law
        import io
        uae_content = b"This is UAE Federal Law about commercial contracts."
        uae_files = {"file": ("uae_law.txt", io.BytesIO(uae_content), "text/plain")}
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "federal_law",
                "title": "UAE Commercial Law",
                "version_label": "v1.0",
                "language": "en",
            },
            files=uae_files,
        )

        # KSA law
        ksa_content = b"This is Saudi Companies Law about commercial contracts."
        ksa_files = {"file": ("ksa_law.txt", io.BytesIO(ksa_content), "text/plain")}
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "KSA",
                "instrument_type": "royal_decree",
                "title": "Saudi Companies Law",
                "version_label": "v1.0",
                "language": "en",
            },
            files=ksa_files,
        )

        # Search from the KSA-only workspace
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "commercial contracts",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Should only get KSA results, NOT UAE
        for result in data.get("results", []):
            assert result["jurisdiction"] == "KSA", (
                f"Expected only KSA jurisdiction, but got {result['jurisdiction']}. "
                "Policy enforcement failed!"
            )

    @pytest.mark.asyncio
    async def test_mixed_jurisdiction_policy_filters_correctly(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        tenant_factory,
        user_factory,
        workspace_factory,
        membership_factory,
    ):
        """Workspace with UAE+DIFC policy should see both but not KSA."""
        from src.models.policy_profile import PolicyProfile

        # Create tenant and workspace
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant, email="mixed@example.com")
        user.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace, user)
        await clean_db.refresh(user)

        # Create a policy profile that allows UAE and DIFC only
        mixed_policy = PolicyProfile(
            tenant_id=tenant.id,
            name="UAE DIFC Policy",
            description="UAE and DIFC only",
            config={
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE", "DIFC"],
                "feature_flags": {},
            },
            is_default=False,
        )
        clean_db.add(mixed_policy)
        await clean_db.commit()
        await clean_db.refresh(mixed_policy)

        # Attach policy to workspace
        workspace.policy_profile_id = mixed_policy.id
        await clean_db.commit()

        # Create instruments in different jurisdictions
        import io
        for jur in ["UAE", "DIFC", "KSA"]:
            content = f"Legal content about regulations in {jur}.".encode()
            files = {"file": (f"{jur}_doc.txt", io.BytesIO(content), "text/plain")}
            await async_client.post(
                "/global/legal-instruments",
                headers={
                    "X-Tenant-Id": tenant.id,
                    "X-User-Id": user.id,
                    "X-Workspace-Id": workspace.id,
                },
                data={
                    "jurisdiction": jur,
                    "instrument_type": "regulation",
                    "title": f"{jur} Regulation",
                    "version_label": "v1.0",
                    "language": "en",
                },
                files=files,
            )

        # Search from the UAE+DIFC workspace
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "regulations",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Should only get UAE and DIFC results, NOT KSA
        jurisdictions_found = {r["jurisdiction"] for r in data.get("results", [])}
        assert "KSA" not in jurisdictions_found, (
            f"KSA should not be in results for UAE+DIFC policy. Found: {jurisdictions_found}"
        )
        # Should have UAE and/or DIFC
        allowed = {"UAE", "DIFC"}
        assert jurisdictions_found.issubset(allowed), (
            f"Found unexpected jurisdictions: {jurisdictions_found - allowed}"
        )

    @pytest.mark.asyncio
    async def test_search_results_include_source_label(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Global search results should include source_label for user trust."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument with specific dates
        import io
        content = b"Legal provisions regarding commercial transactions and contracts."
        files = {"file": ("law.txt", io.BytesIO(content), "text/plain")}

        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "KSA",
                "instrument_type": "royal_decree",
                "title": "Saudi Companies Law",
                "effective_at": "2022-01-01",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )

        # Search
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "commercial transactions",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Check source_label is present and formatted correctly
        if data.get("results"):
            result = data["results"][0]
            assert "source_label" in result
            # Should be like "Saudi Companies Law (2022)"
            assert "Saudi Companies Law" in result["source_label"]
            assert result["source_type"] == "global_legal"

    @pytest.mark.asyncio
    async def test_global_search_deny_by_default_when_policy_empty(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        tenant_factory,
        user_factory,
        workspace_factory,
        membership_factory,
    ):
        """Global search returns zero results when policy allows nothing (deny-by-default)."""
        from src.models.policy_profile import PolicyProfile

        # Create tenant and workspace
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant, email="deny_test@example.com")
        user.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace, user)
        await clean_db.refresh(user)

        # Create a policy profile with EMPTY allowed lists (deny-by-default)
        deny_all_policy = PolicyProfile(
            tenant_id=tenant.id,
            name="Deny All Policy",
            description="Empty allowed lists = deny all",
            config={
                "allowed_workflows": [],
                "allowed_input_languages": [],  # EMPTY!
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": [],  # EMPTY!
                "feature_flags": {},
            },
            is_default=False,
        )
        clean_db.add(deny_all_policy)
        await clean_db.commit()
        await clean_db.refresh(deny_all_policy)

        # Attach policy to workspace
        workspace.policy_profile_id = deny_all_policy.id
        await clean_db.commit()

        # Create a global instrument
        import io
        content = b"Legal document that should not be returned due to deny-by-default."
        files = {"file": ("deny_test.txt", io.BytesIO(content), "text/plain")}

        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "UAE Law Deny Test",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )

        # Search should return ZERO results due to deny-by-default
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "legal document",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # MUST return zero results - deny-by-default enforcement
        assert data["total"] == 0, (
            f"Expected 0 results (deny-by-default) but got {data['total']}. "
            "Policy with empty allowed_jurisdictions/languages should return nothing."
        )

    @pytest.mark.asyncio
    async def test_global_search_respects_allowed_input_languages(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        tenant_factory,
        user_factory,
        workspace_factory,
        membership_factory,
    ):
        """Global search filters by allowed_input_languages from policy."""
        from src.models.policy_profile import PolicyProfile

        # Create tenant and workspace
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant, email="lang_filter@example.com")
        user.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace, user)
        await clean_db.refresh(user)

        # Create a policy that only allows Arabic
        arabic_only_policy = PolicyProfile(
            tenant_id=tenant.id,
            name="Arabic Only Policy",
            description="Only Arabic language allowed",
            config={
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["ar"],  # Arabic only!
                "allowed_output_languages": ["ar"],
                "allowed_jurisdictions": ["UAE", "KSA"],
                "feature_flags": {},
            },
            is_default=False,
        )
        clean_db.add(arabic_only_policy)
        await clean_db.commit()
        await clean_db.refresh(arabic_only_policy)

        # Attach policy to workspace
        workspace.policy_profile_id = arabic_only_policy.id
        await clean_db.commit()

        # Create English and Arabic instruments
        import io
        en_content = b"English legal document content."
        en_files = {"file": ("en_doc.txt", io.BytesIO(en_content), "text/plain")}
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "English Law",
                "version_label": "v1.0",
                "language": "en",  # English
            },
            files=en_files,
        )

        ar_content = "محتوى قانوني عربي".encode('utf-8')
        ar_files = {"file": ("ar_doc.txt", io.BytesIO(ar_content), "text/plain")}
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "KSA",
                "instrument_type": "law",
                "title": "Arabic Law",
                "version_label": "v1.0",
                "language": "ar",  # Arabic
            },
            files=ar_files,
        )

        # Search should only return Arabic results
        response = await async_client.post(
            "/global/search/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "query": "legal content قانوني",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # All results should be Arabic (if any)
        for result in data.get("results", []):
            assert result["language"] == "ar", (
                f"Expected only Arabic results, but got language={result['language']}. "
                "allowed_input_languages filter not enforced."
            )


# =============================================================================
# Viewer Endpoint Tests (Read-Only, All Authenticated Users)
# =============================================================================


class TestGlobalLegalViewer:
    """Tests for the global legal viewer endpoints (read-only).

    These endpoints are available to all authenticated users (not just platform admins)
    but respect workspace policy for jurisdiction filtering.
    """

    @pytest.mark.asyncio
    async def test_viewer_list_instruments(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Regular users can list global legal instruments via viewer endpoint."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument first
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "UAE Test Law for Viewer",
            },
        )

        # Use viewer endpoint (not admin endpoint)
        response = await async_client.get(
            "/global/legal/instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_viewer_get_instrument_detail(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Users can get instrument detail via viewer endpoint."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument
        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "federal_law",
                "title": "UAE Federal Law for Viewer Detail",
            },
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]

        # Get detail via viewer endpoint
        response = await async_client.get(
            f"/global/legal/instruments/{instrument_id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == instrument_id
        assert data["title"] == "UAE Federal Law for Viewer Detail"
        assert "versions" in data

    @pytest.mark.asyncio
    async def test_viewer_get_version_detail(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Users can get version detail via viewer endpoint."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument with a file
        file_content = b"This is test content for version detail viewer."
        files = {"file": ("test_viewer.txt", io.BytesIO(file_content), "text/plain")}

        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "DIFC",
                "instrument_type": "regulation",
                "title": "DIFC Reg for Version Viewer",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]
        version_id = create_response.json()["version"]["id"]

        # Get version detail via viewer endpoint
        response = await async_client.get(
            f"/global/legal/instruments/{instrument_id}/versions/{version_id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == version_id
        assert data["version_label"] == "v1.0"
        assert data["instrument_id"] == instrument_id
        assert data["instrument_title"] == "DIFC Reg for Version Viewer"

    @pytest.mark.asyncio
    async def test_viewer_list_chunks(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Users can list chunks via viewer endpoint."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument with a file
        file_content = b"This is test content for chunk listing in the viewer."
        files = {"file": ("test_chunks.txt", io.BytesIO(file_content), "text/plain")}

        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "KSA",
                "instrument_type": "royal_decree",
                "title": "KSA Decree for Chunk Viewer",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]
        version_id = create_response.json()["version"]["id"]

        # List chunks via viewer endpoint
        response = await async_client.get(
            f"/global/legal/instruments/{instrument_id}/versions/{version_id}/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert "chunk_count" in data
        assert data["version_id"] == version_id
        assert data["chunk_count"] >= 1

    @pytest.mark.asyncio
    async def test_viewer_get_chunk_with_context(
        self, async_client: AsyncClient, platform_admin_with_workspace
    ):
        """Users can get a single chunk with context via viewer endpoint."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument with a file
        file_content = b"This is test content for single chunk viewer with context navigation."
        files = {"file": ("test_single_chunk.txt", io.BytesIO(file_content), "text/plain")}

        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "ADGM",
                "instrument_type": "guideline",
                "title": "ADGM Guide for Single Chunk",
                "version_label": "v1.0",
                "language": "en",
            },
            files=files,
        )
        assert create_response.status_code == 201
        instrument_id = create_response.json()["instrument"]["id"]
        version_id = create_response.json()["version"]["id"]

        # First get the chunk list
        chunks_response = await async_client.get(
            f"/global/legal/instruments/{instrument_id}/versions/{version_id}/chunks",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        chunks = chunks_response.json()["chunks"]
        assert len(chunks) >= 1
        chunk_id = chunks[0]["id"]

        # Get single chunk with context
        response = await async_client.get(
            f"/global/legal/instruments/{instrument_id}/versions/{version_id}/chunks/{chunk_id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "chunk" in data
        assert data["chunk"]["id"] == chunk_id
        assert "text" in data["chunk"]
        assert "char_start" in data["chunk"]
        assert "char_end" in data["chunk"]

    @pytest.mark.asyncio
    async def test_viewer_policy_denies_unauthorized_jurisdiction(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        tenant_factory,
        user_factory,
        workspace_factory,
        membership_factory,
    ):
        """Viewer endpoint denies access to instruments outside workspace policy."""
        from src.models.policy_profile import PolicyProfile

        # Create tenant and workspace
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant, email="viewer_policy@example.com")
        user.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace, user)
        await clean_db.refresh(user)

        # Create a policy that only allows KSA
        ksa_only_policy = PolicyProfile(
            tenant_id=tenant.id,
            name="KSA Only Viewer Policy",
            description="Only KSA allowed",
            config={
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en", "ar"],
                "allowed_jurisdictions": ["KSA"],
                "feature_flags": {},
            },
            is_default=False,
        )
        clean_db.add(ksa_only_policy)
        await clean_db.commit()
        await clean_db.refresh(ksa_only_policy)

        # Attach policy to workspace
        workspace.policy_profile_id = ksa_only_policy.id
        await clean_db.commit()

        # Create a UAE instrument (outside KSA policy)
        create_response = await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",  # Not in KSA-only policy
                "instrument_type": "law",
                "title": "UAE Law Denied by Policy",
            },
        )
        assert create_response.status_code == 201
        uae_instrument_id = create_response.json()["instrument"]["id"]

        # Try to access UAE instrument via viewer - should be denied
        response = await async_client.get(
            f"/global/legal/instruments/{uae_instrument_id}",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 403
        assert "jurisdiction" in response.text.lower() or "policy" in response.text.lower()

    @pytest.mark.asyncio
    async def test_viewer_creates_audit_log(
        self, async_client: AsyncClient, platform_admin_with_workspace, clean_db: AsyncSession
    ):
        """Viewer endpoint creates audit log entries."""
        user, tenant, workspace, _ = platform_admin_with_workspace

        # Create an instrument
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "UAE Law for Audit Test",
            },
        )

        # Access viewer endpoint
        await async_client.get(
            "/global/legal/instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )

        # Check audit log was created
        result = await clean_db.execute(
            select(AuditLog).where(AuditLog.action == "global.legal.view")
        )
        audit_logs = result.scalars().all()
        assert len(audit_logs) >= 1
        assert any(log.status == "success" for log in audit_logs)

    @pytest.mark.asyncio
    async def test_viewer_list_only_shows_active_instruments(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        tenant_factory,
        user_factory,
        workspace_factory,
        membership_factory,
    ):
        """Viewer list only shows active instruments, not superseded/repealed."""
        # Create tenant and workspace
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant, email="viewer_active@example.com")
        user.is_platform_admin = True
        await clean_db.commit()
        await membership_factory(workspace, user)
        await clean_db.refresh(user)

        # Create active and superseded instruments
        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "UAE Active Law",
                "status": "active",
            },
        )

        await async_client.post(
            "/global/legal-instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            data={
                "jurisdiction": "UAE",
                "instrument_type": "law",
                "title": "UAE Superseded Law",
                "status": "superseded",
            },
        )

        # Viewer list should only show active
        response = await async_client.get(
            "/global/legal/instruments",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()

        # All items should be active
        for item in data["items"]:
            assert item["status"] == "active", (
                f"Viewer list should only show active instruments, found: {item['status']}"
            )


# =============================================================================
# Platform Admin Bootstrap Tests
# =============================================================================


class TestPlatformAdminBootstrap:
    """Tests for platform admin bootstrap mechanism."""

    @pytest.mark.asyncio
    async def test_bootstrap_sets_admin_when_user_exists(
        self, clean_db: AsyncSession, tenant_factory, user_factory
    ):
        """Bootstrap should set is_platform_admin=true when user exists."""
        from src.services.platform_admin_bootstrap import bootstrap_platform_admin
        from src.config import settings

        # Create a user
        tenant = await tenant_factory()
        user = await user_factory(tenant, email="bootstrap@example.com")
        await clean_db.commit()

        # Verify user is not admin initially
        assert user.is_platform_admin is False

        # Mock the settings to use this email
        original_email = settings.platform_admin_email
        original_env = settings.environment
        try:
            settings.platform_admin_email = "bootstrap@example.com"
            settings.environment = "dev"

            result = await bootstrap_platform_admin(clean_db)

            assert result["action"] == "set"
            assert result["email"] == "bootstrap@example.com"

            # Verify user is now admin
            await clean_db.refresh(user)
            assert user.is_platform_admin is True

        finally:
            settings.platform_admin_email = original_email
            settings.environment = original_env

    @pytest.mark.asyncio
    async def test_bootstrap_blocked_in_prod_by_default(
        self, clean_db: AsyncSession, tenant_factory, user_factory
    ):
        """Bootstrap should be blocked in production by default."""
        from src.services.platform_admin_bootstrap import bootstrap_platform_admin
        from src.config import settings

        # Create a user
        tenant = await tenant_factory()
        user = await user_factory(tenant, email="prod_user@example.com")
        await clean_db.commit()

        # Mock production settings
        original_email = settings.platform_admin_email
        original_env = settings.environment
        original_enabled = settings.global_corpus_enabled_in_prod
        try:
            settings.platform_admin_email = "prod_user@example.com"
            settings.environment = "prod"
            settings.global_corpus_enabled_in_prod = False

            result = await bootstrap_platform_admin(clean_db)

            assert result["action"] == "blocked"
            assert "production" in result["message"].lower()

            # User should NOT be admin
            await clean_db.refresh(user)
            assert user.is_platform_admin is False

        finally:
            settings.platform_admin_email = original_email
            settings.environment = original_env
            settings.global_corpus_enabled_in_prod = original_enabled

    @pytest.mark.asyncio
    async def test_bootstrap_user_not_found(self, clean_db: AsyncSession):
        """Bootstrap should log warning when user doesn't exist."""
        from src.services.platform_admin_bootstrap import bootstrap_platform_admin
        from src.config import settings

        original_email = settings.platform_admin_email
        original_env = settings.environment
        try:
            settings.platform_admin_email = "nonexistent@example.com"
            settings.environment = "dev"

            result = await bootstrap_platform_admin(clean_db)

            assert result["action"] == "user_not_found"
            assert "not found" in result["message"].lower()

        finally:
            settings.platform_admin_email = original_email
            settings.environment = original_env

    @pytest.mark.asyncio
    async def test_bootstrap_already_admin(
        self, clean_db: AsyncSession, tenant_factory, user_factory
    ):
        """Bootstrap should skip if user is already admin."""
        from src.services.platform_admin_bootstrap import bootstrap_platform_admin
        from src.config import settings

        # Create an admin user
        tenant = await tenant_factory()
        user = await user_factory(tenant, email="already_admin@example.com")
        user.is_platform_admin = True
        await clean_db.commit()

        original_email = settings.platform_admin_email
        original_env = settings.environment
        try:
            settings.platform_admin_email = "already_admin@example.com"
            settings.environment = "dev"

            result = await bootstrap_platform_admin(clean_db)

            assert result["action"] == "already_admin"

        finally:
            settings.platform_admin_email = original_email
            settings.environment = original_env
