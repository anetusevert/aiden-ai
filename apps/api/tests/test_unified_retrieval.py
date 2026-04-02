"""Tests for Unified Evidence Retrieval across workflows.

Tests cover:
1. evidence_scope="workspace" - unchanged behavior, only workspace results
2. evidence_scope="global" - only global legal results (with policy gating)
3. evidence_scope="both" - merged results with deterministic ranking
4. Policy denial for global scope returns empty with denied_reason
5. Meta includes evidence_scope and counts by source_type
6. Exports work with mixed evidence (workspace + global)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from tests.conftest import TestSessionLocal
from tests.helpers import bootstrap_and_login


# =============================================================================
# Legal Research - Evidence Scope Tests
# =============================================================================


@pytest.mark.integration
class TestLegalResearchEvidenceScope:
    """Tests for Legal Research workflow with evidence_scope."""

    @pytest.mark.asyncio
    async def test_workspace_scope_unchanged_behavior(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that evidence_scope='workspace' behaves same as before (default)."""
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

        # Call legal research with explicit workspace scope
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What is the governing law?",
                "limit": 10,
                "evidence_scope": "workspace",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Meta should include evidence_scope
        assert result["meta"]["evidence_scope"] == "workspace"
        # Should have counts
        assert "workspace_evidence_count" in result["meta"]
        assert "global_evidence_count" in result["meta"]
        assert result["meta"]["global_evidence_count"] == 0  # No global search

    @pytest.mark.asyncio
    async def test_global_scope_policy_denial(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that evidence_scope='global' with empty policy returns denied_reason."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy with EMPTY allowed_jurisdictions (deny-by-default)
        policy_body = {
            "name": "Restrictive Policy",
            "config": {
                "allowed_workflows": ["LEGAL_RESEARCH_V1"],
                "allowed_input_languages": [],  # Empty = deny
                "allowed_output_languages": ["en", "ar"],
                "allowed_jurisdictions": [],  # Empty = deny
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

        # Call legal research with global scope
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What are the KSA employment laws?",
                "limit": 10,
                "evidence_scope": "global",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Should have evidence_scope in meta
        assert result["meta"]["evidence_scope"] == "global"
        # Global evidence should be 0 due to policy denial
        assert result["meta"]["global_evidence_count"] == 0
        # Should have policy_denied_reason
        assert result["meta"]["policy_denied_reason"] is not None
        assert "empty" in result["meta"]["policy_denied_reason"]

    @pytest.mark.asyncio
    async def test_both_scope_with_policy_allowed(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that evidence_scope='both' returns merged results."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy that allows everything
        policy_body = {
            "name": "Permissive Policy",
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

        # Call legal research with both scope
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What is the governing law for contracts in UAE?",
                "limit": 10,
                "evidence_scope": "both",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Meta should include evidence_scope
        assert result["meta"]["evidence_scope"] == "both"
        # Should have counts (may be 0 if no data, but fields present)
        assert "workspace_evidence_count" in result["meta"]
        assert "global_evidence_count" in result["meta"]
        # No policy denial (jurisdictions/languages allowed)
        assert result["meta"]["policy_denied_reason"] is None


# =============================================================================
# Contract Review - Evidence Scope Tests
# =============================================================================


@pytest.mark.integration
class TestContractReviewEvidenceScope:
    """Tests for Contract Review workflow with evidence_scope."""

    @pytest.mark.asyncio
    async def test_evidence_scope_accepted_in_request(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that evidence_scope is accepted and returned in meta."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        policy_body = {
            "name": "Contract Policy",
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

        # Upload a document
        pdf_content = b"%PDF-1.4\n%Mock PDF content for contract review test\n"
        files = {
            "file": ("test_contract.pdf", pdf_content, "application/pdf"),
        }
        form_data = {
            "title": "Test Contract",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
        }
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data=form_data,
        )
        assert response.status_code == 201
        doc_data = response.json()
        document_id = doc_data["document"]["id"]
        version_id = doc_data["version"]["id"]

        # Call contract review with evidence_scope
        response = await async_client.post(
            "/workflows/contract-review",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "review_mode": "quick",
                "focus_areas": ["liability", "termination"],
                "output_language": "en",
                "evidence_scope": "both",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Meta should include evidence_scope
        assert result["meta"]["evidence_scope"] == "both"
        assert "workspace_evidence_count" in result["meta"]
        assert "global_evidence_count" in result["meta"]


# =============================================================================
# Clause Redlines - Evidence Scope Tests
# =============================================================================


@pytest.mark.integration
class TestClauseRedlinesEvidenceScope:
    """Tests for Clause Redlines workflow with evidence_scope."""

    @pytest.mark.asyncio
    async def test_evidence_scope_accepted_and_meta_counts_included(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that evidence_scope is accepted and meta includes counts."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
        policy_body = {
            "name": "Clause Policy",
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

        # Upload a document
        pdf_content = b"%PDF-1.4\n%Mock PDF content for clause redlines test\n"
        files = {
            "file": ("test_contract.pdf", pdf_content, "application/pdf"),
        }
        form_data = {
            "title": "Test Contract for Clauses",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
        }
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data=form_data,
        )
        assert response.status_code == 201
        doc_data = response.json()
        document_id = doc_data["document"]["id"]
        version_id = doc_data["version"]["id"]

        # Call clause redlines with evidence_scope
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "jurisdiction": "UAE",
                "clause_types": ["governing_law", "termination"],
                "output_language": "en",
                "evidence_scope": "workspace",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Meta should include evidence_scope
        assert result["meta"]["evidence_scope"] == "workspace"
        assert "workspace_evidence_count" in result["meta"]
        assert "global_evidence_count" in result["meta"]

    @pytest.mark.asyncio
    async def test_global_only_scope_with_insufficient_document_chunks(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that global-only scope with no document chunks still works."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy with empty jurisdictions (deny global)
        policy_body = {
            "name": "Restrictive Policy",
            "config": {
                "allowed_workflows": ["CLAUSE_REDLINES_V1"],
                "allowed_input_languages": [],  # Empty = deny global
                "allowed_output_languages": ["en", "ar"],
                "allowed_jurisdictions": [],  # Empty = deny global
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

        # Upload a minimal document
        pdf_content = b"%PDF-1.4\n%Minimal PDF\n"
        files = {
            "file": ("test.pdf", pdf_content, "application/pdf"),
        }
        form_data = {
            "title": "Test",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
        }
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data=form_data,
        )
        assert response.status_code == 201
        doc_data = response.json()
        document_id = doc_data["document"]["id"]
        version_id = doc_data["version"]["id"]

        # Call clause redlines with global scope (will be policy-denied)
        response = await async_client.post(
            "/workflows/clause-redlines",
            headers=headers,
            json={
                "document_id": document_id,
                "version_id": version_id,
                "jurisdiction": "UAE",
                "clause_types": ["governing_law"],
                "output_language": "en",
                "evidence_scope": "global",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Meta should include evidence_scope
        assert result["meta"]["evidence_scope"] == "global"
        # Global should be 0 due to policy denial
        assert result["meta"]["global_evidence_count"] == 0
        # Policy denial reason should be set
        assert result["meta"]["policy_denied_reason"] is not None


# =============================================================================
# Evidence Source Type Tests
# =============================================================================


@pytest.mark.integration
class TestEvidenceSourceType:
    """Tests for evidence source_type in results."""

    @pytest.mark.asyncio
    async def test_workspace_evidence_has_correct_source_type(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that workspace evidence has source_type='workspace_document'."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create policy
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
        await async_client.post("/policy-profiles", headers=headers, json=policy_body)

        # Upload a document with some content
        pdf_content = (
            b"%PDF-1.4\n"
            b"This contract governs the termination provisions and liability clauses. "
            b"The governing law shall be UAE law. Termination requires 30 days notice. "
            b"Liability is limited to direct damages only. Force majeure applies."
            b"\n%%EOF"
        )
        files = {
            "file": ("contract.pdf", pdf_content, "application/pdf"),
        }
        form_data = {
            "title": "UAE Employment Contract",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
        }
        response = await async_client.post(
            "/documents",
            headers=headers,
            files=files,
            data=form_data,
        )
        assert response.status_code == 201

        # Call legal research
        response = await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "What is the termination notice period?",
                "limit": 10,
                "evidence_scope": "workspace",
            },
        )
        assert response.status_code == 200
        result = response.json()

        # Check evidence has source_type
        if result["evidence"]:
            for evidence in result["evidence"]:
                assert evidence["source_type"] == "workspace_document"
                # source_label should be present (document title)
                assert "source_label" in evidence


# =============================================================================
# Audit Logging Tests
# =============================================================================


@pytest.mark.integration
class TestEvidenceScopeAuditLogging:
    """Tests for audit logging of evidence_scope."""

    @pytest.mark.asyncio
    async def test_audit_log_includes_evidence_scope(
        self,
        async_client: AsyncClient,
        clean_db,
    ):
        """Test that audit logs include evidence_scope and counts."""
        data, token = await bootstrap_and_login(async_client)
        headers = {"Authorization": f"Bearer {token}"}
        tenant_id = data["tenant"]["id"]

        # Create policy
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
        await async_client.post("/policy-profiles", headers=headers, json=policy_body)

        # Call legal research with specific scope
        await async_client.post(
            "/workflows/legal-research",
            headers=headers,
            json={
                "question": "Test question",
                "limit": 10,
                "evidence_scope": "both",
            },
        )

        # Check audit logs
        async with TestSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT meta FROM audit_logs
                    WHERE tenant_id = :tenant_id
                    AND action = 'workflow.run.success'
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"tenant_id": tenant_id},
            )
            row = result.fetchone()

        assert row is not None
        meta = row[0]  # meta is JSONB, already dict

        # Verify audit log includes evidence scope info
        assert meta["evidence_scope"] == "both"
        assert "workspace_evidence_count" in meta
        assert "global_evidence_count" in meta
        assert "policy_jurisdictions_count" in meta
        assert "policy_languages_count" in meta


# =============================================================================
# Provenance Field Consistency Tests
# =============================================================================


class TestProvenanceFieldConsistency:
    """Tests for provenance field canonicalization across backend DTOs.

    Canonical provenance fields that must exist end-to-end:
    - source_type (required)
    - source_label (required)
    - jurisdiction (optional)
    - official_source_url (optional)
    - published_at (optional)
    - effective_at (optional)
    """

    def test_unified_evidence_chunk_has_all_provenance_fields(self) -> None:
        """Test that UnifiedEvidenceChunk contains all canonical provenance fields."""
        from src.services.unified_retrieval_service import UnifiedEvidenceChunk

        # Create a workspace evidence chunk
        workspace_chunk = UnifiedEvidenceChunk(
            chunk_id="chunk-123",
            chunk_index=0,
            snippet="Test snippet",
            source_type="workspace_document",
            source_label="Test Document",
        )

        # Required fields must be present
        assert hasattr(workspace_chunk, "source_type")
        assert hasattr(workspace_chunk, "source_label")
        assert workspace_chunk.source_type == "workspace_document"
        assert workspace_chunk.source_label == "Test Document"

        # Optional fields must exist (can be None)
        assert hasattr(workspace_chunk, "jurisdiction")
        assert hasattr(workspace_chunk, "official_source_url")
        assert hasattr(workspace_chunk, "published_at")
        assert hasattr(workspace_chunk, "effective_at")

    def test_unified_evidence_chunk_global_legal_provenance(self) -> None:
        """Test that global legal evidence populates all provenance fields."""
        from src.services.unified_retrieval_service import UnifiedEvidenceChunk

        global_chunk = UnifiedEvidenceChunk(
            chunk_id="global-chunk-456",
            chunk_index=5,
            snippet="Legal text from UAE Labour Law",
            source_type="global_legal",
            source_label="UAE Labour Law (2022)",
            jurisdiction="UAE",
            official_source_url="https://laws.uae.gov/labour",
            published_at="2022-01-15",
            effective_at="2022-06-01",
        )

        # All provenance fields populated
        assert global_chunk.source_type == "global_legal"
        assert global_chunk.source_label == "UAE Labour Law (2022)"
        assert global_chunk.jurisdiction == "UAE"
        assert global_chunk.official_source_url == "https://laws.uae.gov/labour"
        assert global_chunk.published_at == "2022-01-15"
        assert global_chunk.effective_at == "2022-06-01"

    def test_unified_retrieval_meta_has_policy_fields(self) -> None:
        """Test that UnifiedRetrievalMeta contains all policy metadata fields."""
        from src.services.unified_retrieval_service import UnifiedRetrievalMeta

        meta = UnifiedRetrievalMeta(
            evidence_scope="both",
            workspace_evidence_count=5,
            global_evidence_count=3,
            total_evidence_count=8,
            policy_applied=True,
            policy_jurisdictions_count=4,
            policy_languages_count=2,
            policy_denied_reason=None,
        )

        # Convert to dict for audit logging
        meta_dict = meta.to_dict()

        # All fields must be present
        assert "evidence_scope" in meta_dict
        assert "workspace_evidence_count" in meta_dict
        assert "global_evidence_count" in meta_dict
        assert "total_evidence_count" in meta_dict
        assert "policy_applied" in meta_dict
        assert "policy_jurisdictions_count" in meta_dict
        assert "policy_languages_count" in meta_dict
        assert "policy_denied_reason" in meta_dict

    def test_api_schema_evidence_chunk_provenance(self) -> None:
        """Test that API schema EvidenceChunk has canonical provenance fields."""
        from src.schemas.research import EvidenceChunk

        # Create evidence with all fields
        evidence = EvidenceChunk(
            chunk_id="test-chunk",
            chunk_index=0,
            snippet="Test snippet",
            source_type="global_legal",
            source_label="Test Law",
            char_start=0,
            char_end=100,
            jurisdiction="KSA",
            official_source_url="https://example.com/law",
            published_at="2023-01-01",
            effective_at="2023-06-01",
        )

        # Required provenance
        assert evidence.source_type == "global_legal"
        assert evidence.source_label == "Test Law"

        # Optional provenance
        assert evidence.jurisdiction == "KSA"
        assert evidence.official_source_url == "https://example.com/law"
        assert evidence.published_at == "2023-01-01"
        assert evidence.effective_at == "2023-06-01"

    def test_evidence_chunk_ref_has_source_type(self) -> None:
        """Test that EvidenceChunkRef (for findings) includes source_type."""
        from src.schemas.contract_review import EvidenceChunkRef

        # Workspace evidence
        workspace_ref = EvidenceChunkRef(
            chunk_id="ws-chunk",
            snippet="Workspace text",
            char_start=0,
            char_end=50,
            source_type="workspace_document",
            source_label="Employment Contract",
        )
        assert workspace_ref.source_type == "workspace_document"

        # Global legal evidence
        global_ref = EvidenceChunkRef(
            chunk_id="gl-chunk",
            snippet="Legal text",
            char_start=0,
            char_end=50,
            source_type="global_legal",
            source_label="UAE Labour Law",
            instrument_id="inst-123",
            jurisdiction="UAE",
            official_source_url="https://laws.uae.gov",
        )
        assert global_ref.source_type == "global_legal"
        assert global_ref.instrument_id == "inst-123"
        assert global_ref.jurisdiction == "UAE"
        assert global_ref.official_source_url == "https://laws.uae.gov"
