"""Unified Evidence Retrieval Service for Workflows.

This service combines workspace document retrieval and global legal corpus
retrieval into a single unified interface for workflows.

Design principles:
1. Scope-aware: supports "workspace", "global", or "both"
2. Policy-gated: all global retrieval respects workspace policy (deny-by-default)
3. Provenance-explicit: every evidence chunk clearly indicates its source
4. Deterministic: stable ranking and merging for reproducible results

Usage:
    service = UnifiedRetrievalService(db)
    bundle = await service.retrieve_evidence(
        ctx=ctx,
        query="What are the termination provisions?",
        scope="both",
        limit=10,
    )
    # bundle.items contains UnifiedEvidenceChunk from both sources
    # bundle.meta contains counts and policy info
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.services.global_legal_retrieval_service import (
    GlobalLegalRetrievalService,
    GlobalLegalSearchFilters,
    GlobalLegalSearchResult,
    PolicyFilters,
    PolicyMeta,
)
from src.services.policy_service import PolicyService
from src.services.retrieval_service import RetrievalService, SearchFilters, SearchResult

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================


class EvidenceScope(str, Enum):
    """Evidence retrieval scope options."""

    WORKSPACE = "workspace"
    GLOBAL = "global"
    BOTH = "both"


SourceType = Literal["workspace_document", "global_legal"]


@dataclass
class UnifiedEvidenceChunk:
    """A single evidence chunk from either workspace or global legal corpus.

    This normalized representation supports both source types with explicit
    provenance for user trust and audit requirements.
    """

    # =========================================================================
    # Core identification (required for all evidence)
    # =========================================================================
    chunk_id: str
    chunk_index: int
    snippet: str

    # =========================================================================
    # Source provenance (required - user trust)
    # =========================================================================
    source_type: SourceType
    source_label: str  # Human-readable label (e.g., "Saudi Companies Law (2022)")

    # =========================================================================
    # Scores (for ranking)
    # =========================================================================
    score: float = 0.0
    vector_score: float = 0.0
    keyword_score: float = 0.0

    # =========================================================================
    # Location/citation (for all sources)
    # =========================================================================
    char_start: int = 0
    char_end: int = 0
    page_start: int | None = None
    page_end: int | None = None

    # =========================================================================
    # Document metadata (workspace documents)
    # =========================================================================
    document_id: str | None = None
    version_id: str | None = None
    document_title: str | None = None
    document_type: str | None = None

    # =========================================================================
    # Instrument metadata (global legal)
    # =========================================================================
    instrument_id: str | None = None
    instrument_title: str | None = None
    instrument_title_ar: str | None = None
    instrument_type: str | None = None

    # =========================================================================
    # Common metadata
    # =========================================================================
    jurisdiction: str | None = None
    language: str | None = None

    # =========================================================================
    # Legal provenance (global legal)
    # =========================================================================
    published_at: str | None = None  # ISO date string
    effective_at: str | None = None  # ISO date string
    official_source_url: str | None = None


@dataclass
class UnifiedRetrievalMeta:
    """Metadata about the unified retrieval operation.

    Contains counts, policy information, and any denial reasons for audit.
    """

    # Scope used for retrieval
    evidence_scope: str = "workspace"

    # Evidence counts by source
    workspace_evidence_count: int = 0
    global_evidence_count: int = 0
    total_evidence_count: int = 0

    # Policy metadata
    policy_applied: bool = True
    policy_jurisdictions_count: int = 0
    policy_languages_count: int = 0
    policy_denied_reason: str | None = None

    def to_dict(self) -> dict:
        """Convert to dict for audit logging."""
        return {
            "evidence_scope": self.evidence_scope,
            "workspace_evidence_count": self.workspace_evidence_count,
            "global_evidence_count": self.global_evidence_count,
            "total_evidence_count": self.total_evidence_count,
            "policy_applied": self.policy_applied,
            "policy_jurisdictions_count": self.policy_jurisdictions_count,
            "policy_languages_count": self.policy_languages_count,
            "policy_denied_reason": self.policy_denied_reason,
        }


@dataclass
class UnifiedEvidenceBundle:
    """Return type for UnifiedRetrievalService.retrieve_evidence().

    Contains the merged evidence items and metadata about the retrieval.
    """

    # List of unified evidence items, ordered by score
    items: list[UnifiedEvidenceChunk] = field(default_factory=list)

    # Retrieval metadata (for audit and display)
    meta: UnifiedRetrievalMeta = field(default_factory=UnifiedRetrievalMeta)


# =============================================================================
# Unified Retrieval Service
# =============================================================================


class UnifiedRetrievalService:
    """Unified evidence retrieval across workspace and global legal sources.

    This service:
    1. Respects evidence_scope to determine which sources to query
    2. Enforces workspace policy on all retrievals
    3. Normalizes results into UnifiedEvidenceChunk format
    4. Merges and ranks results deterministically

    Ranking strategy for scope="both":
    - Get top N from each source
    - Normalize scores within each source (min-max)
    - Sort by normalized score descending
    - Tie-breaker: source_type (workspace before global), then chunk_index asc

    This ensures deterministic, reproducible ordering.
    """

    # Default limits per source when scope="both"
    DEFAULT_LIMIT_PER_SOURCE_RESEARCH = 8
    DEFAULT_LIMIT_PER_SOURCE_CONTRACT = 20

    def __init__(self, db: AsyncSession):
        """Initialize the unified retrieval service.

        Args:
            db: Async database session
        """
        self.db = db
        self.workspace_retrieval = RetrievalService(db)
        self.global_retrieval = GlobalLegalRetrievalService(db)
        self.policy_service = PolicyService(db)

    async def retrieve_evidence(
        self,
        ctx: RequestContext,
        query: str,
        *,
        scope: EvidenceScope | str = EvidenceScope.WORKSPACE,
        limit: int = 10,
        workspace_filters: SearchFilters | None = None,
        global_filters: GlobalLegalSearchFilters | None = None,
        limit_per_source: int | None = None,
    ) -> UnifiedEvidenceBundle:
        """Retrieve evidence from the specified scope(s).

        Args:
            ctx: Request context with tenant/workspace info
            query: Search query string
            scope: Evidence scope ("workspace", "global", or "both")
            limit: Maximum total results to return
            workspace_filters: Optional filters for workspace search
            global_filters: Optional filters for global legal search
            limit_per_source: When scope="both", limit per source before merging

        Returns:
            UnifiedEvidenceBundle with items and metadata
        """
        # Normalize scope
        if isinstance(scope, str):
            scope = EvidenceScope(scope)

        # Resolve policy for the workspace
        resolved_policy = await self.policy_service.resolve(ctx)

        # Build policy filters for global search
        policy_filters = PolicyFilters(
            allowed_jurisdictions=resolved_policy.config.allowed_jurisdictions or [],
            allowed_input_languages=resolved_policy.config.allowed_input_languages or [],
        )

        # Initialize metadata
        meta = UnifiedRetrievalMeta(
            evidence_scope=scope.value,
            policy_applied=True,
            policy_jurisdictions_count=len(policy_filters.allowed_jurisdictions),
            policy_languages_count=len(policy_filters.allowed_input_languages),
        )

        workspace_items: list[UnifiedEvidenceChunk] = []
        global_items: list[UnifiedEvidenceChunk] = []

        # Determine per-source limit for "both" scope
        per_source_limit = limit_per_source or limit

        # Retrieve from workspace if scope includes it
        if scope in (EvidenceScope.WORKSPACE, EvidenceScope.BOTH):
            workspace_results = await self.workspace_retrieval.search_chunks(
                ctx,
                query,
                limit=per_source_limit if scope == EvidenceScope.BOTH else limit,
                filters=workspace_filters,
            )
            workspace_items = self._convert_workspace_results(workspace_results)
            meta.workspace_evidence_count = len(workspace_items)

        # Retrieve from global if scope includes it
        if scope in (EvidenceScope.GLOBAL, EvidenceScope.BOTH):
            global_response = await self.global_retrieval.search_chunks(
                query,
                limit=per_source_limit if scope == EvidenceScope.BOTH else limit,
                filters=global_filters,
                policy_filters=policy_filters,
            )
            global_items = self._convert_global_results(global_response.items)
            meta.global_evidence_count = len(global_items)

            # Capture policy denial reason if any
            if global_response.policy_meta.policy_denied_reason:
                meta.policy_denied_reason = global_response.policy_meta.policy_denied_reason

        # Merge and rank results
        if scope == EvidenceScope.BOTH:
            merged = self._merge_and_rank(workspace_items, global_items)
        elif scope == EvidenceScope.WORKSPACE:
            merged = workspace_items
        else:  # GLOBAL
            merged = global_items

        # Apply final limit
        final_items = merged[:limit]
        meta.total_evidence_count = len(final_items)

        return UnifiedEvidenceBundle(items=final_items, meta=meta)

    def _convert_workspace_results(
        self, results: list[SearchResult]
    ) -> list[UnifiedEvidenceChunk]:
        """Convert workspace search results to unified format."""
        return [
            UnifiedEvidenceChunk(
                chunk_id=r.chunk_id,
                chunk_index=r.chunk_index,
                snippet=r.snippet,
                source_type="workspace_document",
                source_label=r.document_title,
                score=r.final_score,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score,
                char_start=r.char_start,
                char_end=r.char_end,
                page_start=r.page_start,
                page_end=r.page_end,
                document_id=r.document_id,
                version_id=r.version_id,
                document_title=r.document_title,
                document_type=r.document_type,
                jurisdiction=r.jurisdiction,
                language=r.language,
            )
            for r in results
        ]

    def _convert_global_results(
        self, results: list[GlobalLegalSearchResult]
    ) -> list[UnifiedEvidenceChunk]:
        """Convert global legal search results to unified format."""
        return [
            UnifiedEvidenceChunk(
                chunk_id=r.chunk_id,
                chunk_index=r.chunk_index,
                snippet=r.snippet,
                source_type="global_legal",
                source_label=r.source_label,
                score=r.final_score,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score,
                char_start=r.char_start,
                char_end=r.char_end,
                page_start=r.page_start,
                page_end=r.page_end,
                version_id=r.version_id,
                instrument_id=r.instrument_id,
                instrument_title=r.instrument_title,
                instrument_title_ar=r.instrument_title_ar,
                instrument_type=r.instrument_type,
                jurisdiction=r.jurisdiction,
                language=r.language,
                published_at=r.published_at,
                effective_at=r.effective_at,
                official_source_url=r.official_source_url,
            )
            for r in results
        ]

    def _merge_and_rank(
        self,
        workspace_items: list[UnifiedEvidenceChunk],
        global_items: list[UnifiedEvidenceChunk],
    ) -> list[UnifiedEvidenceChunk]:
        """Merge and rank results from both sources deterministically.

        Ranking strategy:
        1. Normalize scores within each source (min-max normalization)
        2. Combine all items
        3. Sort by normalized score descending
        4. Tie-breakers:
           - source_type: "workspace_document" before "global_legal"
           - chunk_index: ascending

        Args:
            workspace_items: Items from workspace search
            global_items: Items from global legal search

        Returns:
            Merged and ranked list of items
        """
        # Normalize workspace scores
        if workspace_items:
            workspace_items = self._normalize_scores(workspace_items)

        # Normalize global scores
        if global_items:
            global_items = self._normalize_scores(global_items)

        # Combine all items
        all_items = workspace_items + global_items

        # Sort with stable tie-breakers
        # Primary: score descending
        # Secondary: source_type (workspace=0, global=1) - workspace first
        # Tertiary: chunk_index ascending
        all_items.sort(
            key=lambda x: (
                -x.score,  # Higher score first
                0 if x.source_type == "workspace_document" else 1,  # Workspace first
                x.chunk_index,  # Lower chunk_index first
            )
        )

        return all_items

    def _normalize_scores(
        self, items: list[UnifiedEvidenceChunk]
    ) -> list[UnifiedEvidenceChunk]:
        """Normalize scores to [0, 1] range using min-max normalization.

        Args:
            items: List of evidence chunks

        Returns:
            Same items with normalized scores
        """
        if not items:
            return items

        scores = [item.score for item in items]
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score if max_score != min_score else 1.0

        for item in items:
            item.score = (item.score - min_score) / score_range

        return items
