"""Contract review service for CONTRACT_REVIEW_V1 workflow.

This service implements the CONTRACT_REVIEW_V1 workflow:
1. Fetches chunks for a specific document version
2. Optionally augments with global legal evidence (scope-aware)
3. Ranks and selects evidence chunks deterministically
4. Generates structured findings using an LLM
5. Validates citations and builds response
6. Enforces strict citation requirements (every finding must have valid citations)

Unified Retrieval:
- Supports evidence_scope: "workspace", "global", or "both"
- "workspace" (default): Uses only chunks from the target document
- "global": Augments with global legal corpus evidence
- "both": Uses document chunks + global legal evidence
"""

import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.llm import LLMProvider, get_llm_provider
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_version import DocumentVersion
from src.schemas.contract_review import (
    ContractReviewMeta,
    ContractReviewResponse,
    EvidenceChunkRef,
    EvidenceScope,
    Finding,
    FocusArea,
    ReviewMode,
)
from src.schemas.workflow_status import WorkflowResultStatus
from src.services.unified_retrieval_service import (
    EvidenceScope as UnifiedEvidenceScope,
    UnifiedEvidenceChunk,
    UnifiedRetrievalMeta,
    UnifiedRetrievalService,
)
from src.utils.hashing import hash_prompt

logger = logging.getLogger(__name__)


# Workflow identifier
WORKFLOW_NAME = "CONTRACT_REVIEW_V1"

# Minimum number of evidence chunks required for a confident review
MIN_EVIDENCE_CHUNKS = 3

# Chunk limits per review mode
CHUNK_LIMITS = {
    "quick": 20,
    "standard": 40,
    "deep": 80,
}

# Contract-relevant keywords for clause-likelihood ranking
CONTRACT_KEYWORDS = [
    "shall",
    "liability",
    "terminate",
    "termination",
    "governing law",
    "indemn",
    "indemnify",
    "indemnification",
    "confidential",
    "confidentiality",
    "payment",
    "ip",
    "intellectual property",
    "warranty",
    "warranties",
    "representations",
    "breach",
    "damages",
    "force majeure",
    "assignment",
    "notice",
    "dispute",
    "arbitration",
]

# Pattern to match citation markers like [1], [2]
CITATION_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass
class EvidenceChunk:
    """Internal representation of an evidence chunk."""

    chunk_id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    page_start: int | None
    page_end: int | None
    score: float  # Clause-likelihood score

    # Source provenance (for unified retrieval)
    source_type: str = "workspace_document"
    source_label: str = ""

    # Global legal metadata (optional)
    instrument_id: str | None = None
    jurisdiction: str | None = None
    official_source_url: str | None = None


@dataclass
class StrictCitationResult:
    """Result of strict citation enforcement for contract review."""

    summary: str
    findings: list[Finding]
    removed_findings_count: int
    strict_citations_failed: bool
    warnings: list[str] = field(default_factory=list)


