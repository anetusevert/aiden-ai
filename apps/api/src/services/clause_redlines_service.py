"""Clause redlines service for CLAUSE_REDLINES_V1 workflow.

This service implements the CLAUSE_REDLINES_V1 workflow:
1. Runs clause detection (heuristic)
2. Optionally augments with global legal evidence (scope-aware)
3. Builds evidence bundles for each clause type
4. Generates redline suggestions using an LLM
5. Validates citations and builds response
6. Enforces strict citation requirements for contract claims

Unified Retrieval:
- Supports evidence_scope: "workspace", "global", or "both"
- "workspace" (default): Uses only chunks from the target document
- "global" or "both": Augments with global legal corpus evidence
"""

import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.clause_library import ClauseType, get_clause_for_jurisdiction, get_clause_types
from src.dependencies.auth import RequestContext
from src.llm import LLMProvider, get_llm_provider
from src.schemas.clause_redlines import (
    ClauseRedlineItem,
    ClauseRedlinesMeta,
    ClauseRedlinesResponse,
    ConfidenceLevel,
    EvidenceChunkRef,
    EvidenceScope,
    Jurisdiction,
    Severity,
)
from src.schemas.workflow_status import WorkflowResultStatus
from src.services.clause_detection_service import (
    ClauseDetectionService,
    ClauseDetectionResult,
    DocumentClauseDetection,
    EvidenceChunk,
)
from src.services.unified_retrieval_service import (
    EvidenceScope as UnifiedEvidenceScope,
    UnifiedRetrievalMeta,
    UnifiedRetrievalService,
)
from src.utils.hashing import hash_prompt

logger = logging.getLogger(__name__)


# Workflow identifier
WORKFLOW_NAME = "CLAUSE_REDLINES_V1"

# Minimum number of total evidence chunks required for analysis
MIN_EVIDENCE_CHUNKS = 3

# Pattern to match citation markers like [1], [2]
CITATION_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass
class StrictCitationResult:
    """Result of strict citation enforcement for clause redlines."""

    summary: str
    items: list[ClauseRedlineItem]
    downgraded_count: int
    removed_count: int
    strict_citations_failed: bool
    warnings: list[str] = field(default_factory=list)


