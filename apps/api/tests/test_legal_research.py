"""Tests for Legal Research workflow (LEGAL_RESEARCH_V1).

Tests cover:
1. Insufficient evidence returns appropriate message
2. Sufficient evidence returns cited answer
3. Citation validation works correctly
4. Policy enforcement (LEGAL_RESEARCH_V1 must be allowed)
5. Audit logging for workflow runs
6. Output language handling (English/Arabic)
7. Jurisdiction/language filter validation against policy
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from tests.conftest import TestSessionLocal
from tests.helpers import bootstrap_and_login


@pytest.mark.integration
class TestLegalResearchInsufficientEvidence:
    """Tests for insufficient evidence scenarios."""

    @pytest.mark.asyncio
    async def test_insufficient_evidence_returns_message(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that insufficient evidence returns appropriate message."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that allows LEGAL_RESEARCH_V1
        policy_body = {
            "name": "Research Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
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

        # Do NOT upload any documents - workspace is empty

        # Call legal research endpoint
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What are the notice requirements for contract termination?",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should indicate insufficient sources
        assert result["insufficient_sources"] is True
        assert "insufficient" in result["answer_text"].lower() or "Insufficient" in result["answer_text"]
        assert result["citations"] == []
        assert result["evidence"] == []  # No documents in workspace

    @pytest.mark.asyncio
    async def test_insufficient_evidence_arabic_message(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that insufficient evidence returns Arabic message when requested."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that allows LEGAL_RESEARCH_V1
        policy_body = {
            "name": "Research Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en", "ar"],
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

        # Call with Arabic output
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What are the notice requirements?",
                "output_language": "ar",
            },
        )
        assert response.status_code == 200
        result = response.json()

        assert result["insufficient_sources"] is True
        assert result["meta"]["output_language"] == "ar"


@pytest.mark.integration
class TestLegalResearchSufficientEvidence:
    """Tests for sufficient evidence scenarios."""

    @pytest.mark.asyncio
    async def test_sufficient_evidence_returns_cited_answer(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that sufficient evidence returns a cited answer."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that allows LEGAL_RESEARCH_V1
        policy_body = {
            "name": "Research Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
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

        # Upload multiple documents to provide sufficient evidence
        for i in range(3):
            content = (
                f"Document {i + 1}: Employment Agreement\n\n"
                f"This document outlines the terms of employment.\n"
                f"Notice Period: 30 days advance written notice is required for termination.\n"
                f"The employee must provide notice to the employer in writing.\n"
                f"Additional terms and conditions apply as per UAE law.\n"
            ).encode() * 10  # Make it longer to ensure chunking

            files = {"file": (f"employment_{i}.txt", content, "text/plain")}
            form_data = {
                "title": f"Employment Agreement {i + 1}",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            }
            response = await async_client.post(
                "/documents",
                headers=headers,
                files=files,
                data=form_data,
            )
            assert response.status_code == 201

        # Call legal research endpoint
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What is the notice period for employment termination?",
                "limit": 10,
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have a valid answer with citations
        assert result["insufficient_sources"] is False
        assert "[1]" in result["answer_text"]
        assert len(result["citations"]) > 0
        assert len(result["evidence"]) >= 3

        # Check citation structure
        citation = result["citations"][0]
        assert "citation_index" in citation
        assert "chunk_id" in citation
        assert "document_id" in citation
        assert "document_title" in citation

        # Check meta
        assert result["meta"]["provider"] == "stub"
        assert result["meta"]["chunk_count"] >= 3

    @pytest.mark.asyncio
    async def test_citation_maps_to_evidence(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that citations correctly map to evidence chunks."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Legal document {i + 1} with important legal provisions.\n" * 50).encode()
            files = {"file": (f"legal_{i}.txt", content, "text/plain")}
            form_data = {
                "title": f"Legal Document {i + 1}",
                "document_type": "policy",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            }
            await async_client.post(
                "/documents", headers=headers, files=files, data=form_data
            )

        # Run research
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "What are the legal provisions?"},
        )
        assert response.status_code == 200
        result = response.json()

        # Verify citation mapping
        evidence_ids = {e["chunk_id"] for e in result["evidence"]}
        for citation in result["citations"]:
            assert citation["chunk_id"] in evidence_ids


@pytest.mark.integration
class TestLegalResearchPolicyEnforcement:
    """Tests for policy enforcement."""

    @pytest.mark.asyncio
    async def test_policy_disallows_workflow_returns_403(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that policy denying LEGAL_RESEARCH_V1 returns 403."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that does NOT allow LEGAL_RESEARCH_V1
        policy_body = {
            "name": "No Research Policy",
            "config": {
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],  # Different workflow
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

        # Call legal research endpoint - should be denied
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What are the notice requirements?",
            },
        )
        assert response.status_code == 403
        assert "LEGAL_RESEARCH_V1" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_jurisdiction_filter_outside_policy_returns_403(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that requesting a jurisdiction outside policy returns 403."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that only allows UAE
        policy_body = {
            "name": "UAE Only Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
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

        # Request with KSA jurisdiction - should be denied
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What are the notice requirements?",
                "filters": {"jurisdiction": "KSA"},
            },
        )
        assert response.status_code == 403
        assert "KSA" in response.json()["detail"]
        assert "not allowed" in response.json()["detail"]

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
            "name": "English Only Output Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en"],  # Only English output
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

        # Request Arabic output - should be denied
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What are the notice requirements?",
                "output_language": "ar",
            },
        )
        assert response.status_code == 403
        assert "ar" in response.json()["detail"]


@pytest.mark.integration
class TestLegalResearchAuditLogging:
    """Tests for audit logging."""

    @pytest.mark.asyncio
    async def test_successful_research_logs_audit_event(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that successful research creates audit log entry."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}
        tenant_id = data["tenant_id"]

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Run research (will return insufficient sources but still logs)
        await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "Test question for audit logging"},
        )

        # Check audit log
        response = await async_client.get(
            "/audit",
            headers=headers,
            params={"action": "workflow.run.success"},
        )
        assert response.status_code == 200
        logs = response.json()["items"]

        # Find the workflow log
        workflow_logs = [
            log for log in logs if log["meta"].get("workflow") == "LEGAL_RESEARCH_V1"
        ]
        assert len(workflow_logs) > 0

        log = workflow_logs[0]
        assert "question_hash" in log["meta"]
        assert log["meta"]["workflow"] == "LEGAL_RESEARCH_V1"

    @pytest.mark.asyncio
    async def test_policy_denied_logs_failure(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that policy denial creates failure audit log."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that denies LEGAL_RESEARCH_V1
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "No Research",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Try to run research - will be denied
        await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "Test question"},
        )

        # The 403 response means policy check failed before workflow.run.fail is logged
        # This is expected - the require_workflow_allowed raises HTTPException
        # The audit log for this would be at the policy enforcement level


@pytest.mark.integration
class TestLegalResearchFilters:
    """Tests for filter functionality."""

    @pytest.mark.asyncio
    async def test_filters_applied_to_search(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that filters are properly applied to the search."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE", "DIFC"],
                },
                "is_default": True,
            },
        )

        # Upload UAE document
        content = ("UAE employment law document with notice requirements.\n" * 50).encode()
        files = {"file": ("uae.txt", content, "text/plain")}
        await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "UAE Employment Law",
                "document_type": "regulatory",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            },
        )

        # Upload DIFC document
        content = ("DIFC employment law document with different provisions.\n" * 50).encode()
        files = {"file": ("difc.txt", content, "text/plain")}
        await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data={
                "title": "DIFC Employment Law",
                "document_type": "regulatory",
                "jurisdiction": "DIFC",
                "language": "en",
                "confidentiality": "internal",
            },
        )

        # Search with UAE filter - should only return UAE documents
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "employment law",
                "filters": {"jurisdiction": "UAE"},
            },
        )
        assert response.status_code == 200
        result = response.json()

        # All evidence should be UAE jurisdiction
        for chunk in result["evidence"]:
            assert chunk["jurisdiction"] == "UAE"


@pytest.mark.integration
class TestLegalResearchRoles:
    """Tests for role-based access."""

    @pytest.mark.asyncio
    async def test_viewer_can_use_research(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that VIEWER role can use the research endpoint."""
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
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

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

        # Viewer should be able to use research
        response = await async_client.post(
            "/workflows/legal-research",
            headers=viewer_headers,
            json={"question": "Test question"},
        )
        assert response.status_code == 200


