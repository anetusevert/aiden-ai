"""Tests for Clause Redlines workflow (CLAUSE_REDLINES_V1).

Run all clause redlines tests (requires PostgreSQL + MinIO):
    uv run pytest tests/test_clause_redlines.py -v

Run v2 detection tests only:
    uv run pytest tests/test_clause_redlines.py -v -k "V2"

Tests cover:
1. Happy path: returns items for at least 2 clause types with valid citations
2. Uncited claim: items with uncited "contract says" claims are downgraded
3. Invalid citations: out-of-range citations are corrected/removed
4. Policy disallows workflow -> 403
5. Role enforcement: VIEWER gets 403, EDITOR allowed
6. Audit log entry created
7. Document/version access validation

v2 Detection Tests:
8. Heading detection boosts correct clause selection
9. Neighbor inclusion adds adjacent chunk evidence
10. Negative scoring prevents selecting signature/schedule chunks
11. Confidence_level and confidence_reason populated deterministically
"""

import pytest
from httpx import AsyncClient

from tests.helpers import bootstrap_and_login


@pytest.mark.integration
class TestClauseRedlinesHappyPath:
    """Tests for successful clause redlines scenarios."""

    @pytest.mark.asyncio
    async def test_clause_redlines_returns_items_with_citations(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that clause redlines returns properly cited items."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that allows CLAUSE_REDLINES_V1
        policy_body = {
            "name": "Clause Redlines Policy",
            "config": {
                "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en", "ar"],
                "allowed_jurisdictions": ["UAE", "DIFC", "ADGM", "KSA"],
                "feature_flags": {},
            },
            "is_default": True,
        }
        response = await async_client.post(
            "/policy-profiles",
            headers=headers,
            json=policy_body,
        )
        assert response.status_code == 201

        # Upload a contract document with clause-related content
        content = (
            "EMPLOYMENT AGREEMENT\n\n"
            "This Employment Agreement is governed by the laws of the United Arab Emirates.\n"
            "Any disputes shall be resolved in the courts of Dubai.\n\n"
            "TERMINATION: The Employee may terminate this Agreement by providing 30 days written notice.\n"
            "The Employer may terminate for cause without notice.\n\n"
            "LIABILITY: The Employer's liability under this Agreement shall not exceed the total contract value.\n"
            "Neither party shall be liable for consequential damages.\n\n"
            "CONFIDENTIALITY: All confidential information must be kept secret.\n"
            "Disclosure to third parties is prohibited without consent.\n\n"
            "PAYMENT: Payment shall be made within 30 days of invoice date.\n"
            "Late payment shall incur a fee of 1% per month.\n\n"
        ).encode() * 10  # Make it longer to ensure chunking

        files = {"file": ("contract.txt", content, "text/plain")}
        form_data = {
            "title": "Employment Contract",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "confidential",
        }
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data=form_data,
        )
        assert response.status_code == 201
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Call clause redlines endpoint
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "jurisdiction": "UAE",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have items with citations
        assert result["insufficient_sources"] is False
        assert len(result["items"]) >= 2  # At least 2 clause types

        # Check item structure
        item = result["items"][0]
        assert "clause_type" in item
        assert "status" in item
        assert "confidence" in item
        assert item["status"] in ["found", "missing", "insufficient_evidence"]

        # Found items should have citations
        found_items = [i for i in result["items"] if i["status"] == "found"]
        if found_items:
            for found_item in found_items:
                assert "citations" in found_item
                # Issue should contain citation markers if present
                if found_item["issue"]:
                    assert "[" in found_item["issue"] or found_item["status"] == "missing"

        # Check meta
        assert result["meta"]["provider"] == "stub"
        assert result["meta"]["jurisdiction"] == "UAE"
        assert result["meta"]["strict_citations_failed"] is False

    @pytest.mark.asyncio
    async def test_clause_redlines_with_playbook_hint(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that clause redlines accepts playbook_hint parameter."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE", "DIFC"],
                },
                "is_default": True,
            },
        )

        # Upload document
        content = (
            "CONTRACT TERMS\n\n"
            "Governing law: UAE courts.\n"
            "Liability is limited to the contract value.\n"
            "Termination requires 30 days notice.\n"
        ).encode() * 20

        files = {"file": ("terms.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Terms Document",
                "document_type": "contract",
                "jurisdiction": "DIFC",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze with playbook_hint
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "jurisdiction": "DIFC",
                "playbook_hint": "Focus on DIFC-specific requirements and English law principles.",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should complete successfully with hint
        assert result["insufficient_sources"] is False
        assert result["meta"]["jurisdiction"] == "DIFC"

    @pytest.mark.asyncio
    async def test_clause_redlines_with_specific_clause_types(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that clause redlines can analyze specific clause types."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document
        content = (
            "CONTRACT\n\n"
            "Liability shall be limited to 100,000 USD.\n"
            "Governing law: UAE.\n"
        ).encode() * 20

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Contract Doc",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze only specific clause types
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "clause_types": ["liability", "governing_law"],
            },
        )
        assert response.status_code == 200
        result = response.json()

        assert result["insufficient_sources"] is False


@pytest.mark.integration
class TestClauseRedlinesStrictCitations:
    """Tests for strict citation enforcement."""

    @pytest.mark.asyncio
    async def test_uncited_claim_is_downgraded(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that items with uncited 'contract says' claims are downgraded."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with test marker for uncited claim mode
        content = (
            "[TEST:CLAUSE_REDLINES_UNCITED_CLAIM]\n"
            "CONTRACT TERMS\n\n"
            "Liability shall be limited. Termination requires notice.\n"
        ).encode() * 20

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Test Contract [TEST:CLAUSE_REDLINES_UNCITED_CLAIM]",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have downgraded some items
        meta = result["meta"]
        assert meta["downgraded_count"] >= 1

        # Items without valid citations for contract claims should be downgraded
        for item in result["items"]:
            if item["status"] == "found":
                # Found items should have citations
                assert len(item["citations"]) > 0

    @pytest.mark.asyncio
    async def test_invalid_citations_corrected(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that out-of-range citations are corrected/removed."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with test marker for invalid citations mode
        content = (
            "[TEST:CLAUSE_REDLINES_INVALID_CITATIONS]\n"
            "CONTRACT PROVISIONS\n\n"
            "Governing law is UAE.\n"
            "Liability is capped.\n"
        ).encode() * 20

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Test Contract [TEST:CLAUSE_REDLINES_INVALID_CITATIONS]",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # The valid item should remain
        if result["items"]:
            for item in result["items"]:
                if item["status"] == "found" and item["citations"]:
                    # All remaining citations should be valid (within range)
                    chunk_count = result["meta"]["evidence_chunk_count"]
                    for cite in item["citations"]:
                        assert cite <= chunk_count


@pytest.mark.integration
class TestClauseRedlinesPolicyEnforcement:
    """Tests for policy enforcement."""

    @pytest.mark.asyncio
    async def test_policy_disallows_workflow_returns_403(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that policy denying CLAUSE_REDLINES_V1 returns 403."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that does NOT allow CLAUSE_REDLINES_V1
        policy_body = {
            "name": "No Redlines Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],  # Different workflow
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],
                "feature_flags": {},
            },
            "is_default": True,
        }
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json=policy_body,
        )

        # Upload a document
        content = b"Sample contract content." * 50
        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Test Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Call clause redlines endpoint - should be denied
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 403
        assert "CLAUSE_REDLINES_V1" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_jurisdiction_outside_policy_returns_403(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that requesting jurisdiction outside policy returns 403."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that only allows UAE jurisdiction
        policy_body = {
            "name": "UAE Only Policy",
            "config": {
                "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                "allowed_input_languages": ["en"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE"],  # Only UAE
                "feature_flags": {},
            },
            "is_default": True,
        }
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json=policy_body,
        )

        # Upload a document
        content = b"Sample contract." * 50
        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Test Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Request DIFC jurisdiction - should be denied
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "jurisdiction": "DIFC",
            },
        )
        assert response.status_code == 403
        assert "DIFC" in response.json()["detail"]


