"""Research service for legal research workflow.

This service implements the LEGAL_RESEARCH_V1 workflow:
1. Retrieves relevant chunks from the document vault (or global legal corpus)
2. Generates cited answers using an LLM
3. Validates citations and builds response
4. Enforces strict citation requirements (every paragraph must have citations)

Unified Retrieval:
- Supports evidence_scope: "workspace", "global", or "both"
- Uses UnifiedRetrievalService for scope-aware evidence retrieval
- All evidence chunks include explicit source_type provenance
"""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.llm import LLMProvider, get_llm_provider
from src.schemas.research import (
    CitationReference,
    EvidenceChunk,
    EvidenceScope,
    LegalResearchResponse,
    ResearchFilters,
    ResearchMeta,
)
from src.schemas.workflow_status import WorkflowResultStatus
from src.services.retrieval_service import SearchFilters
from src.services.unified_retrieval_service import (
    EvidenceScope as UnifiedEvidenceScope,
    UnifiedEvidenceBundle,
    UnifiedEvidenceChunk,
    UnifiedRetrievalService,
)
from src.utils.hashing import hash_prompt, hash_question

logger = logging.getLogger(__name__)


# Minimum number of evidence chunks required for a confident answer
MIN_EVIDENCE_CHUNKS = 3

# Minimum answer length (chars) after strict enforcement to be considered valid
MIN_ANSWER_LENGTH = 50

# Workflow identifier
WORKFLOW_NAME = "LEGAL_RESEARCH_V1"

# Pattern to match citation markers like [1], [2], [1,2], [1][2]
CITATION_PATTERN = re.compile(r"\[(\d+)\]")
CITATION_MULTI_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


@dataclass
class StrictCitationResult:
    """Result of strict citation enforcement."""

    cleaned_answer: str
    citations: list[CitationReference]
    removed_paragraph_count: int
    strict_citations_failed: bool
    warnings: list[str] = field(default_factory=list)
    citation_count_used: int = 0


@dataclass
class ResearchContext:
    """Internal context for research execution."""

    question: str
    limit: int
    filters: ResearchFilters | None
    output_language: str
    request_id: str | None