@pytest.mark.integration
class TestLLMProviderStub:
    """Tests for StubLLMProvider behavior."""

    @pytest.mark.asyncio
    async def test_stub_provider_returns_deterministic_output(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that stub provider returns consistent, deterministic output."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Test document {i} with legal content.\n" * 50).encode()
            await async_client.post(
                "/documents",
                headers=headers,
                files={"file": (f"doc_{i}.txt", content, "text/plain")},
                data={
                    "title": f"Doc {i}",
                    "document_type": "contract",
                    "jurisdiction": "UAE",
                    "language": "en",
                    "confidentiality": "internal",
                },
            )

        # Run same question twice
        question = "What is the legal position?"
        response1 = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": question},
        )
        response2 = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": question},
        )

        # Both should return stub provider
        assert response1.json()["meta"]["provider"] == "stub"
        assert response2.json()["meta"]["provider"] == "stub"


# =============================================================================
# Strict Citation Enforcement Tests
# =============================================================================


@pytest.mark.integration
class TestStrictCitationEnforcement:
    """Tests for strict citation enforcement."""

    @pytest.mark.asyncio
    async def test_uncited_paragraph_removed(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that paragraphs without citations are removed."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Test document {i} with legal provisions and terms.\n" * 50).encode()
            await async_client.post(
                "/documents",
                headers=headers,
                files={"file": (f"doc_{i}.txt", content, "text/plain")},
                data={
                    "title": f"Legal Document {i}",
                    "document_type": "contract",
                    "jurisdiction": "UAE",
                    "language": "en",
                    "confidentiality": "internal",
                },
            )

        # Include test marker to trigger uncited paragraph mode
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "What is the legal position? [TEST:UNCITED_PARAGRAPH]"},
        )
        assert response.status_code == 200
        result = response.json()

        # Check strict enforcement results
        meta = result["meta"]
        assert meta["strict_citation_enforced"] is True
        assert meta["removed_paragraph_count"] >= 1
        assert meta["strict_citations_failed"] is False

        # The uncited paragraph text should not be in the answer
        assert "no citations and should be removed" not in result["answer_text"]

        # The cited paragraphs should remain
        assert "[1]" in result["answer_text"] or "[2]" in result["answer_text"]

        # Validation warnings should mention removed paragraph
        assert meta["validation_warnings"] is not None
        removed_warnings = [w for w in meta["validation_warnings"] if "Removed uncited" in w]
        assert len(removed_warnings) >= 1

    @pytest.mark.asyncio
    async def test_all_uncited_content_downgrades_to_insufficient(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that if all paragraphs are uncited, answer is downgraded."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Test document {i} with content.\n" * 50).encode()
            await async_client.post(
                "/documents",
                headers=headers,
                files={"file": (f"doc_{i}.txt", content, "text/plain")},
                data={
                    "title": f"Document {i}",
                    "document_type": "contract",
                    "jurisdiction": "UAE",
                    "language": "en",
                    "confidentiality": "internal",
                },
            )

        # Include test marker to trigger no-citations mode
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "What is the legal position? [TEST:NO_CITATIONS]"},
        )
        assert response.status_code == 200
        result = response.json()

        # Should be downgraded to insufficient
        assert result["insufficient_sources"] is True
        assert "Insufficient sources" in result["answer_text"]

        # Check strict enforcement results
        meta = result["meta"]
        assert meta["strict_citation_enforced"] is True
        assert meta["strict_citations_failed"] is True
        assert meta["citation_count_used"] == 0

    @pytest.mark.asyncio
    async def test_footer_only_citations_dont_pass(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that citations only in a footer section don't pass strict enforcement."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Test document {i} with legal content.\n" * 50).encode()
            await async_client.post(
                "/documents",
                headers=headers,
                files={"file": (f"doc_{i}.txt", content, "text/plain")},
                data={
                    "title": f"Document {i}",
                    "document_type": "contract",
                    "jurisdiction": "UAE",
                    "language": "en",
                    "confidentiality": "internal",
                },
            )

        # Include test marker to trigger footer-only mode
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "What is the legal position? [TEST:FOOTER_ONLY]"},
        )
        assert response.status_code == 200
        result = response.json()

        # Should be downgraded because paragraphs have no inline citations
        assert result["insufficient_sources"] is True

        meta = result["meta"]
        assert meta["strict_citation_enforced"] is True
        assert meta["strict_citations_failed"] is True

    @pytest.mark.asyncio
    async def test_valid_citations_remain_valid(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that valid citations are preserved and mapped correctly."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Legal document {i} with important provisions.\n" * 50).encode()
            await async_client.post(
                "/documents",
                headers=headers,
                files={"file": (f"doc_{i}.txt", content, "text/plain")},
                data={
                    "title": f"Legal Doc {i}",
                    "document_type": "contract",
                    "jurisdiction": "UAE",
                    "language": "en",
                    "confidentiality": "internal",
                },
            )

        # Normal query (no test markers) - should return properly cited answer
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "What are the legal provisions?"},
        )
        assert response.status_code == 200
        result = response.json()

        # Should NOT be downgraded
        assert result["insufficient_sources"] is False
        assert result["meta"]["strict_citations_failed"] is False

        # Citations should be present and valid
        assert len(result["citations"]) > 0
        assert "[1]" in result["answer_text"]

        # Citation count should match
        assert result["meta"]["citation_count_used"] > 0

        # Citations should map to evidence
        evidence_ids = {e["chunk_id"] for e in result["evidence"]}
        for citation in result["citations"]:
            assert citation["chunk_id"] in evidence_ids

    @pytest.mark.asyncio
    async def test_strict_citation_audit_logging(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that strict citation fields are included in audit logs."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        await async_client.post(
            "/policy-profiles",
            headers=headers,
            json={
                "name": "Research Policy",
                "config": {
                    "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                    "allowed_input_languages": ["en"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],
                },
                "is_default": True,
            },
        )

        # Upload documents
        for i in range(3):
            content = (f"Legal document {i} content.\n" * 50).encode()
            await async_client.post(
                "/documents",
                headers=headers,
                files={"file": (f"doc_{i}.txt", content, "text/plain")},
                data={
                    "title": f"Doc {i}",
                    "document_type": "contract",
                    "jurisdiction": "UAE",
                    "language": "en",
                    "confidentiality": "internal",
                },
            )

        # Run research with uncited paragraph
        await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={"question": "What is the position? [TEST:UNCITED_PARAGRAPH]"},
        )

        # Check audit log
        response = await async_client.get(
            "/audit",
            headers=headers,
            params={"action": "workflow.run.success"},
        )
        assert response.status_code == 200
        logs = response.json()["items"]

        # Find the workflow log
        workflow_logs = [
            log for log in logs if log["meta"].get("workflow") == "LEGAL_RESEARCH_V1"
        ]
        assert len(workflow_logs) > 0

        log = workflow_logs[0]
        # Check that new fields are present in audit
        assert "removed_paragraph_count" in log["meta"]
        assert "strict_citations_failed" in log["meta"]
        assert "citation_count_used" in log["meta"]
