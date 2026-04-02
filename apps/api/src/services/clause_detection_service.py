"""Clause detection service for CLAUSE_REDLINES_V1 workflow (v2).

This service provides deterministic clause detection using keyword triggers,
heading detection, and negative scoring heuristics.
No LLM calls are made - this is a pure heuristic-based service.

v2 improvements:
- Heading/clause-title detection with significant score boost
- Neighbor chunk inclusion for context
- Negative scoring for signature blocks, annexes, TOC
- Confidence calibration with level and reason
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clause_library import RISK_TRIGGERS, ClauseType, get_clause_types
from src.dependencies.auth import RequestContext
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_version import DocumentVersion

logger = logging.getLogger(__name__)


# Maximum evidence chunks per clause type (increased for neighbor inclusion)
MAX_EVIDENCE_PER_CLAUSE = 5

# Minimum confidence threshold to consider a clause "found"
MIN_CONFIDENCE_THRESHOLD = 0.3

# Confidence level thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.7
MEDIUM_CONFIDENCE_THRESHOLD = 0.4

# Heading detection boost multiplier
HEADING_BOOST = 3.0

# Negative scoring penalty
NEGATIVE_PENALTY = -5.0

# Confidence level type
ConfidenceLevel = Literal["high", "medium", "low"]

# ------------------------------------------------------------------
# Heading patterns for clause-title detection
# ------------------------------------------------------------------

# Numbered heading pattern: e.g., "1.", "1.1", "2.3.1 TERMINATION"
NUMBERED_HEADING_PATTERN = re.compile(
    r"^\s*\d+(\.\d+)*\.?\s+[A-Z]",
    re.MULTILINE,
)

# Common clause headings mapped to clause types
CLAUSE_HEADING_PATTERNS: dict[ClauseType, list[re.Pattern]] = {
    "governing_law": [
        re.compile(r"\b(governing\s+law|applicable\s+law|choice\s+of\s+law|jurisdiction)\b", re.IGNORECASE),
    ],
    "termination": [
        re.compile(r"\b(termination|term\s+and\s+termination|duration\s+and\s+termination)\b", re.IGNORECASE),
    ],
    "liability": [
        re.compile(r"\b(liabilit(y|ies)|limitation\s+of\s+liability|exclusion\s+of\s+liability)\b", re.IGNORECASE),
    ],
    "indemnity": [
        re.compile(r"\b(indemnit(y|ies)|indemnification|hold\s+harmless)\b", re.IGNORECASE),
    ],
    "confidentiality": [
        re.compile(r"\b(confidentialit(y|ies)|non-?disclosure|proprietary\s+information)\b", re.IGNORECASE),
    ],
    "payment": [
        re.compile(r"\b(payment|payment\s+terms|fees|compensation|remuneration)\b", re.IGNORECASE),
    ],
    "ip": [
        re.compile(r"\b(intellectual\s+property|ip\s+rights|copyright|patents?|trademarks?)\b", re.IGNORECASE),
    ],
    "force_majeure": [
        re.compile(r"\b(force\s+majeure|act\s+of\s+god|extraordinary\s+events?)\b", re.IGNORECASE),
    ],
}

# ------------------------------------------------------------------
# Negative scoring patterns (signature blocks, annexes, TOC, etc.)
# ------------------------------------------------------------------

NEGATIVE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Signature blocks
    (re.compile(r"^\s*(signature|signed|executed|witness|in\s+witness\s+whereof)", re.IGNORECASE | re.MULTILINE), "signature_block"),
    (re.compile(r"^\s*(by|name|title|date)\s*:\s*_{2,}", re.IGNORECASE | re.MULTILINE), "signature_block"),
    (re.compile(r"\bauthorized\s+signator(y|ies)\b", re.IGNORECASE), "signature_block"),
    # Annex / Schedule headers
    (re.compile(r"^\s*(annex|schedule|appendix|exhibit|attachment)\s+[A-Z0-9]", re.IGNORECASE | re.MULTILINE), "annex_header"),
    # Table of contents
    (re.compile(r"\b(table\s+of\s+contents?|contents)\b", re.IGNORECASE), "toc"),
    (re.compile(r"\.{5,}\s*\d+", re.MULTILINE), "toc"),  # "Section Name ......... 5"
    # Definitions section (usually not a clause itself)
    (re.compile(r"^\s*(definitions?|interpretation)\s*$", re.IGNORECASE | re.MULTILINE), "definitions"),
    # Recitals / whereas clauses
    (re.compile(r"^\s*(whereas|recitals?|background)\s*:?\s*$", re.IGNORECASE | re.MULTILINE), "recitals"),
]


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
    score: float  # Clause-relevance score


@dataclass
class ClauseDetectionResult:
    """Result of clause detection for a single clause type."""

    clause_type: ClauseType
    found: bool
    confidence: float
    confidence_level: ConfidenceLevel
    confidence_reason: str
    evidence: list[EvidenceChunk] = field(default_factory=list)


@dataclass
class DocumentClauseDetection:
    """Complete clause detection results for a document."""

    document_id: str
    version_id: str
    jurisdiction: str
    results: dict[ClauseType, ClauseDetectionResult] = field(default_factory=dict)
    all_chunks: list[EvidenceChunk] = field(default_factory=list)


class ClauseDetectionService:
    """Service for deterministic clause detection in contracts.

    This service:
    1. Loads chunks for a document version
    2. Scores each chunk against clause-type keyword triggers
    3. Returns top N chunks as evidence for each clause type
    4. All ranking is deterministic (tie-breaker: chunk_index asc)
    """

    def __init__(self, db: AsyncSession):
        """Initialize the clause detection service.

        Args:
            db: Async database session
        """
        self.db = db

    async def detect_clauses(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
        clause_types: list[ClauseType] | None = None,
    ) -> DocumentClauseDetection:
        """Detect clauses in a document version.

        Args:
            ctx: Request context with tenant/workspace info
            document_id: ID of the document
            version_id: ID of the version to analyze
            clause_types: Optional list of clause types to detect (default: all)

        Returns:
            DocumentClauseDetection with results per clause type
        """
        # Verify document/version access and get jurisdiction
        document, version = await self._verify_document_access(
            ctx, document_id, version_id
        )

        # Default to all clause types if not specified
        if clause_types is None:
            clause_types = get_clause_types()

        # Fetch all chunks for this version
        chunks = await self._fetch_chunks(ctx, document_id, version_id)

        # Convert to EvidenceChunk objects
        all_chunks = [
            EvidenceChunk(
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                score=0.0,  # Will be updated per clause type
            )
            for chunk in chunks
        ]

        # Detect each clause type
        results: dict[ClauseType, ClauseDetectionResult] = {}
        for clause_type in clause_types:
            result = self._detect_clause_type(clause_type, all_chunks)
            results[clause_type] = result

        return DocumentClauseDetection(
            document_id=document_id,
            version_id=version_id,
            jurisdiction=document.jurisdiction or "UAE",
            results=results,
            all_chunks=all_chunks,
        )

    async def _verify_document_access(
        self, ctx: RequestContext, document_id: str, version_id: str
    ) -> tuple[Document, DocumentVersion]:
        """Verify document and version belong to workspace.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            Tuple of (Document, DocumentVersion)

        Raises:
            ValueError: If document/version not found
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

    async def _fetch_chunks(
        self, ctx: RequestContext, document_id: str, version_id: str
    ) -> list[DocumentChunk]:
        """Fetch all chunks for a document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            List of DocumentChunk objects ordered by chunk_index
        """
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
        return list(result.scalars().all())

    def _detect_clause_type(
        self, clause_type: ClauseType, chunks: list[EvidenceChunk]
    ) -> ClauseDetectionResult:
        """Detect a specific clause type in the document chunks (v2).

        v2 improvements:
        - Heading detection with score boost
        - Negative scoring for signature/annex/TOC chunks
        - Neighbor chunk inclusion for context
        - Confidence level and reason

        Args:
            clause_type: The clause type to detect
            chunks: List of all document chunks

        Returns:
            ClauseDetectionResult with detection status, evidence, and confidence details
        """
        # Get risk triggers for this clause type
        triggers = RISK_TRIGGERS.get(clause_type, [])
        if not triggers:
            return ClauseDetectionResult(
                clause_type=clause_type,
                found=False,
                confidence=0.0,
                confidence_level="low",
                confidence_reason="No triggers defined for clause type",
                evidence=[],
            )

        # Score each chunk with v2 logic
        scored_chunks: list[tuple[EvidenceChunk, float, dict]] = []
        for chunk in chunks:
            score, scoring_info = self._score_chunk_v2(chunk.text, triggers, clause_type)
            if score > 0:
                scored_chunks.append((chunk, score, scoring_info))

        if not scored_chunks:
            return ClauseDetectionResult(
                clause_type=clause_type,
                found=False,
                confidence=0.0,
                confidence_level="low",
                confidence_reason="No matching triggers found",
                evidence=[],
            )

        # Sort by score desc, then chunk_index asc for deterministic ordering
        scored_chunks.sort(key=lambda x: (-x[1], x[0].chunk_index))

        # Select best chunk and include neighbors
        evidence_with_neighbors = self._include_neighbor_chunks(
            scored_chunks, chunks
        )

        # Calculate overall confidence (average of top chunk scores, normalized)
        max_possible_score = len(triggers) + HEADING_BOOST  # If all triggers match + heading
        top_scores = [s for _, s, _ in scored_chunks[:3]]  # Use top 3 for confidence calc
        avg_score = sum(top_scores) / len(top_scores)
        confidence = min(avg_score / max(max_possible_score * 0.3, 1), 1.0)
        confidence = round(max(0.0, confidence), 3)

        # Determine confidence level and reason
        confidence_level, confidence_reason = self._calculate_confidence_details(
            confidence, scored_chunks[:3]
        )

        # Determine if found based on confidence level
        found = confidence_level in ("high", "medium")

        return ClauseDetectionResult(
            clause_type=clause_type,
            found=found,
            confidence=confidence,
            confidence_level=confidence_level,
            confidence_reason=confidence_reason,
            evidence=evidence_with_neighbors,
        )

    def _score_chunk_v2(
        self, text: str, triggers: list[str], clause_type: ClauseType
    ) -> tuple[float, dict]:
        """Score a chunk with v2 logic (heading boost, negative scoring).

        Args:
            text: Chunk text
            triggers: List of trigger keywords
            clause_type: The clause type being detected

        Returns:
            Tuple of (score, scoring_info dict)
        """
        text_lower = text.lower()
        score = 0.0
        scoring_info: dict = {
            "trigger_matches": 0,
            "heading_match": False,
            "negative_match": None,
        }

        # Count trigger matches
        for trigger in triggers:
            if trigger.lower() in text_lower:
                score += 1.0
                scoring_info["trigger_matches"] += 1

        # Check for heading match (significant boost)
        if self._has_heading_match(text, clause_type):
            score += HEADING_BOOST
            scoring_info["heading_match"] = True

        # Check for negative patterns (penalty)
        negative_type = self._check_negative_patterns(text)
        if negative_type:
            score += NEGATIVE_PENALTY
            scoring_info["negative_match"] = negative_type

        return score, scoring_info

    def _has_heading_match(self, text: str, clause_type: ClauseType) -> bool:
        """Check if text contains a heading matching the clause type.

        Args:
            text: Chunk text
            clause_type: The clause type to check

        Returns:
            True if a matching heading is found
        """
        # Check for numbered heading pattern
        has_numbered = bool(NUMBERED_HEADING_PATTERN.search(text))

        # Check for clause-specific heading
        patterns = CLAUSE_HEADING_PATTERNS.get(clause_type, [])
        for pattern in patterns:
            if pattern.search(text):
                # Extra confidence if it's in a numbered heading context
                return True

        return False

    def _check_negative_patterns(self, text: str) -> str | None:
        """Check if text matches any negative patterns.

        Args:
            text: Chunk text

        Returns:
            Name of matched negative pattern, or None
        """
        for pattern, name in NEGATIVE_PATTERNS:
            if pattern.search(text):
                return name
        return None

    def _include_neighbor_chunks(
        self,
        scored_chunks: list[tuple[EvidenceChunk, float, dict]],
        all_chunks: list[EvidenceChunk],
    ) -> list[EvidenceChunk]:
        """Include neighbor chunks for the best matches.

        For each top-scoring chunk, include its immediate neighbors
        (chunk_index - 1 and chunk_index + 1) if they exist.

        Args:
            scored_chunks: List of (chunk, score, info) tuples sorted by score
            all_chunks: List of all chunks in document order

        Returns:
            De-duplicated list of evidence chunks (max MAX_EVIDENCE_PER_CLAUSE)
        """
        # Build index lookup
        chunk_by_index: dict[int, EvidenceChunk] = {
            c.chunk_index: c for c in all_chunks
        }

        # Collect evidence chunks with neighbors
        seen_indices: set[int] = set()
        evidence: list[EvidenceChunk] = []

        # Take top 2 scored chunks and include their neighbors
        for chunk, score, info in scored_chunks[:2]:
            for offset in [0, -1, 1]:  # Self, previous, next
                target_idx = chunk.chunk_index + offset
                if target_idx in seen_indices:
                    continue
                if target_idx in chunk_by_index:
                    neighbor = chunk_by_index[target_idx]
                    # Don't include if it has strong negative scoring
                    if self._check_negative_patterns(neighbor.text):
                        continue
                    # Create evidence chunk with appropriate score
                    ev_score = score if offset == 0 else score * 0.5
                    evidence.append(
                        EvidenceChunk(
                            chunk_id=neighbor.chunk_id,
                            chunk_index=neighbor.chunk_index,
                            text=neighbor.text,
                            char_start=neighbor.char_start,
                            char_end=neighbor.char_end,
                            page_start=neighbor.page_start,
                            page_end=neighbor.page_end,
                            score=ev_score,
                        )
                    )
                    seen_indices.add(target_idx)

            if len(evidence) >= MAX_EVIDENCE_PER_CLAUSE:
                break

        # Sort by chunk_index for coherent reading order
        evidence.sort(key=lambda c: c.chunk_index)

        return evidence[:MAX_EVIDENCE_PER_CLAUSE]

    def _calculate_confidence_details(
        self,
        confidence: float,
        top_scored: list[tuple[EvidenceChunk, float, dict]],
    ) -> tuple[ConfidenceLevel, str]:
        """Calculate confidence level and generate explanation.

        Args:
            confidence: Normalized confidence score (0..1)
            top_scored: Top scored chunks with their info

        Returns:
            Tuple of (confidence_level, confidence_reason)
        """
        # Collect scoring info from top chunks
        total_triggers = sum(info.get("trigger_matches", 0) for _, _, info in top_scored)
        has_heading = any(info.get("heading_match", False) for _, _, info in top_scored)

        # Build reason components
        reason_parts: list[str] = []

        if has_heading:
            reason_parts.append("Matched heading")

        if total_triggers > 0:
            reason_parts.append(f"{total_triggers} trigger(s)")

        if not reason_parts:
            reason_parts.append("Weak signal")

        # Determine level
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            level: ConfidenceLevel = "high"
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            level = "medium"
        else:
            level = "low"

        reason = " + ".join(reason_parts)
        return level, reason

    def _score_chunk(self, text: str, triggers: list[str]) -> float:
        """Score a chunk based on keyword trigger matches (legacy v1 method).

        Kept for backwards compatibility. Use _score_chunk_v2 for v2 detection.

        Args:
            text: Chunk text
            triggers: List of trigger keywords

        Returns:
            Score (number of trigger matches)
        """
        text_lower = text.lower()
        score = 0.0

        for trigger in triggers:
            if trigger.lower() in text_lower:
                score += 1.0

        return score