class ContractReviewService:
    """Service for contract review with structured findings.

    This service:
    1. Fetches chunks for the target document version
    2. Optionally augments with global legal evidence (scope-aware)
    3. Ranks chunks by clause-likelihood (deterministic)
    4. Builds a prompt with numbered evidence
    5. Generates structured findings using an LLM
    6. Validates citations and returns structured response
    """

    # Global legal evidence limit when scope includes global
    GLOBAL_EVIDENCE_LIMIT = 20

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider | None = None,
    ):
        """Initialize the contract review service.

        Args:
            db: Async database session
            llm_provider: LLM provider (defaults to configured provider)
        """
        self.db = db
        self.llm = llm_provider or get_llm_provider()
        self.unified_retrieval = UnifiedRetrievalService(db)

    async def review_contract(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
        *,
        review_mode: ReviewMode = "standard",
        focus_areas: list[FocusArea] | None = None,
        output_language: str = "en",
        playbook_hint: str | None = None,
        request_id: str | None = None,
        evidence_scope: EvidenceScope = "workspace",
    ) -> ContractReviewResponse:
        """Review a contract document and produce structured findings.

        Args:
            ctx: Request context with tenant/workspace info
            document_id: ID of the document to review
            version_id: ID of the specific version to review
            review_mode: Review depth (quick/standard/deep)
            focus_areas: Optional focus areas to prioritize
            output_language: Language for the output ("en" or "ar")
            playbook_hint: Optional hint from a playbook to guide the review focus
            request_id: Request ID for tracing
            evidence_scope: Evidence retrieval scope ("workspace", "global", or "both")

        Returns:
            ContractReviewResponse with summary, findings, and evidence
        """
        # Verify document/version belongs to workspace
        document, version = await self._verify_document_access(
            ctx, document_id, version_id
        )

        # Initialize retrieval meta for tracking
        retrieval_meta = UnifiedRetrievalMeta(
            evidence_scope=evidence_scope,
        )

        # Fetch and rank chunks from the contract document
        evidence = await self._fetch_and_rank_chunks(
            ctx, document_id, version_id, review_mode, document.title
        )
        retrieval_meta.workspace_evidence_count = len(evidence)

        # Optionally augment with global legal evidence
        if evidence_scope in ("global", "both"):
            global_evidence = await self._fetch_global_legal_evidence(
                ctx, document, focus_areas, retrieval_meta
            )
            # For "both", append global evidence after workspace evidence
            # For "global" only, this is still used alongside document chunks
            evidence = evidence + global_evidence
            retrieval_meta.global_evidence_count = len(global_evidence)

        retrieval_meta.total_evidence_count = len(evidence)

        # Check for insufficient evidence
        if len(evidence) < MIN_EVIDENCE_CHUNKS:
            return self._build_insufficient_response(
                evidence=evidence,
                request_id=request_id,
                output_language=output_language,
                review_mode=review_mode,
                evidence_scope=evidence_scope,
                retrieval_meta=retrieval_meta,
            )

        # Build prompt and generate findings
        prompt = self._build_prompt(
            document.title, evidence, focus_areas, output_language, playbook_hint
        )
        system_prompt = self._build_system_prompt(output_language)

        # Compute prompt hash for traceability (never store raw prompt)
        prompt_fingerprint = hash_prompt(prompt, system_prompt)

        llm_response = await self.llm.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.0,  # Deterministic for legal analysis
            max_tokens=4096,
        )

        # Parse and validate the JSON response
        result = self._process_response(llm_response.text, evidence)

        # If strict enforcement failed, return insufficient sources response
        if result.strict_citations_failed:
            return self._build_strict_failed_response(
                evidence=evidence,
                request_id=request_id,
                output_language=output_language,
                review_mode=review_mode,
                model=llm_response.model,
                provider=llm_response.provider,
                removed_findings_count=result.removed_findings_count,
                warnings=result.warnings,
                prompt_hash=prompt_fingerprint,
                evidence_scope=evidence_scope,
                retrieval_meta=retrieval_meta,
            )

        return ContractReviewResponse(
            summary=result.summary,
            findings=result.findings,
            insufficient_sources=False,
            meta=ContractReviewMeta(
                status=WorkflowResultStatus.SUCCESS,
                model=llm_response.model,
                provider=llm_response.provider,
                evidence_chunk_count=len(evidence),
                request_id=request_id,
                output_language=output_language,
                review_mode=review_mode,
                removed_findings_count=result.removed_findings_count,
                strict_citations_failed=False,
                validation_warnings=result.warnings if result.warnings else None,
                prompt_hash=prompt_fingerprint,
                llm_provider=llm_response.provider,
                llm_model=llm_response.model,
                # Evidence scope and counts
                evidence_scope=evidence_scope,
                workspace_evidence_count=retrieval_meta.workspace_evidence_count,
                global_evidence_count=retrieval_meta.global_evidence_count,
                # Policy metadata
                policy_jurisdictions_count=retrieval_meta.policy_jurisdictions_count,
                policy_languages_count=retrieval_meta.policy_languages_count,
                policy_denied_reason=retrieval_meta.policy_denied_reason,
            ),
        )

    async def _verify_document_access(
        self, ctx: RequestContext, document_id: str, version_id: str
    ) -> tuple[Document, DocumentVersion]:
        """Verify the document and version belong to the workspace.

        Args:
            ctx: Request context
            document_id: Document ID to verify
            version_id: Version ID to verify

        Returns:
            Tuple of (Document, DocumentVersion)

        Raises:
            ValueError: If document/version not found or doesn't belong to workspace
        """
        # Verify document belongs to workspace
        doc_result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.workspace_id == ctx.workspace.id,
                Document.tenant_id == ctx.tenant.id,
            )
        )
        document = doc_result.scalar_one_or_none()
        if not document:
            raise ValueError(
                f"Document {document_id} not found in workspace {ctx.workspace.id}"
            )

        # Verify version belongs to document
        version_result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.id == version_id,
                DocumentVersion.document_id == document_id,
            )
        )
        version = version_result.scalar_one_or_none()
        if not version:
            raise ValueError(
                f"Version {version_id} not found for document {document_id}"
            )

        return document, version

    async def _fetch_and_rank_chunks(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
        review_mode: ReviewMode,
        document_title: str = "",
    ) -> list[EvidenceChunk]:
        """Fetch chunks for the document version and rank by clause-likelihood.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID
            review_mode: Review depth mode
            document_title: Title for source label

        Returns:
            List of ranked EvidenceChunk objects
        """
        chunk_limit = CHUNK_LIMITS.get(review_mode, 40)

        # Fetch all chunks for this version
        result = await self.db.execute(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.version_id == version_id,
                DocumentChunk.tenant_id == ctx.tenant.id,
                DocumentChunk.workspace_id == ctx.workspace.id,
            )
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = result.scalars().all()

        # Score and rank chunks
        scored_chunks: list[EvidenceChunk] = []
        for chunk in chunks:
            score = self._calculate_clause_score(chunk.text)
            scored_chunks.append(
                EvidenceChunk(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    score=score,
                    source_type="workspace_document",
                    source_label=document_title,
                )
            )

        # Sort by score desc, then chunk_index asc for deterministic ordering
        scored_chunks.sort(key=lambda c: (-c.score, c.chunk_index))

        # Return top N chunks
        return scored_chunks[:chunk_limit]

    async def _fetch_global_legal_evidence(
        self,
        ctx: RequestContext,
        document: Document,
        focus_areas: list[FocusArea] | None,
        retrieval_meta: UnifiedRetrievalMeta,
    ) -> list[EvidenceChunk]:
        """Fetch global legal evidence to augment contract review.

        Uses the document jurisdiction and focus areas to build a relevant query.

        Args:
            ctx: Request context
            document: The document being reviewed
            focus_areas: Optional focus areas to target
            retrieval_meta: Retrieval metadata to update

        Returns:
            List of EvidenceChunk objects from global legal corpus
        """
        # Build query from focus areas and document context
        query_parts = []
        if focus_areas:
            query_parts.extend(focus_areas)
        else:
            # Default contract review topics
            query_parts.extend(["liability", "termination", "governing law", "indemnity"])

        query = " ".join(query_parts) + f" {document.jurisdiction} contract law"

        # Retrieve from global legal corpus only
        bundle = await self.unified_retrieval.retrieve_evidence(
            ctx,
            query,
            scope=UnifiedEvidenceScope.GLOBAL,
            limit=self.GLOBAL_EVIDENCE_LIMIT,
        )

        # Update retrieval meta with policy info
        retrieval_meta.policy_jurisdictions_count = bundle.meta.policy_jurisdictions_count
        retrieval_meta.policy_languages_count = bundle.meta.policy_languages_count
        retrieval_meta.policy_denied_reason = bundle.meta.policy_denied_reason

        # Convert to internal EvidenceChunk format
        return [
            EvidenceChunk(
                chunk_id=r.chunk_id,
                chunk_index=r.chunk_index,
                text=r.snippet,
                char_start=r.char_start,
                char_end=r.char_end,
                page_start=r.page_start,
                page_end=r.page_end,
                score=r.score,
                source_type="global_legal",
                source_label=r.source_label,
                instrument_id=r.instrument_id,
                jurisdiction=r.jurisdiction,
                official_source_url=r.official_source_url,
            )
            for r in bundle.items
        ]

    def _calculate_clause_score(self, text: str) -> float:
        """Calculate clause-likelihood score for a chunk.

        Scoring heuristic:
        - Base score from text length (longer chunks more likely to contain clauses)
        - Bonus for contract keywords

        Args:
            text: Chunk text content

        Returns:
            Clause-likelihood score (higher is better)
        """
        text_lower = text.lower()

        # Length score (normalized, max ~1.0 for 1000+ chars)
        length_score = min(len(text) / 1000.0, 1.0)

        # Keyword score (count matching keywords)
        keyword_count = 0
        for keyword in CONTRACT_KEYWORDS:
            if keyword in text_lower:
                keyword_count += 1

        # Normalize keyword score (max ~1.0 for 5+ keywords)
        keyword_score = min(keyword_count / 5.0, 1.0)

        # Combined score (weighted)
        return length_score * 0.4 + keyword_score * 0.6

    def _build_insufficient_response(
        self,
        evidence: list[EvidenceChunk],
        request_id: str | None,
        output_language: str,
        review_mode: str,
        evidence_scope: EvidenceScope = "workspace",
        retrieval_meta: UnifiedRetrievalMeta | None = None,
    ) -> ContractReviewResponse:
        """Build response when there's insufficient evidence."""
        if output_language == "ar":
            message = "لا تتوفر مصادر كافية في مساحة العمل الخاصة بك لمراجعة هذا العقد بثقة."
        else:
            message = (
                "Insufficient sources in your workspace to review this contract confidently."
            )

        return ContractReviewResponse(
            summary=message,
            findings=[],
            insufficient_sources=True,
            meta=ContractReviewMeta(
                status=WorkflowResultStatus.INSUFFICIENT_SOURCES,
                model="none",
                provider="none",
                evidence_chunk_count=len(evidence),
                request_id=request_id,
                output_language=output_language,
                review_mode=review_mode,
                removed_findings_count=0,
                strict_citations_failed=False,
                validation_warnings=None,
                prompt_hash=None,
                llm_provider=None,
                llm_model=None,
                # Evidence scope and counts
                evidence_scope=evidence_scope,
                workspace_evidence_count=retrieval_meta.workspace_evidence_count if retrieval_meta else 0,
                global_evidence_count=retrieval_meta.global_evidence_count if retrieval_meta else 0,
                # Policy metadata
                policy_jurisdictions_count=retrieval_meta.policy_jurisdictions_count if retrieval_meta else 0,
                policy_languages_count=retrieval_meta.policy_languages_count if retrieval_meta else 0,
                policy_denied_reason=retrieval_meta.policy_denied_reason if retrieval_meta else None,
            ),
        )

    def _build_strict_failed_response(
        self,
        evidence: list[EvidenceChunk],
        request_id: str | None,
        output_language: str,
        review_mode: str,
        model: str,
        provider: str,
        removed_findings_count: int,
        warnings: list[str],
        prompt_hash: str | None = None,
        evidence_scope: EvidenceScope = "workspace",
        retrieval_meta: UnifiedRetrievalMeta | None = None,
    ) -> ContractReviewResponse:
        """Build response when strict citation enforcement fails."""
        if output_language == "ar":
            message = "لا تتوفر مصادر كافية في مساحة العمل الخاصة بك لمراجعة هذا العقد بثقة."
        else:
            message = (
                "Insufficient sources in your workspace to review this contract confidently."
            )

        return ContractReviewResponse(
            summary=message,
            findings=[],
            insufficient_sources=True,
            meta=ContractReviewMeta(
                status=WorkflowResultStatus.CITATION_VIOLATION,
                model=model,
                provider=provider,
                evidence_chunk_count=len(evidence),
                request_id=request_id,
                output_language=output_language,
                review_mode=review_mode,
                removed_findings_count=removed_findings_count,
                strict_citations_failed=True,
                validation_warnings=warnings if warnings else None,
                prompt_hash=prompt_hash,
                llm_provider=provider,
                llm_model=model,
                # Evidence scope and counts
                evidence_scope=evidence_scope,
                workspace_evidence_count=retrieval_meta.workspace_evidence_count if retrieval_meta else 0,
                global_evidence_count=retrieval_meta.global_evidence_count if retrieval_meta else 0,
                # Policy metadata
                policy_jurisdictions_count=retrieval_meta.policy_jurisdictions_count if retrieval_meta else 0,
                policy_languages_count=retrieval_meta.policy_languages_count if retrieval_meta else 0,
                policy_denied_reason=retrieval_meta.policy_denied_reason if retrieval_meta else None,
            ),
        )

    def _build_system_prompt(self, output_language: str) -> str:
        """Build system prompt for the LLM with strict citation requirements."""
        language_instruction = (
            "Respond in Arabic." if output_language == "ar" else "Respond in English."
        )

        return f"""You are a contract review specialist. Your role is to analyze contracts and identify risks based ONLY on the evidence provided.

CRITICAL REQUIREMENTS:
1. Output MUST be valid JSON matching the specified schema.
2. EVERY finding MUST include citations like [1], [2] in the issue and recommendation fields.
3. The citations list MUST contain valid evidence indices (1 to N).
4. The summary MUST contain at least one citation.
5. Do NOT hallucinate or make up information not in the sources.
6. If you cannot make a statement with a citation, do not include that finding.
7. Temperature is 0 - be precise and deterministic.

{language_instruction}

OUTPUT FORMAT (strict JSON):
{{
  "summary": "Executive summary with citations [1][2]...",
  "findings": [
    {{
      "title": "Brief title",
      "severity": "low|medium|high|critical",
      "category": "liability|termination|governing_law|payment|ip|confidentiality|other",
      "issue": "Description of the issue with citations [1]",
      "recommendation": "How to address it with citations [1]",
      "citations": [1, 2]
    }}
  ]
}}
"""

    def _build_prompt(
        self,
        document_title: str,
        evidence: list[EvidenceChunk],
        focus_areas: list[FocusArea] | None,
        output_language: str,
        playbook_hint: str | None = None,
    ) -> str:
        """Build the user prompt with evidence bundle."""
        prompt_parts = [
            f"CONTRACT REVIEW: {document_title}",
            "",
        ]

        # Prepend playbook hint if provided
        if playbook_hint:
            prompt_parts.append(f"PLAYBOOK GUIDANCE: {playbook_hint}")
            prompt_parts.append("")

        prompt_parts.append("EVIDENCE SOURCES:")
        prompt_parts.append("")

        for i, chunk in enumerate(evidence, 1):
            prompt_parts.append(f"[EVIDENCE {i}]")
            if chunk.page_start is not None:
                prompt_parts.append(
                    f"Pages: {chunk.page_start}-{chunk.page_end or chunk.page_start}"
                )
            prompt_parts.append(f"Content:\n{chunk.text}")
            prompt_parts.append("")

        prompt_parts.append("INSTRUCTIONS:")
        prompt_parts.append(
            "1. Analyze the contract and identify risks, issues, and areas of concern."
        )
        prompt_parts.append(
            "2. For each finding, cite the relevant evidence using [1], [2], etc."
        )
        prompt_parts.append(
            f"3. Valid citations are [1] through [{len(evidence)}] only."
        )
        prompt_parts.append(
            "4. Include a summary with citations to key evidence."
        )

        if focus_areas:
            focus_str = ", ".join(focus_areas)
            prompt_parts.append(
                f"5. Focus especially on these areas: {focus_str}"
            )

        prompt_parts.append("")
        prompt_parts.append("Output the review as valid JSON.")

        return "\n".join(prompt_parts)

    def _process_response(
        self, response: str, evidence: list[EvidenceChunk]
    ) -> StrictCitationResult:
        """Process the LLM response with strict citation enforcement.

        Args:
            response: Raw LLM response (expected to be JSON)
            evidence: List of evidence chunks

        Returns:
            StrictCitationResult with validated findings
        """
        warnings: list[str] = []
        valid_indices = set(range(1, len(evidence) + 1))

        # Try to parse JSON
        try:
            # Handle potential markdown code blocks
            json_str = response.strip()
            if json_str.startswith("```"):
                # Remove code fence
                lines = json_str.split("\n")
                json_str = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            warnings.append(f"Failed to parse JSON response: {str(e)[:100]}")
            return StrictCitationResult(
                summary="Insufficient sources in your workspace to review this contract confidently.",
                findings=[],
                removed_findings_count=0,
                strict_citations_failed=True,
                warnings=warnings,
            )

        # Extract summary
        summary = data.get("summary", "")

        # Validate summary has citations
        summary_citations = self._extract_valid_citations(summary, valid_indices)
        if not summary_citations:
            warnings.append("Summary has no valid citations")

        # Process findings
        raw_findings = data.get("findings", [])
        valid_findings: list[Finding] = []
        removed_count = 0

        for i, f in enumerate(raw_findings):
            try:
                # Extract and validate citations
                citations = f.get("citations", [])
                if not isinstance(citations, list):
                    citations = []

                # Filter to valid indices
                valid_cites = [c for c in citations if c in valid_indices]

                # Also check for citations in issue and recommendation text
                issue_text = f.get("issue", "")
                rec_text = f.get("recommendation", "")
                text_citations = self._extract_valid_citations(
                    issue_text + " " + rec_text, valid_indices
                )
                valid_cites = list(set(valid_cites) | text_citations)

                if not valid_cites:
                    # No valid citations - remove this finding
                    removed_count += 1
                    title = f.get("title", "Untitled")[:50]
                    warnings.append(f"Removed finding without valid citations: '{title}'")
                    continue

                # Build evidence references
                evidence_refs = []
                for cite_idx in sorted(valid_cites):
                    if 1 <= cite_idx <= len(evidence):
                        chunk = evidence[cite_idx - 1]
                        evidence_refs.append(
                            EvidenceChunkRef(
                                chunk_id=chunk.chunk_id,
                                snippet=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                                char_start=chunk.char_start,
                                char_end=chunk.char_end,
                                source_type=chunk.source_type,
                                source_label=chunk.source_label,
                                instrument_id=chunk.instrument_id,
                                jurisdiction=chunk.jurisdiction,
                                official_source_url=chunk.official_source_url,
                            )
                        )

                # Create validated finding
                finding = Finding(
                    title=f.get("title", "Untitled Finding"),
                    severity=self._validate_severity(f.get("severity", "medium")),
                    category=self._validate_category(f.get("category", "other")),
                    issue=issue_text,
                    recommendation=rec_text,
                    citations=sorted(valid_cites),
                    evidence=evidence_refs,
                )
                valid_findings.append(finding)

            except Exception as e:
                removed_count += 1
                warnings.append(f"Failed to process finding {i}: {str(e)[:50]}")

        # Check if all findings were removed
        strict_failed = len(valid_findings) == 0 and removed_count > 0

        # If summary has no citations but we have findings, regenerate summary from findings
        if not summary_citations and valid_findings:
            # Generate summary from valid findings
            all_cites = set()
            for f in valid_findings:
                all_cites.update(f.citations)
            cite_str = "".join(f"[{c}]" for c in sorted(all_cites)[:3])
            summary = f"Contract review identified {len(valid_findings)} finding(s) requiring attention {cite_str}."
            warnings.append("Summary regenerated from findings due to missing citations")

        return StrictCitationResult(
            summary=summary,
            findings=valid_findings,
            removed_findings_count=removed_count,
            strict_citations_failed=strict_failed,
            warnings=warnings,
        )

    def _extract_valid_citations(self, text: str, valid_indices: set[int]) -> set[int]:
        """Extract valid citation indices from text."""
        found = set()
        for match in CITATION_PATTERN.finditer(text):
            num = int(match.group(1))
            if num in valid_indices:
                found.add(num)
        return found

    def _validate_severity(self, severity: str) -> str:
        """Validate and normalize severity level."""
        valid = {"low", "medium", "high", "critical"}
        severity_lower = severity.lower() if severity else "medium"
        return severity_lower if severity_lower in valid else "medium"

    def _validate_category(self, category: str) -> str:
        """Validate and normalize category."""
        valid = {
            "liability",
            "termination",
            "governing_law",
            "payment",
            "ip",
            "confidentiality",
            "other",
        }
        category_lower = category.lower() if category else "other"
        return category_lower if category_lower in valid else "other"