class ResearchService:
    """Service for legal research with cited answers.

    This service:
    1. Retrieves relevant document chunks (from workspace, global, or both)
    2. Builds a prompt with evidence
    3. Generates a cited answer using an LLM
    4. Validates citations
    5. Returns structured response with explicit provenance
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider | None = None,
    ):
        """Initialize the research service.

        Args:
            db: Async database session
            llm_provider: LLM provider (defaults to configured provider)
        """
        self.db = db
        self.llm = llm_provider or get_llm_provider()
        self.unified_retrieval = UnifiedRetrievalService(db)

    async def answer_question(
        self,
        ctx: RequestContext,
        question: str,
        *,
        limit: int = 10,
        filters: ResearchFilters | None = None,
        output_language: str = "en",
        request_id: str | None = None,
        evidence_scope: EvidenceScope = "workspace",
    ) -> LegalResearchResponse:
        """Answer a legal question with citations.

        Args:
            ctx: Request context with tenant/workspace info
            question: The legal question to answer
            limit: Maximum evidence chunks to retrieve
            filters: Optional filters for retrieval
            output_language: Language for the output ("en" or "ar")
            request_id: Request ID for tracing
            evidence_scope: Evidence retrieval scope ("workspace", "global", or "both")

        Returns:
            LegalResearchResponse with answer, citations, and evidence
        """
        # Build search filters from research filters
        search_filters = SearchFilters(
            document_type=filters.document_type if filters else None,
            jurisdiction=filters.jurisdiction if filters else None,
            language=filters.language if filters else None,
            include_unindexed=False,  # Only indexed documents
        )

        # Retrieve relevant chunks using unified retrieval
        # For scope="both", get 8 chunks from each source for research workflow
        bundle = await self.unified_retrieval.retrieve_evidence(
            ctx,
            question,
            scope=evidence_scope,
            limit=limit,
            workspace_filters=search_filters,
            limit_per_source=8 if evidence_scope == "both" else None,
        )

        # Convert to evidence chunks
        evidence = self._build_evidence_from_bundle(bundle)

        # Check for insufficient evidence
        if len(evidence) < MIN_EVIDENCE_CHUNKS:
            return self._build_insufficient_response(
                evidence=evidence,
                request_id=request_id,
                output_language=output_language,
                evidence_scope=evidence_scope,
                bundle_meta=bundle.meta,
            )

        # Build prompt and generate answer
        prompt = self._build_prompt(question, evidence, output_language)
        system_prompt = self._build_system_prompt(output_language)

        # Compute prompt hash for traceability (never store raw prompt)
        prompt_fingerprint = hash_prompt(prompt, system_prompt)

        llm_response = await self.llm.generate(
            prompt,
            system_prompt=system_prompt,
            temperature=0.0,  # Deterministic for legal answers
            max_tokens=2048,
        )

        # Apply strict citation enforcement
        result = self._process_answer(llm_response.text, evidence)

        # If strict enforcement failed, return insufficient sources response
        if result.strict_citations_failed:
            return self._build_strict_failed_response(
                evidence=evidence,
                request_id=request_id,
                output_language=output_language,
                model=llm_response.model,
                provider=llm_response.provider,
                removed_paragraph_count=result.removed_paragraph_count,
                warnings=result.warnings,
                prompt_hash=prompt_fingerprint,
                evidence_scope=evidence_scope,
                bundle_meta=bundle.meta,
            )

        return LegalResearchResponse(
            answer_text=result.cleaned_answer,
            citations=result.citations,
            evidence=evidence,
            insufficient_sources=False,
            meta=ResearchMeta(
                status=WorkflowResultStatus.SUCCESS,
                model=llm_response.model,
                provider=llm_response.provider,
                chunk_count=len(evidence),
                request_id=request_id,
                output_language=output_language,
                validation_warnings=result.warnings if result.warnings else None,
                strict_citation_enforced=True,
                removed_paragraph_count=result.removed_paragraph_count,
                strict_citations_failed=False,
                citation_count_used=result.citation_count_used,
                prompt_hash=prompt_fingerprint,
                llm_provider=llm_response.provider,
                llm_model=llm_response.model,
                # Evidence scope and counts
                evidence_scope=evidence_scope,
                workspace_evidence_count=bundle.meta.workspace_evidence_count,
                global_evidence_count=bundle.meta.global_evidence_count,
                # Policy metadata
                policy_jurisdictions_count=bundle.meta.policy_jurisdictions_count,
                policy_languages_count=bundle.meta.policy_languages_count,
                policy_denied_reason=bundle.meta.policy_denied_reason,
            ),
        )

    def _build_evidence_from_bundle(
        self, bundle: UnifiedEvidenceBundle
    ) -> list[EvidenceChunk]:
        """Convert unified evidence bundle to evidence chunks."""
        return [
            EvidenceChunk(
                chunk_id=r.chunk_id,
                chunk_index=r.chunk_index,
                snippet=r.snippet,
                # Source provenance
                source_type=r.source_type,
                source_label=r.source_label,
                # Document metadata (workspace)
                document_id=r.document_id,
                version_id=r.version_id,
                document_title=r.document_title,
                document_type=r.document_type,
                # Instrument metadata (global)
                instrument_id=r.instrument_id,
                instrument_title=r.instrument_title,
                instrument_title_ar=r.instrument_title_ar,
                instrument_type=r.instrument_type,
                # Common metadata
                jurisdiction=r.jurisdiction,
                language=r.language,
                char_start=r.char_start,
                char_end=r.char_end,
                page_start=r.page_start,
                page_end=r.page_end,
                final_score=r.score,
                # Legal provenance (global)
                published_at=r.published_at,
                effective_at=r.effective_at,
                official_source_url=r.official_source_url,
            )
            for r in bundle.items
        ]

    def _build_insufficient_response(
        self,
        evidence: list[EvidenceChunk],
        request_id: str | None,
        output_language: str,
        evidence_scope: EvidenceScope = "workspace",
        bundle_meta=None,
    ) -> LegalResearchResponse:
        """Build response when there's insufficient evidence."""
        if output_language == "ar":
            message = (
                "لا تتوفر مصادر كافية في مساحة العمل الخاصة بك للإجابة بثقة."
            )
        else:
            message = "Insufficient sources in your workspace to answer confidently."

        return LegalResearchResponse(
            answer_text=message,
            citations=[],
            evidence=evidence,
            insufficient_sources=True,
            meta=ResearchMeta(
                status=WorkflowResultStatus.INSUFFICIENT_SOURCES,
                model="none",
                provider="none",
                chunk_count=len(evidence),
                request_id=request_id,
                output_language=output_language,
                validation_warnings=None,
                strict_citation_enforced=True,
                removed_paragraph_count=0,
                strict_citations_failed=False,
                citation_count_used=0,
                prompt_hash=None,
                llm_provider=None,
                llm_model=None,
                # Evidence scope and counts
                evidence_scope=evidence_scope,
                workspace_evidence_count=bundle_meta.workspace_evidence_count if bundle_meta else 0,
                global_evidence_count=bundle_meta.global_evidence_count if bundle_meta else 0,
                # Policy metadata
                policy_jurisdictions_count=bundle_meta.policy_jurisdictions_count if bundle_meta else 0,
                policy_languages_count=bundle_meta.policy_languages_count if bundle_meta else 0,
                policy_denied_reason=bundle_meta.policy_denied_reason if bundle_meta else None,
            ),
        )

    def _build_strict_failed_response(
        self,
        evidence: list[EvidenceChunk],
        request_id: str | None,
        output_language: str,
        model: str,
        provider: str,
        removed_paragraph_count: int,
        warnings: list[str],
        prompt_hash: str | None = None,
        evidence_scope: EvidenceScope = "workspace",
        bundle_meta=None,
    ) -> LegalResearchResponse:
        """Build response when strict citation enforcement fails.

        This is used when the LLM produces content but none of it
        meets the citation requirements after paragraph filtering.
        """
        if output_language == "ar":
            message = (
                "لا تتوفر مصادر كافية في مساحة العمل الخاصة بك للإجابة بثقة."
            )
        else:
            message = "Insufficient sources in your workspace to answer confidently."

        return LegalResearchResponse(
            answer_text=message,
            citations=[],
            evidence=evidence,
            insufficient_sources=True,
            meta=ResearchMeta(
                status=WorkflowResultStatus.CITATION_VIOLATION,
                model=model,
                provider=provider,
                chunk_count=len(evidence),
                request_id=request_id,
                output_language=output_language,
                validation_warnings=warnings if warnings else None,
                strict_citation_enforced=True,
                removed_paragraph_count=removed_paragraph_count,
                strict_citations_failed=True,
                citation_count_used=0,
                prompt_hash=prompt_hash,
                llm_provider=provider,
                llm_model=model,
                # Evidence scope and counts
                evidence_scope=evidence_scope,
                workspace_evidence_count=bundle_meta.workspace_evidence_count if bundle_meta else 0,
                global_evidence_count=bundle_meta.global_evidence_count if bundle_meta else 0,
                # Policy metadata
                policy_jurisdictions_count=bundle_meta.policy_jurisdictions_count if bundle_meta else 0,
                policy_languages_count=bundle_meta.policy_languages_count if bundle_meta else 0,
                policy_denied_reason=bundle_meta.policy_denied_reason if bundle_meta else None,
            ),
        )

    def _build_system_prompt(self, output_language: str) -> str:
        """Build system prompt for the LLM with strict citation requirements."""
        language_instruction = (
            "Respond in Arabic." if output_language == "ar" else "Respond in English."
        )

        return f"""You are a legal research assistant. Your role is to provide accurate, well-cited answers based ONLY on the evidence provided.

CRITICAL CITATION RULES (MUST FOLLOW):
1. EVERY paragraph in your answer MUST contain at least one citation like [1], [2], etc.
2. Do NOT write any paragraph without a citation - such paragraphs will be removed.
3. NEVER hallucinate or make up information not in the sources.
4. Use ONLY citation numbers that correspond to the evidence chunks provided (1 to N).
5. If you cannot make a statement with a citation, do not make that statement.
6. If evidence is insufficient to answer, respond with: "Insufficient sources in your workspace to answer confidently."

{language_instruction}

REQUIRED FORMAT:
- Each paragraph must have inline citations: "The contract specifies a 30-day notice period [1]."
- Multiple citations are allowed: "This is supported by the agreement [1][2]." or "This is confirmed [1, 2]."
- A "Key Sources" section at the end is optional but does not count as citations for paragraphs.
- DO NOT put all citations only at the end - each paragraph needs its own citations.
"""

    def _build_prompt(
        self, question: str, evidence: list[EvidenceChunk], output_language: str
    ) -> str:
        """Build the user prompt with evidence bundle."""
        prompt_parts = [
            f"QUESTION: {question}",
            "",
            "EVIDENCE SOURCES:",
            "",
        ]

        for i, chunk in enumerate(evidence, 1):
            prompt_parts.append(f"[EVIDENCE {i}]")
            prompt_parts.append(f"Document: {chunk.document_title}")
            prompt_parts.append(f"Type: {chunk.document_type}")
            prompt_parts.append(f"Jurisdiction: {chunk.jurisdiction}")
            if chunk.page_start is not None:
                prompt_parts.append(f"Pages: {chunk.page_start}-{chunk.page_end or chunk.page_start}")
            prompt_parts.append(f"Content:\n{chunk.snippet}")
            prompt_parts.append("")

        prompt_parts.append("INSTRUCTIONS:")
        prompt_parts.append(
            "1. Provide a comprehensive answer with inline citations [1], [2], etc."
        )
        prompt_parts.append(
            "2. EVERY paragraph MUST contain at least one citation. Paragraphs without citations will be removed."
        )
        prompt_parts.append(
            "3. Valid citations are [1] through [" + str(len(evidence)) + "] only."
        )
        prompt_parts.append(
            "4. If the evidence is insufficient, say: 'Insufficient sources in your workspace to answer confidently.'"
        )

        return "\n".join(prompt_parts)

    def _process_answer(
        self, answer: str, evidence: list[EvidenceChunk]
    ) -> StrictCitationResult:
        """Process the LLM answer with strict citation enforcement.

        Applies paragraph-level citation requirements:
        - Each paragraph must have at least one valid citation
        - Paragraphs without citations are removed
        - If all content is removed, marks as strict_citations_failed

        Returns:
            StrictCitationResult with cleaned answer and enforcement metadata
        """
        warnings: list[str] = []
        valid_indices = set(range(1, len(evidence) + 1))

        # Split into paragraphs (blank line delimiter)
        paragraphs = self._split_into_paragraphs(answer)

        # Detect and handle references-only footer
        paragraphs, footer_removed = self._handle_references_footer(paragraphs)
        if footer_removed:
            warnings.append("References-only footer detected and handled")

        # Process each paragraph for citations
        kept_paragraphs: list[str] = []
        removed_count = 0
        all_found_citations: set[int] = set()

        for para in paragraphs:
            # Find valid citations in this paragraph
            para_citations = self._extract_valid_citations(para, valid_indices)

            if para_citations:
                # Paragraph has valid citations - keep it
                # But first strip any invalid citations
                cleaned_para, invalid_count = self._strip_invalid_citations(
                    para, valid_indices
                )
                if invalid_count > 0:
                    warnings.append(
                        f"Removed {invalid_count} invalid citation(s) from paragraph"
                    )
                kept_paragraphs.append(cleaned_para)
                all_found_citations.update(para_citations)
            else:
                # No valid citations - remove paragraph
                removed_count += 1
                # Log first 50 chars of removed content for debugging
                preview = para[:50].replace("\n", " ")
                warnings.append(f"Removed uncited paragraph: '{preview}...'")

        # Reconstruct answer from kept paragraphs
        cleaned_answer = "\n\n".join(kept_paragraphs)

        # Clean up whitespace
        cleaned_answer = re.sub(r"\n{3,}", "\n\n", cleaned_answer).strip()

        # Check if answer is too short or empty after enforcement
        strict_failed = False
        if len(cleaned_answer) < MIN_ANSWER_LENGTH or not all_found_citations:
            strict_failed = True
            warnings.append(
                "Answer downgraded: insufficient cited content after strict enforcement"
            )

        # Build citation references for citations actually used
        citations = self._build_citation_references(all_found_citations, evidence)

        return StrictCitationResult(
            cleaned_answer=cleaned_answer,
            citations=citations,
            removed_paragraph_count=removed_count,
            strict_citations_failed=strict_failed,
            warnings=warnings,
            citation_count_used=len(all_found_citations),
        )

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs (blank line delimiter).

        Args:
            text: The text to split

        Returns:
            List of non-empty paragraphs
        """
        # Split on one or more blank lines
        raw_paragraphs = re.split(r"\n\s*\n", text)
        # Filter out empty/whitespace-only paragraphs
        return [p.strip() for p in raw_paragraphs if p.strip()]

    def _handle_references_footer(
        self, paragraphs: list[str]
    ) -> tuple[list[str], bool]:
        """Detect and handle a references-only footer section.

        If the last paragraph(s) appear to be a references section
        (e.g., "References:", "Sources:", "Key Sources:") and contain
        only citation markers without substantive content, mark them
        as a footer.

        The footer is kept only if earlier paragraphs have citations.

        Args:
            paragraphs: List of paragraphs

        Returns:
            Tuple of (processed_paragraphs, footer_was_removed)
        """
        if not paragraphs:
            return paragraphs, False

        # Check if last paragraph looks like a references section
        last_para = paragraphs[-1]
        references_patterns = [
            r"^(references|sources|key sources|bibliography)\s*:",
            r"^(المراجع|المصادر)\s*:",  # Arabic
        ]

        is_references = False
        for pattern in references_patterns:
            if re.match(pattern, last_para, re.IGNORECASE | re.MULTILINE):
                is_references = True
                break

        if not is_references:
            return paragraphs, False

        # It's a references section - check if earlier paragraphs have citations
        earlier_paragraphs = paragraphs[:-1]
        has_earlier_citations = any(
            CITATION_PATTERN.search(p) for p in earlier_paragraphs
        )

        if has_earlier_citations:
            # Keep everything - references footer is fine
            return paragraphs, False
        else:
            # Remove the references footer since earlier content has no citations
            return earlier_paragraphs, True

    def _extract_valid_citations(
        self, text: str, valid_indices: set[int]
    ) -> set[int]:
        """Extract valid citation indices from text.

        Supports [1], [2], [1,2], [1][2] formats.

        Args:
            text: Text to search
            valid_indices: Set of valid citation numbers

        Returns:
            Set of valid citation numbers found
        """
        found = set()

        # Handle [n] format
        for match in CITATION_PATTERN.finditer(text):
            num = int(match.group(1))
            if num in valid_indices:
                found.add(num)

        # Handle [n,m] format
        for match in CITATION_MULTI_PATTERN.finditer(text):
            nums_str = match.group(1)
            for num_str in nums_str.split(","):
                num = int(num_str.strip())
                if num in valid_indices:
                    found.add(num)

        return found

    def _strip_invalid_citations(
        self, text: str, valid_indices: set[int]
    ) -> tuple[str, int]:
        """Strip invalid citations from text.

        Args:
            text: Text to process
            valid_indices: Set of valid citation numbers

        Returns:
            Tuple of (cleaned_text, count_of_removed_citations)
        """
        removed_count = 0

        def replace_invalid(match):
            nonlocal removed_count
            num = int(match.group(1))
            if num in valid_indices:
                return match.group(0)
            removed_count += 1
            return ""

        cleaned = CITATION_PATTERN.sub(replace_invalid, text)
        # Clean up double spaces
        cleaned = re.sub(r"  +", " ", cleaned)
        return cleaned.strip(), removed_count

    def _build_citation_references(
        self, citation_nums: set[int], evidence: list[EvidenceChunk]
    ) -> list[CitationReference]:
        """Build CitationReference objects for the given citation numbers.

        Args:
            citation_nums: Set of citation numbers (1-indexed)
            evidence: List of evidence chunks

        Returns:
            List of CitationReference objects
        """
        citations = []
        for citation_num in sorted(citation_nums):
            if 1 <= citation_num <= len(evidence):
                chunk = evidence[citation_num - 1]
                citations.append(
                    CitationReference(
                        citation_index=citation_num,
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        version_id=chunk.version_id,
                        document_title=chunk.document_title,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                    )
                )
        return citations


# Note: hash_question is imported from src.utils.hashing
# and re-exported for backwards compatibility
