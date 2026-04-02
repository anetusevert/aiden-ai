"""Tests for Contract Review workflow (CONTRACT_REVIEW_V1).

Tests cover:
1. Happy path: returns JSON with 2 findings with valid citations
2. Invalid citations: findings removed -> removed_findings_count > 0
3. Uncited summary: triggers regenerated summary
4. Policy disallows workflow -> 403
5. Role enforcement: VIEWER gets 403, EDITOR allowed
6. Audit log entry created
7. Document/version access validation
"""

import pytest
from httpx import AsyncClient

from tests.helpers import bootstrap_and_login


@pytest.mark.integration
class TestContractReviewHappyPath:
    """Tests for successful contract review scenarios."""

    @pytest.mark.asyncio
    async def test_contract_review_returns_findings_with_citations(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that contract review returns properly cited findings."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that allows CONTRACT_REVIEW_V1
        policy_body = {
            "name": "Contract Review Policy",
            "config": {
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
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

        # Upload a contract document with enough content for chunks
        content = (
            "EMPLOYMENT AGREEMENT\n\n"
            "This Employment Agreement (the 'Agreement') is entered into as of the date below.\n\n"
            "1. TERM AND TERMINATION\n"
            "The Employee may terminate this Agreement by providing 30 days written notice.\n"
            "The Employer may terminate for cause without notice.\n"
            "Termination shall be effective upon the date specified in the notice.\n\n"
            "2. LIABILITY\n"
            "The Employer's liability under this Agreement shall not exceed the total contract value.\n"
            "Neither party shall be liable for consequential damages.\n"
            "This limitation of liability shall survive termination.\n\n"
            "3. GOVERNING LAW\n"
            "This Agreement shall be governed by the laws of the United Arab Emirates.\n"
            "Any disputes shall be resolved through arbitration in Dubai.\n"
            "The parties submit to the jurisdiction of UAE courts.\n\n"
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

        # Call contract review endpoint
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "review_mode": "standard",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have findings with citations
        assert result["insufficient_sources"] is False
        assert len(result["findings"]) > 0
        assert "[1]" in result["summary"] or "[2]" in result["summary"]

        # Check finding structure
        finding = result["findings"][0]
        assert "title" in finding
        assert "severity" in finding
        assert "category" in finding
        assert "issue" in finding
        assert "recommendation" in finding
        assert "citations" in finding
        assert len(finding["citations"]) > 0

        # Check meta
        assert result["meta"]["provider"] == "stub"
        assert result["meta"]["evidence_chunk_count"] >= 3
        assert result["meta"]["strict_citations_failed"] is False

    @pytest.mark.asyncio
    async def test_contract_review_with_playbook_hint(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that contract review accepts playbook_hint parameter."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document
        content = (
            "CONTRACT TERMS\n\n"
            "Payment shall be made within 30 days of invoice.\n"
            "Liability is limited to the contract value.\n"
            "Governing law is UAE.\n"
        ).encode() * 20

        files = {"file": ("terms.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Terms Document",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Review with playbook_hint
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "review_mode": "quick",
                "focus_areas": ["liability", "payment"],
                "playbook_hint": "Prioritize UAE governing law and DIFC considerations.",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should complete successfully with hint
        assert result["insufficient_sources"] is False
        assert result["meta"]["review_mode"] == "quick"

    @pytest.mark.asyncio
    async def test_contract_review_with_focus_areas(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that contract review respects focus areas."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document
        content = (
            "CONTRACT TERMS\n\n"
            "Payment shall be made within 30 days of invoice.\n"
            "Liability is limited to the contract value.\n"
            "Confidential information must be protected.\n"
        ).encode() * 20

        files = {"file": ("terms.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Terms Document",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Review with focus areas
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "review_mode": "quick",
                "focus_areas": ["liability", "payment"],
            },
        )
        assert response.status_code == 200
        result = response.json()

        assert result["insufficient_sources"] is False
        assert result["meta"]["review_mode"] == "quick"


@pytest.mark.integration
class TestContractReviewStrictCitations:
    """Tests for strict citation enforcement."""

    @pytest.mark.asyncio
    async def test_invalid_citations_removed(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that findings with invalid citations are removed."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with test marker in title to trigger test mode
        content = (
            "[TEST:CONTRACT_INVALID_CITATIONS]\n"
            "CONTRACT TERMS\n\n"
            "Liability shall be limited. Termination requires notice.\n"
        ).encode() * 20

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Test Contract [TEST:CONTRACT_INVALID_CITATIONS]",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Review
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have removed some findings
        meta = result["meta"]
        assert meta["removed_findings_count"] >= 1

        # The valid finding should remain
        if result["findings"]:
            for finding in result["findings"]:
                # All remaining findings should have valid citations
                assert len(finding["citations"]) > 0
                for cite in finding["citations"]:
                    assert cite <= meta["evidence_chunk_count"]

    @pytest.mark.asyncio
    async def test_uncited_summary_regenerated(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that uncited summary is regenerated from findings."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload document with test marker for no-summary-citation mode
        content = (
            "[TEST:CONTRACT_NO_SUMMARY_CITATION]\n"
            "CONTRACT PROVISIONS\n\n"
            "The liability is capped at 100,000 USD.\n"
            "Payment terms require net 30 payment.\n"
        ).encode() * 20

        files = {"file": ("contract.txt", content, "text/plain")}
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "Test Contract [TEST:CONTRACT_NO_SUMMARY_CITATION]",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )
        doc_result = response.json()
        document_id = doc_result["document"]["id"]
        version_id = doc_result["version"]["id"]

        # Review
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Summary should contain citations (regenerated)
        assert "[1]" in result["summary"] or "[2]" in result["summary"]

        # Validation warnings should mention regeneration
        meta = result["meta"]
        if meta["validation_warnings"]:
            warning_text = " ".join(meta["validation_warnings"])
            assert "regenerated" in warning_text.lower() or "summary" in warning_text.lower()


@pytest.mark.integration
class TestContractReviewPolicyEnforcement:
    """Tests for policy enforcement."""

    @pytest.mark.asyncio
    async def test_policy_disallows_workflow_returns_403(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that policy denying CONTRACT_REVIEW_V1 returns 403."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that does NOT allow CONTRACT_REVIEW_V1
        policy_body = {
            "name": "No Review Policy",
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

        # Call contract review endpoint - should be denied
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 403
        assert "CONTRACT_REVIEW_V1" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_output_language_outside_policy_returns_403(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that requesting an output language outside policy returns 403."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that only allows English output
        policy_body = {
            "name": "English Only Policy",
            "config": {
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en"],  # Only English
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

        # Request Arabic output - should be denied
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "output_language": "ar",
            },
        )
        assert response.status_code == 403
        assert "ar" in response.json()["detail"]


@pytest.mark.integration
class TestContractReviewRoles:
    """Tests for role-based access."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_use_contract_review(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that VIEWER role cannot use the contract review endpoint."""
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
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
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

        # Viewer should be denied contract review (requires EDITOR)
        response = await async_client.post(
            "/workflows/contract-review",
            headers=viewer_headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 403
        assert "EDITOR" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_editor_can_use_contract_review(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that EDITOR role can use the contract review endpoint."""
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
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
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
            "/workflows/contract-review",
            headers=editor_headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
            },
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestContractReviewAuditLogging:
    """Tests for audit logging."""

    @pytest.mark.asyncio
    async def test_successful_review_logs_audit_event(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that successful review creates audit log entry."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
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
            "Liability clause here. Termination requires notice.\n"
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

        # Run review
        await async_client.post(
            "/workflows/contract-review",
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

        # Find the workflow log for CONTRACT_REVIEW_V1
        workflow_logs = [
            log for log in logs if log["meta"].get("workflow") == "CONTRACT_REVIEW_V1"
        ]
        assert len(workflow_logs) > 0

        log = workflow_logs[0]
        assert log["meta"]["workflow"] == "CONTRACT_REVIEW_V1"
        assert log["meta"]["document_id"] == document_id
        assert log["meta"]["version_id"] == version_id
        assert "evidence_chunk_count" in log["meta"]
        assert "removed_findings_count" in log["meta"]
        assert "strict_citations_failed" in log["meta"]


@pytest.mark.integration
class TestContractReviewDocumentAccess:
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
        tenant_id = data["tenant_id"]

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Try to review a non-existent document
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": "00000000-0000-0000-0000-000000000000",
                "version_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_version_not_found_returns_404(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that accessing a non-existent version returns 404."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
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

        # Try to review with wrong version ID
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert response.status_code == 404
        assert "version" in response.json()["detail"].lower()


@pytest.mark.integration
class TestContractReviewInsufficientEvidence:
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
                "name": "Review Policy",
                "config": {
                    "allowed_workflows": ["CONTRACT_REVIEW_V1"],
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

        # Review - should return insufficient sources
        response = await async_client.post(
            "/workflows/contract-review",
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
        assert result["findings"] == []