class ClauseRedlinesService:
    """Service for generating clause-centric redline suggestions.

    This service:
    1. Uses ClauseDetectionService to detect clauses
    2. Optionally augments with global legal evidence (scope-aware)
    3. Builds evidence bundles per clause type
    4. Uses LLM to generate redline suggestions
    5. Validates citations strictly (contract claims must be cited)
    6. Returns structured response with clear separation of template vs contract text
    """

    # Global legal evidence limit when scope includes global
    GLOBAL_EVIDENCE_LIMIT = 20

    def __init__(
        self,
        db: AsyncSession,
        llm_provider: LLMProvider | None = None,
    ):
        """Initialize the clause redlines service.

        Args:
            db: Async database session
            llm_provider: LLM provider (defaults to configured provider)
        """
        self.db = db
        self.llm = llm_provider or get_llm_provider()
        self.detection_service = ClauseDetectionService(db)
        self.unified_retrieval = UnifiedRetrievalService(db)

    async def generate_redlines(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
        *,
        jurisdiction: Jurisdiction | None = None,
        clause_types: list[ClauseType] | None = None,
        output_language: str = "en",
        playbook_hint: str | None = None,
        request_id: str | None = None,
        evidence_scope: EvidenceScope = "workspace",
    ) -> ClauseRedlinesResponse:
        """Generate clause redline suggestions for a document.

        Args:
            ctx: Request context with tenant/workspace info
            document_id: ID of the document
            version_id: ID of the version to analyze
            jurisdiction: Jurisdiction for clause templates (defaults to document jurisdiction)
            clause_types: Optional list of clause types to analyze (default: all)
            output_language: Language for the output ("en" or "ar")
            playbook_hint: Optional hint from a playbook
            request_id: Request ID for tracing
            evidence_scope: Evidence retrieval scope ("workspace", "global", or "both")

        Returns:
            ClauseRedlinesResponse with summary and items
        """
        # Initialize retrieval meta for tracking
        retrieval_meta = UnifiedRetrievalMeta(
            evidence_scope=evidence_scope,
        )

        # Run clause detection
        detection = await self.detection_service.detect_clauses(
            ctx, document_id, version_id, clause_types
        )

        # Use detected jurisdiction if not specified
        effective_jurisdiction = jurisdiction or detection.jurisdiction
        if effective_jurisdiction not in ("UAE", "DIFC", "ADGM", "KSA"):
            effective_jurisdiction = "UAE"  # Default fallback

        # Track workspace evidence count
        retrieval_meta.workspace_evidence_count = len(detection.all_chunks)

        # Check for insufficient evidence
        total_chunks = len(detection.all_chunks)
        if total_chunks < MIN_EVIDENCE_CHUNKS:
            return self._build_insufficient_response(
                total_chunks=total_chunks,
                jurisdiction=effective_jurisdiction,
                request_id=request_id,
                output_language=output_language,
                evidence_scope=evidence_scope,
                retrieval_meta=retrieval_meta,
            )

        # Build evidence map for the LLM prompt
        evidence_chunks, evidence_map = self._build_evidence_bundle(detection)

        # Optionally augment with global legal evidence
        if evidence_scope in ("global", "both"):
            global_evidence = await self._fetch_global_legal_evidence(
                ctx, effective_jurisdiction, clause_types or list(detection.results.keys()), retrieval_meta
            )
            # Append global evidence (with adjusted indices)
            start_idx = len(evidence_chunks) + 1
            for i, chunk in enumerate(global_evidence):
                evidence_chunks.append(chunk)
                # Add global evidence to evidence_map for all clause types
                for clause_type in evidence_map.keys():
                    evidence_map[clause_type].append(start_idx + i)
            retrieval_meta.global_evidence_count = len(global_evidence)

        retrieval_meta.total_evidence_count = len(evidence_chunks)

        if not evidence_chunks:
            return self._build_insufficient_response(
                total_chunks=0,
                jurisdiction=effective_jurisdiction,
                request_id=request_id,
                output_language=output_language,
                evidence_scope=evidence_scope,
                retrieval_meta=retrieval_meta,
            )

        # Build prompt and generate redlines
        prompt = self._build_prompt(
            detection=detection,
            evidence_chunks=evidence_chunks,
            evidence_map=evidence_map,
            jurisdiction=effective_jurisdiction,
            output_language=output_language,
            playbook_hint=playbook_hint,
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
        result = self._process_response(
            llm_response.text,
            evidence_chunks,
            evidence_map,
            detection,
            effective_jurisdiction,
        )

        # If strict enforcement failed, return insufficient sources response
        if result.strict_citations_failed:
            return self._build_strict_failed_response(
                total_chunks=len(evidence_chunks),
                jurisdiction=effective_jurisdiction,
                request_id=request_id,
                output_language=output_language,
                model=llm_response.model,
                provider=llm_response.provider,
                downgraded_count=result.downgraded_count,
                removed_count=result.removed_count,
                warnings=result.warnings,
                prompt_hash=prompt_fingerprint,
                evidence_scope=evidence_scope,
                retrieval_meta=retrieval_meta,
            )

        return ClauseRedlinesResponse(
            summary=result.summary,
            items=result.items,
            insufficient_sources=False,
            meta=ClauseRedlinesMeta(
                status=WorkflowResultStatus.SUCCESS,
                model=llm_response.model,
                provider=llm_response.provider,
                evidence_chunk_count=len(evidence_chunks),
                request_id=request_id,
                output_language=output_language,
                jurisdiction=effective_jurisdiction,
                downgraded_count=result.downgraded_count,
                removed_count=result.removed_count,
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

    def _build_evidence_bundle(
        self, detection: DocumentClauseDetection
    ) -> tuple[list[EvidenceChunk], dict[ClauseType, list[int]]]:
        """Build a de-duplicated evidence bundle from detection results.

        Args:
            detection: Clause detection results

        Returns:
            Tuple of (list of unique evidence chunks, map of clause_type to evidence indices)
        """
        # Collect all evidence chunks, de-duplicated by chunk_id
        chunk_map: dict[str, EvidenceChunk] = {}
        for result in detection.results.values():
            for chunk in result.evidence:
                if chunk.chunk_id not in chunk_map:
                    chunk_map[chunk.chunk_id] = chunk

        # Sort by chunk_index for deterministic ordering
        evidence_chunks = sorted(chunk_map.values(), key=lambda c: c.chunk_index)

        # Build reverse map: chunk_id -> 1-indexed evidence number
        chunk_to_idx: dict[str, int] = {
            chunk.chunk_id: i + 1 for i, chunk in enumerate(evidence_chunks)
        }

        # Build map: clause_type -> list of evidence indices
        evidence_map: dict[ClauseType, list[int]] = {}
        for clause_type, result in detection.results.items():
            indices = [chunk_to_idx[chunk.chunk_id] for chunk in result.evidence]
            evidence_map[clause_type] = sorted(indices)

        return evidence_chunks, evidence_map

    async def _fetch_global_legal_evidence(
        self,
        ctx: RequestContext,
        jurisdiction: str,
        clause_types: list[ClauseType],
        retrieval_meta: UnifiedRetrievalMeta,
    ) -> list[EvidenceChunk]:
        """Fetch global legal evidence to augment clause analysis.

        Uses the jurisdiction and clause types to build a relevant query.

        Args:
            ctx: Request context
            jurisdiction: Target jurisdiction
            clause_types: List of clause types being analyzed
            retrieval_meta: Retrieval metadata to update

        Returns:
            List of EvidenceChunk objects from global legal corpus
        """
        # Build query from clause types and jurisdiction
        query = f"{' '.join(clause_types)} {jurisdiction} contract law clauses"

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
            )
            for r in bundle.items
        ]

    def _build_insufficient_response(
        self,
        total_chunks: int,
        jurisdiction: str,
        request_id: str | None,
        output_language: str,
        evidence_scope: EvidenceScope = "workspace",
        retrieval_meta: UnifiedRetrievalMeta | None = None,
    ) -> ClauseRedlinesResponse:
        """Build response when there's insufficient evidence."""
        if output_language == "ar":
            message = "لا تتوفر مصادر كافية في مساحة العمل الخاصة بك لتحليل هذا العقد بثقة."
        else:
            message = (
                "Insufficient sources in your workspace to analyze this contract confidently."
            )

        return ClauseRedlinesResponse(
            summary=message,
            items=[],
            insufficient_sources=True,
            meta=ClauseRedlinesMeta(
                status=WorkflowResultStatus.INSUFFICIENT_SOURCES,
                model="none",
                provider="none",
                evidence_chunk_count=total_chunks,
                request_id=request_id,
                output_language=output_language,
                jurisdiction=jurisdiction,
                downgraded_count=0,
                removed_count=0,
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
        total_chunks: int,
        jurisdiction: str,
        request_id: str | None,
        output_language: str,
        model: str,
        provider: str,
        downgraded_count: int,
        removed_count: int,
        warnings: list[str],
        prompt_hash: str | None = None,
        evidence_scope: EvidenceScope = "workspace",
        retrieval_meta: UnifiedRetrievalMeta | None = None,
    ) -> ClauseRedlinesResponse:
        """Build response when strict citation enforcement fails."""
        if output_language == "ar":
            message = "لا تتوفر مصادر كافية في مساحة العمل الخاصة بك لتحليل هذا العقد بثقة."
        else:
            message = (
                "Insufficient sources in your workspace to analyze this contract confidently."
            )

        return ClauseRedlinesResponse(
            summary=message,
            items=[],
            insufficient_sources=True,
            meta=ClauseRedlinesMeta(
                status=WorkflowResultStatus.CITATION_VIOLATION,
                model=model,
                provider=provider,
                evidence_chunk_count=total_chunks,
                request_id=request_id,
                output_language=output_language,
                jurisdiction=jurisdiction,
                downgraded_count=downgraded_count,
                removed_count=removed_count,
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

        return f"""You are a contract clause analysis specialist. Your role is to identify clause issues and suggest redlines based ONLY on the evidence provided.

CRITICAL REQUIREMENTS:
1. Output MUST be valid JSON matching the specified schema.
2. Any claim about what the CONTRACT says MUST include citations like [1], [2].
3. The "Recommended Text" field contains TEMPLATE text from the clause library - this does NOT need citations.
4. The "issue" field MUST describe problems in the contract WITH citations.
5. The "rationale" field MUST cite the contract if referencing it.
6. If you cannot cite a claim about the contract, mark status as "insufficient_evidence".
7. Do NOT hallucinate or make up information not in the sources.
8. Temperature is 0 - be precise and deterministic.

STRICT RULES FOR CITATIONS:
- Contract claims without citations will be REJECTED
- Template/recommended text does NOT need citations (clearly label it as "Recommended Text")
- Missing clauses should propose template text but NOT claim it exists in the contract

{language_instruction}

OUTPUT FORMAT (strict JSON):
{{
  "summary": "Executive summary with citations to contract excerpts [1][2]...",
  "items": [
    {{
      "clause_type": "governing_law|termination|liability|indemnity|confidentiality|payment|ip|force_majeure",
      "status": "found|missing|insufficient_evidence",
      "confidence": 0.0 to 1.0,
      "issue": "Description of issues in the contract with citations [1]",
      "suggested_redline": "Recommended Text: Template clause language from library",
      "rationale": "Why this change is recommended, citing contract [1] if applicable",
      "severity": "low|medium|high|critical",
      "citations": [1, 2]
    }}
  ]
}}
"""

    def _build_prompt(
        self,
        detection: DocumentClauseDetection,
        evidence_chunks: list[EvidenceChunk],
        evidence_map: dict[ClauseType, list[int]],
        jurisdiction: str,
        output_language: str,
        playbook_hint: str | None = None,
    ) -> str:
        """Build the user prompt with evidence bundle and clause library."""
        prompt_parts = [
            "CLAUSE REDLINES ANALYSIS",
            f"Jurisdiction: {jurisdiction}",
            "",
        ]

        # Prepend playbook hint if provided
        if playbook_hint:
            prompt_parts.append(f"PLAYBOOK GUIDANCE: {playbook_hint}")
            prompt_parts.append("")

        # Add evidence sources
        prompt_parts.append("CONTRACT EVIDENCE SOURCES:")
        prompt_parts.append("")

        for i, chunk in enumerate(evidence_chunks, 1):
            prompt_parts.append(f"[EVIDENCE {i}]")
            if chunk.page_start is not None:
                prompt_parts.append(
                    f"Pages: {chunk.page_start}-{chunk.page_end or chunk.page_start}"
                )
            prompt_parts.append(f"Content:\n{chunk.text}")
            prompt_parts.append("")

        # Add clause library templates
        prompt_parts.append("CLAUSE LIBRARY TEMPLATES:")
        prompt_parts.append(f"(For {jurisdiction} jurisdiction)")
        prompt_parts.append("")

        for clause_type in detection.results.keys():
            template = get_clause_for_jurisdiction(clause_type, jurisdiction)
            if template:
                prompt_parts.append(f"[{clause_type.upper()}]")
                prompt_parts.append(f"Recommended Text: {template.recommended_clause_text}")
                prompt_parts.append(f"Notes: {template.notes}")
                prompt_parts.append("")

        # Add detection hints
        prompt_parts.append("DETECTION HINTS:")
        for clause_type, result in detection.results.items():
            status = "FOUND" if result.found else "NOT FOUND"
            evidence_refs = evidence_map.get(clause_type, [])
            evidence_str = ", ".join(f"[{i}]" for i in evidence_refs) if evidence_refs else "none"
            prompt_parts.append(
                f"- {clause_type}: {status} (confidence: {result.confidence:.2f}, evidence: {evidence_str})"
            )
        prompt_parts.append("")

        # Instructions
        prompt_parts.append("INSTRUCTIONS:")
        prompt_parts.append("1. For each clause type, analyze the contract evidence.")
        prompt_parts.append("2. If clause is FOUND: describe issues with citations, suggest improvements.")
        prompt_parts.append("3. If clause is MISSING: mark as 'missing', suggest adding the template clause.")
        prompt_parts.append("4. If insufficient evidence: mark as 'insufficient_evidence'.")
        prompt_parts.append(f"5. Valid citations are [1] through [{len(evidence_chunks)}] only.")
        prompt_parts.append("6. NEVER claim the contract says something without a citation.")
        prompt_parts.append("7. Template text should be prefixed with 'Recommended Text:'.")
        prompt_parts.append("")
        prompt_parts.append("Output the analysis as valid JSON.")

        return "\n".join(prompt_parts)

    def _process_response(
        self,
        response: str,
        evidence_chunks: list[EvidenceChunk],
        evidence_map: dict[ClauseType, list[int]],
        detection: DocumentClauseDetection,
        jurisdiction: str,
    ) -> StrictCitationResult:
        """Process the LLM response with strict citation enforcement.

        Args:
            response: Raw LLM response (expected to be JSON)
            evidence_chunks: List of evidence chunks
            evidence_map: Map of clause_type to evidence indices
            detection: Detection results
            jurisdiction: Jurisdiction for templates

        Returns:
            StrictCitationResult with validated items
        """
        warnings: list[str] = []
        valid_indices = set(range(1, len(evidence_chunks) + 1))

        # Try to parse JSON
        try:
            json_str = response.strip()
            if json_str.startswith("```"):
                lines = json_str.split("\n")
                json_str = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )

            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            warnings.append(f"Failed to parse JSON response: {str(e)[:100]}")
            return StrictCitationResult(
                summary="Unable to parse analysis results.",
                items=[],
                downgraded_count=0,
                removed_count=0,
                strict_citations_failed=True,
                warnings=warnings,
            )

        # Extract summary
        summary = data.get("summary", "")

        # Process items
        raw_items = data.get("items", [])
        valid_items: list[ClauseRedlineItem] = []
        downgraded_count = 0
        removed_count = 0

        for i, item in enumerate(raw_items):
            try:
                clause_type = item.get("clause_type", "")
                status = item.get("status", "insufficient_evidence")
                issue = item.get("issue", "")
                rationale = item.get("rationale", "")

                # Extract citations from item
                citations = item.get("citations", [])
                if not isinstance(citations, list):
                    citations = []

                # Filter to valid indices
                valid_cites = [c for c in citations if c in valid_indices]

                # Also extract citations from issue and rationale text
                text_citations = self._extract_valid_citations(
                    (issue or "") + " " + (rationale or ""), valid_indices
                )
                valid_cites = list(set(valid_cites) | text_citations)

                # Check for uncited contract claims
                has_contract_claim = self._has_uncited_contract_claim(
                    issue, rationale, valid_cites
                )

                # Get confidence details from detection (v2)
                confidence = item.get("confidence", 0.5)
                confidence_level: ConfidenceLevel = "medium"
                confidence_reason = ""
                detection_result: ClauseDetectionResult | None = None

                if clause_type in detection.results:
                    detection_result = detection.results[clause_type]
                    confidence = detection_result.confidence
                    confidence_level = detection_result.confidence_level
                    confidence_reason = detection_result.confidence_reason

                # Apply v2 status semantics based on confidence level
                has_evidence = bool(detection_result and detection_result.evidence)
                status = self._determine_status_v2(
                    llm_status=status,
                    confidence_level=confidence_level,
                    has_evidence=has_evidence,
                    has_valid_citations=bool(valid_cites),
                )

                # Check if downgraded due to uncited claims
                if item.get("status") == "found" and status == "insufficient_evidence":
                    if has_contract_claim and not valid_cites:
                        downgraded_count += 1
                        warnings.append(
                            f"Downgraded '{clause_type}' to insufficient_evidence: uncited contract claims"
                        )

                # Build evidence references
                evidence_refs = []
                for cite_idx in sorted(valid_cites):
                    if 1 <= cite_idx <= len(evidence_chunks):
                        chunk = evidence_chunks[cite_idx - 1]
                        snippet = (
                            chunk.text[:200] + "..."
                            if len(chunk.text) > 200
                            else chunk.text
                        )
                        evidence_refs.append(
                            EvidenceChunkRef(
                                chunk_id=chunk.chunk_id,
                                snippet=snippet,
                                char_start=chunk.char_start,
                                char_end=chunk.char_end,
                            )
                        )

                # Validate severity
                severity = self._validate_severity(item.get("severity", "medium"))

                valid_items.append(
                    ClauseRedlineItem(
                        clause_type=clause_type,
                        status=status,
                        confidence=confidence,
                        confidence_level=confidence_level,
                        confidence_reason=confidence_reason,
                        issue=issue if issue else None,
                        suggested_redline=item.get("suggested_redline"),
                        rationale=rationale if rationale else None,
                        citations=sorted(valid_cites),
                        evidence=evidence_refs,
                        severity=severity,
                    )
                )

            except Exception as e:
                removed_count += 1
                warnings.append(f"Failed to process item {i}: {str(e)[:50]}")

        # Check if too many items failed
        total_items = len(raw_items)
        failed_items = downgraded_count + removed_count
        strict_failed = total_items > 0 and (failed_items / total_items) > 0.5

        return StrictCitationResult(
            summary=summary,
            items=valid_items,
            downgraded_count=downgraded_count,
            removed_count=removed_count,
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

    def _has_uncited_contract_claim(
        self, issue: str | None, rationale: str | None, citations: list[int]
    ) -> bool:
        """Check if issue/rationale make contract claims without citations.

        Simple heuristic: if text contains phrases like "the contract says",
        "according to the agreement", etc., it should have citations.
        """
        contract_claim_phrases = [
            "contract says",
            "contract states",
            "agreement says",
            "agreement states",
            "document says",
            "document states",
            "clause says",
            "clause states",
            "provides that",
            "stipulates that",
            "currently states",
            "existing clause",
            "current language",
        ]

        combined_text = ((issue or "") + " " + (rationale or "")).lower()

        for phrase in contract_claim_phrases:
            if phrase in combined_text:
                return True

        return False

    def _determine_status_v2(
        self,
        llm_status: str,
        confidence_level: ConfidenceLevel,
        has_evidence: bool,
        has_valid_citations: bool,
    ) -> str:
        """Determine clause status using v2 semantics.

        v2 status rules:
        - "found": confidence_level is high or medium
        - "insufficient_evidence": confidence_level is low but some evidence exists
        - "missing": no evidence at all

        Args:
            llm_status: Status suggested by LLM
            confidence_level: Calibrated confidence level from detection
            has_evidence: Whether detection found any evidence chunks
            has_valid_citations: Whether there are valid citations

        Returns:
            Status string: "found", "missing", or "insufficient_evidence"
        """
        # If LLM says missing and no evidence, it's missing
        if llm_status == "missing" and not has_evidence:
            return "missing"

        # If no evidence at all, it's missing
        if not has_evidence:
            return "missing"

        # Apply v2 confidence-based rules
        if confidence_level in ("high", "medium"):
            # High/medium confidence with evidence = found
            return "found"
        else:
            # Low confidence with some evidence = insufficient_evidence
            return "insufficient_evidence"

    def _validate_severity(self, severity: str) -> Severity:
        """Validate and normalize severity level."""
        valid: set[str] = {"low", "medium", "high", "critical"}
        severity_lower = severity.lower() if severity else "medium"
        return severity_lower if severity_lower in valid else "medium"