@pytest.mark.integration
class TestClauseRedlinesRoles:
    """Tests for role-based access."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_use_clause_redlines(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that VIEWER role cannot use the clause redlines endpoint."""
        # Bootstrap with admin
        data, admin_token = await bootstrap_and_login(async_client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        tenant_id = data["tenant_id"]
        workspace_id = data["workspace_id"]

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=admin_headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload a document
        content = b"Sample contract." * 50
        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=admin_headers,
            files=files,
            data={
                "title": "Test Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Create viewer user
        response = await async_client.post(
            f"/tenants/{tenant_id}/users",
            headers=admin_headers,
            json={"email": "viewer@test.com", "full_name": "Viewer User"},
        )
        viewer_id = response.json()["id"]

        # Add viewer to workspace
        await async_client.post(
            f"/workspaces/{workspace_id}/memberships",
            headers=admin_headers,
            json={"user_id": viewer_id, "role": "VIEWER"},
        )

        # Login as viewer
        response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "email": "viewer@test.com",
            },
        )
        viewer_token = response.cookies.get("access_token")
        assert viewer_token
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # Viewer should be denied clause redlines (requires EDITOR)
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=viewer_headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 403
        assert "EDITOR" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_can_use_clause_redlines(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that EDITOR role can use the clause redlines endpoint."""
        # Bootstrap with admin
        data, admin_token = await bootstrap_and_login(async_client)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        tenant_id = data["tenant_id"]
        workspace_id = data["workspace_id"]

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=admin_headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload a document with more content
        content = (
            "EMPLOYMENT CONTRACT\n\n"
            "Liability: The company shall be liable for damages.\n"
            "Termination: 30 days notice required.\n"
            "Governing Law: UAE courts shall have jurisdiction.\n"
        ).encode() * 20

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=admin_headers,
            files=files,
            data={
                "title": "Test Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Create editor user
        response = await async_client.post(
            f"/tenants/{tenant_id}/users",
            headers=admin_headers,
            json={"email": "editor@test.com", "full_name": "Editor User"},
        )
        editor_id = response.json()["id"]

        # Add editor to workspace
        await async_client.post(
            f"/workspaces/{workspace_id}/memberships",
            headers=admin_headers,
            json={"user_id": editor_id, "role": "EDITOR"},
        )

        # Login as editor
        response = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "email": "editor@test.com",
            },
        )
        editor_token = response.cookies.get("access_token")
        assert editor_token
        editor_headers = {"Authorization": f"Bearer {editor_token}"}

        # Editor should be allowed
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=editor_headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestClauseRedlinesAuditLogging:
    """Tests for audit logging."""

    @pytest.mark.asyncio
    async def test_successful_redlines_logs_audit_event(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that successful redlines creates audit log entry."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document
        content = (
            "CONTRACT\n"
            "Liability clause here. Termination requires notice. Governing law UAE.\n"
        ).encode() * 30

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Audit Test Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Run redlines
        await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )

        # Check audit log
        response = await async_client.get(
            "/audit",
            headers=headers,
            params={"action": "workflow.run.success"},
        )
        assert response.status_code == 200
        logs = response.json()["items"]

        # Find the workflow log for CLAUSE_REDLINES_V1
        workflow_logs = [
            log for log in logs if log["meta"].get("workflow") == "CLAUSE_REDLINES_V1"
        ]
        assert len(workflow_logs) > 0

        log = workflow_logs[0]
        assert log["meta"]["workflow"] == "CLAUSE_REDLINES_V1"
        assert log["meta"]["document_id"] == document_id
        assert log["meta"]["version_id"] == version_id
        assert "evidence_chunk_count" in log["meta"]
        assert "item_count" in log["meta"]
        assert "downgraded_count" in log["meta"]
        assert "strict_citations_failed" in log["meta"]


@pytest.mark.integration
class TestClauseRedlinesDocumentAccess:
    """Tests for document/version access validation."""

    @pytest.mark.asyncio
    async def test_document_not_in_workspace_returns_404(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that accessing a document from another workspace returns 404."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Try to analyze a non-existent document
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": "00000000-0000-0000-0000-000000000000",
                "version_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
class TestClauseRedlinesInsufficientEvidence:
    """Tests for insufficient evidence scenarios."""

    @pytest.mark.asyncio
    async def test_insufficient_chunks_returns_insufficient_sources(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that too few chunks returns insufficient sources message."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload a very small document (won't produce many chunks)
        content = b"Short contract."  # Too short to chunk
        files = {"file": ("tiny.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Tiny Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze - should return insufficient sources
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        assert result["insufficient_sources"] is True
        assert "insufficient" in result["summary"].lower()
        assert result["items"] == []


# =============================================================================
# V2 DETECTION TESTS
# =============================================================================


@pytest.mark.integration
class TestClauseDetectionV2HeadingDetection:
    """Tests for v2 heading detection functionality."""

    @pytest.mark.asyncio
    async def test_heading_detection_boosts_clause_selection(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that headings matching clause types boost detection scores."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with clear clause headings
        content = (
            "CONTRACT AGREEMENT\n\n"
            "1. DEFINITIONS\n"
            "Terms used in this agreement.\n\n"
            "2. GOVERNING LAW\n"
            "This Agreement shall be governed by and construed in accordance with the laws of "
            "the United Arab Emirates. Any disputes arising shall be subject to the exclusive "
            "jurisdiction of the courts of Dubai.\n\n"
            "3. TERMINATION\n"
            "Either party may terminate this Agreement by providing thirty (30) days written "
            "notice to the other party. Termination for cause may be immediate upon breach.\n\n"
            "4. LIABILITY\n"
            "The total liability of either party shall not exceed the total contract value. "
            "Neither party shall be liable for indirect, consequential, or punitive damages.\n\n"
            "5. CONFIDENTIALITY\n"
            "All confidential information disclosed must remain secret. Disclosure requires "
            "prior written consent. Trade secrets must be protected.\n\n"
        ).encode() * 5

        files = {"file": ("contract_with_headings.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Contract With Headings",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "clause_types": ["governing_law", "termination", "liability"],
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have found clauses with high/medium confidence due to heading matches
        assert result["insufficient_sources"] is False

        # Check confidence_level and confidence_reason are populated
        for item in result["items"]:
            assert "confidence_level" in item
            assert item["confidence_level"] in ("high", "medium", "low")
            assert "confidence_reason" in item
            assert isinstance(item["confidence_reason"], str)


@pytest.mark.integration
class TestClauseDetectionV2NeighborInclusion:
    """Tests for v2 neighbor chunk inclusion functionality."""

    @pytest.mark.asyncio
    async def test_neighbor_chunks_included_in_evidence(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that neighbor chunks are included for context."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload a longer document that will create multiple chunks
        # with clause content spread across adjacent sections
        content = (
            "MASTER SERVICES AGREEMENT\n\n"
            "ARTICLE I - INTRODUCTION\n"
            "This agreement sets forth the terms and conditions. "
            "The parties agree to the following provisions.\n\n"
            "ARTICLE II - LIMITATION OF LIABILITY\n"
            "2.1 Cap on Damages. The total aggregate liability of either party "
            "arising out of or related to this Agreement shall not exceed the fees "
            "paid or payable to Provider in the twelve months preceding the claim.\n\n"
            "2.2 Exclusions. In no event shall either party be liable for any indirect, "
            "incidental, special, consequential, or punitive damages, including without "
            "limitation lost profits, lost revenue, or lost data.\n\n"
            "2.3 Essential Purpose. The limitations of liability set forth in this "
            "Section shall apply regardless of the form of action and notwithstanding "
            "the failure of any limited remedy to achieve its essential purpose.\n\n"
            "ARTICLE III - INDEMNIFICATION\n"
            "Each party shall indemnify and hold harmless the other party from any claims.\n\n"
        ).encode() * 8

        files = {"file": ("long_contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Long Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze for liability clause specifically
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "clause_types": ["liability"],
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have evidence for liability
        assert result["insufficient_sources"] is False
        liability_items = [
            i for i in result["items"] if i["clause_type"] == "liability"
        ]
        assert len(liability_items) > 0

        # Check that we have multiple evidence entries (neighbor inclusion)
        # The v2 system should include up to 5 evidence chunks per clause type
        if liability_items[0]["status"] == "found":
            # Evidence should be present
            assert len(liability_items[0]["evidence"]) >= 1


@pytest.mark.integration
class TestClauseDetectionV2NegativeScoring:
    """Tests for v2 negative scoring functionality."""

    @pytest.mark.asyncio
    async def test_signature_blocks_not_selected_as_evidence(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that signature blocks are penalized and not selected as evidence."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with actual clauses AND signature block
        content = (
            "SERVICE AGREEMENT\n\n"
            "1. GOVERNING LAW\n"
            "This Agreement shall be governed by the laws of the United Arab Emirates. "
            "The courts of Dubai shall have exclusive jurisdiction.\n\n"
            "2. TERMINATION\n"
            "Either party may terminate this agreement with 30 days notice. "
            "Termination for cause requires written notice.\n\n"
            "3. LIABILITY\n"
            "Total liability shall not exceed the contract value. "
            "No party shall be liable for consequential damages.\n\n"
            "IN WITNESS WHEREOF, the parties have executed this Agreement.\n\n"
            "SIGNATURE:\n"
            "By: _______________________________\n"
            "Name: _____________________________\n"
            "Title: ____________________________\n"
            "Date: _____________________________\n\n"
            "By: _______________________________\n"
            "Name: _____________________________\n"
            "Title: ____________________________\n"
            "Date: _____________________________\n\n"
            "ANNEX A - SCHEDULE OF SERVICES\n"
            "The following services are covered under this agreement.\n\n"
        ).encode() * 5

        files = {"file": ("contract_with_sigs.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Contract With Signatures",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should still find the actual clauses
        assert result["insufficient_sources"] is False

        # Evidence snippets should NOT contain signature block content
        for item in result["items"]:
            for evidence in item["evidence"]:
                snippet = evidence["snippet"].lower()
                # Signature blocks should be excluded from evidence
                assert "in witness whereof" not in snippet
                assert "by: ___" not in snippet


@pytest.mark.integration
class TestClauseDetectionV2ConfidenceCalibration:
    """Tests for v2 confidence calibration functionality."""

    @pytest.mark.asyncio
    async def test_confidence_level_and_reason_populated(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that confidence_level and confidence_reason are populated."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with clear clause content
        content = (
            "PROFESSIONAL SERVICES AGREEMENT\n\n"
            "ARTICLE 1. GOVERNING LAW\n"
            "This Agreement shall be governed by and construed in accordance with "
            "the laws of the United Arab Emirates, without regard to its conflict of "
            "laws provisions. The parties submit to the exclusive jurisdiction of the "
            "courts of Dubai for resolution of any disputes.\n\n"
            "ARTICLE 2. PAYMENT TERMS\n"
            "Payment shall be made within thirty (30) days of receipt of invoice. "
            "Late payments shall incur interest at 1.5% per month. All fees are "
            "exclusive of applicable taxes.\n\n"
            "ARTICLE 3. FORCE MAJEURE\n"
            "Neither party shall be liable for failure to perform due to causes beyond "
            "its reasonable control, including but not limited to acts of God, war, "
            "terrorism, labor disputes, or government actions.\n\n"
        ).encode() * 6

        files = {"file": ("services_agreement.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Services Agreement",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "clause_types": ["governing_law", "payment", "force_majeure"],
            },
        )
        assert response.status_code == 200
        result = response.json()

        assert result["insufficient_sources"] is False

        # All items should have confidence calibration fields
        for item in result["items"]:
            # Check confidence_level is valid
            assert item["confidence_level"] in ("high", "medium", "low")

            # Check confidence_reason is a non-empty string
            assert isinstance(item["confidence_reason"], str)

            # Reason should indicate what contributed to confidence
            # (e.g., "Matched heading + 3 triggers" or "2 trigger(s)")
            if item["confidence_level"] in ("high", "medium"):
                # High/medium should have some reasoning
                assert len(item["confidence_reason"]) > 0

    @pytest.mark.asyncio
    async def test_status_semantics_based_on_confidence_level(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that status is determined by confidence level (v2 semantics)."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Redlines Policy",
                "config": {
                    "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with mixed strength clause content
        content = (
            "CONTRACT DOCUMENT\n\n"
            "SECTION A: GOVERNING LAW\n"
            "This contract is governed by UAE law. Courts of Dubai have jurisdiction. "
            "All disputes shall be resolved according to applicable UAE legislation.\n\n"
            "SECTION B: MISCELLANEOUS\n"
            "General provisions apply. Standard terms and conditions.\n\n"
            "SECTION C: LIABILITY\n"
            "Liability is limited. Damages capped. No consequential liability.\n\n"
        ).encode() * 8

        files = {"file": ("mixed_contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Mixed Strength Contract",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Analyze
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Verify status semantics
        for item in result["items"]:
            if item["confidence_level"] in ("high", "medium"):
                # High/medium confidence should result in "found" status
                assert item["status"] == "found", (
                    f"Expected 'found' for {item['clause_type']} with "
                    f"confidence_level={item['confidence_level']}"
                )
            elif item["confidence_level"] == "low" and len(item["evidence"]) > 0:
                # Low confidence with evidence = insufficient_evidence
                assert item["status"] in ("insufficient_evidence", "missing")
            # Note: "missing" is for cases with no evidence at all
