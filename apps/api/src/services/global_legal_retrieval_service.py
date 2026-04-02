"""Retrieval service for hybrid search over global legal corpus chunks.

This service implements:
- Semantic vector search using pgvector (PostgreSQL-native)
- Keyword search using PostgreSQL full-text search
- Hybrid combination with score fusion
- Policy-aware filtering (respects workspace allowed_jurisdictions)

The global legal corpus is NOT tenant-scoped - it's globally accessible
baseline evidence for all tenants. However, policy constraints still apply:
- allowed_jurisdictions: Only return results from jurisdictions allowed by workspace policy

Design principle: Global ≠ unrestricted. Policy is still the gate.
"""

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import and_, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.embeddings import EmbeddingProvider, get_embedding_provider
from src.models.legal_chunk import LegalChunk
from src.models.legal_chunk_embedding import LegalChunkEmbedding
from src.models.legal_instrument import LegalInstrument
from src.models.legal_instrument_version import LegalInstrumentVersion

logger = logging.getLogger(__name__)


@dataclass
class GlobalLegalSearchResult:
    """A single search result from the global legal corpus.

    Provides clear provenance for user trust:
    - source_type: Always "global_legal"
    - source_label: Human-readable label like "Saudi Companies Law (2022)"
    """

    chunk_id: str
    chunk_index: int
    snippet: str

    # Instrument metadata
    instrument_id: str
    version_id: str
    instrument_title: str
    instrument_title_ar: str | None
    instrument_type: str
    jurisdiction: str
    language: str

    # Dates (critical for legal provenance)
    published_at: str | None  # ISO date string
    effective_at: str | None  # ISO date string

    # Official source (for trust/verification)
    official_source_url: str | None

    # Offsets for citation
    char_start: int
    char_end: int
    page_start: int | None
    page_end: int | None

    # Scores
    vector_score: float
    keyword_score: float
    final_score: float

    # Source provenance (user trust)
    source_type: str = "global_legal"
    source_label: str = ""


@dataclass
class GlobalLegalSearchFilters:
    """Optional filters for global legal search."""

    jurisdiction: str | None = None
    instrument_type: str | None = None
    language: str | None = None


@dataclass
class PolicyFilters:
    """Policy-based filters applied from workspace configuration.

    These filters enforce workspace policy on global search results.
    Global ≠ unrestricted. Policy is still the gate.
    """

    # Allowed jurisdictions from workspace policy
    # If set, only return results from these jurisdictions
    allowed_jurisdictions: list[str] = field(default_factory=list)

    # Allowed input languages from workspace policy
    # If set, only return results in these languages
    allowed_input_languages: list[str] = field(default_factory=list)


@dataclass
class PolicyMeta:
    """Metadata about policy enforcement for audit logging.

    Provides structured information about how policy was applied
    during global legal search, supporting audit trail requirements.
    """

    # Whether policy filtering was applied
    policy_applied: bool = True

    # Count of allowed jurisdictions from policy
    policy_jurisdictions_count: int = 0

    # Count of allowed languages from policy
    policy_languages_count: int = 0

    # Reason if search was denied by policy (deny-by-default)
    # Possible values: None, "allowed_jurisdictions_empty", "allowed_input_languages_empty"
    policy_denied_reason: str | None = None

    def to_dict(self) -> dict:
        """Convert to dict for audit logging."""
        return {
            "policy_applied": self.policy_applied,
            "policy_jurisdictions_count": self.policy_jurisdictions_count,
            "policy_languages_count": self.policy_languages_count,
            "policy_denied_reason": self.policy_denied_reason,
        }


@dataclass
class GlobalLegalSearchServiceResponse:
    """Return type for GlobalLegalRetrievalService.search_chunks().

    Provides a structured, typed response rather than a raw tuple.
    This future-proofs the API and improves type safety.

    Usage:
        response = await service.search_chunks(query, ...)
        items = response.items  # List of search results
        meta = response.policy_meta  # Policy enforcement details
    """

    # List of search result items
    items: list[GlobalLegalSearchResult] = field(default_factory=list)

    # Policy enforcement metadata (for audit logging)
    policy_meta: PolicyMeta = field(default_factory=PolicyMeta)


class GlobalLegalRetrievalService:
    """Service for hybrid search over global legal corpus chunks.

    Implements policy-aware filtering:
    - Respects workspace allowed_jurisdictions
    - Respects workspace allowed_input_languages
    - Generates human-readable source_label for trust

    Design principle: Global ≠ unrestricted. Policy is still the gate.
    """

    # Score combination weights
    VECTOR_WEIGHT = 0.6
    KEYWORD_WEIGHT = 0.4

    # Maximum results to fetch for each search leg before combination
    MAX_CANDIDATES = 50

    # Maximum snippet length
    MAX_SNIPPET_LENGTH = 300

    def __init__(
        self,
        db: AsyncSession,
        provider: EmbeddingProvider | None = None,
    ):
        """Initialize the retrieval service.

        Args:
            db: Async database session
            provider: Embedding provider (defaults to global provider)
        """
        self.db = db
        self.provider = provider or get_embedding_provider()

    async def search_chunks(
        self,
        query: str,
        *,
        limit: int = 10,
        filters: GlobalLegalSearchFilters | None = None,
        policy_filters: PolicyFilters | None = None,
    ) -> GlobalLegalSearchServiceResponse:
        """Search for relevant chunks in global legal corpus.

        This method:
        1. Applies deny-by-default policy: empty allowed lists = zero results
        2. Applies policy filters (allowed_jurisdictions, allowed_input_languages)
        3. Runs both vector and keyword search
        4. Combines results using weighted score fusion
        5. Only searches indexed versions

        Design principle: Global ≠ unrestricted. Policy is still the gate.

        Args:
            query: Search query string
            limit: Maximum number of results (default 10, max 50)
            filters: Optional user-specified search filters
            policy_filters: Policy-based filters from workspace configuration.
                           If set, results are restricted to allowed jurisdictions/languages.

        Returns:
            GlobalLegalSearchServiceResponse containing:
            - items: List of GlobalLegalSearchResult objects ordered by relevance
            - policy_meta: PolicyMeta with enforcement details for audit logging
        """
        # Initialize policy metadata for audit logging
        policy_meta = PolicyMeta()

        # Clamp limit
        limit = min(max(1, limit), 50)

        if not query or not query.strip():
            return GlobalLegalSearchServiceResponse(items=[], policy_meta=policy_meta)

        # Ensure filters exist
        if filters is None:
            filters = GlobalLegalSearchFilters()

        # Ensure policy filters exist
        if policy_filters is None:
            policy_filters = PolicyFilters()

        # Update policy metadata
        policy_meta.policy_jurisdictions_count = len(policy_filters.allowed_jurisdictions)
        policy_meta.policy_languages_count = len(policy_filters.allowed_input_languages)

        # =====================================================================
        # DENY-BY-DEFAULT: Empty policy lists mean zero results
        # This is the core security principle: Global ≠ unrestricted
        # =====================================================================
        if not policy_filters.allowed_jurisdictions:
            logger.info(
                "Global search denied: allowed_jurisdictions is empty (deny-by-default)"
            )
            policy_meta.policy_denied_reason = "allowed_jurisdictions_empty"
            return GlobalLegalSearchServiceResponse(items=[], policy_meta=policy_meta)

        if not policy_filters.allowed_input_languages:
            logger.info(
                "Global search denied: allowed_input_languages is empty (deny-by-default)"
            )
            policy_meta.policy_denied_reason = "allowed_input_languages_empty"
            return GlobalLegalSearchServiceResponse(items=[], policy_meta=policy_meta)

        # Run both searches with policy filters applied
        vector_results = await self._vector_search(query, filters, policy_filters)
        keyword_results = await self._keyword_search(query, filters, policy_filters)

        # Combine results using weighted score fusion
        combined = self._combine_results(vector_results, keyword_results)

        # Sort by final score and limit
        combined.sort(key=lambda r: r.final_score, reverse=True)

        # Generate source labels for results
        for r in combined:
            r.source_label = self._generate_source_label(r)

        return GlobalLegalSearchServiceResponse(
            items=combined[:limit],
            policy_meta=policy_meta,
        )

    def _generate_source_label(self, result: GlobalLegalSearchResult) -> str:
        """Generate human-readable source label for trust/transparency.

        Format: "{Instrument Title} ({Year})" or "{Instrument Title}"

        Examples:
        - "Saudi Companies Law (2022)"
        - "DIFC Contract Law (2021)"
        - "UAE Federal Law No. 1"
        """
        title = result.instrument_title
        year = None

        # Extract year from effective_at or published_at
        if result.effective_at:
            year = result.effective_at[:4]  # ISO format: YYYY-MM-DD
        elif result.published_at:
            year = result.published_at[:4]

        if year:
            return f"{title} ({year})"
        return title

    async def _vector_search(
        self,
        query: str,
        filters: GlobalLegalSearchFilters,
        policy_filters: PolicyFilters,
    ) -> list[GlobalLegalSearchResult]:
        """Perform vector similarity search using pgvector in PostgreSQL.

        Applies both user filters and policy filters.

        Args:
            query: Search query
            filters: User-specified search filters
            policy_filters: Policy-based filters from workspace configuration

        Returns:
            List of GlobalLegalSearchResult with vector scores
        """
        # Generate query embedding
        query_embedding = self.provider.embed_query(query)

        # Format query vector for pgvector
        query_vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Compute cosine similarity in PostgreSQL
        cosine_distance = LegalChunkEmbedding.embedding.op("<=>")(
            text(f"'{query_vector_str}'::vector")
        )
        cosine_similarity = (literal(1) - cosine_distance).label("similarity")

        # Build query
        stmt = (
            select(
                LegalChunk,
                cosine_similarity,
                LegalInstrument.title.label("instrument_title"),
                LegalInstrument.title_ar.label("instrument_title_ar"),
                LegalInstrument.instrument_type,
                LegalInstrument.jurisdiction,
                LegalInstrument.published_at,
                LegalInstrument.effective_at,
                LegalInstrument.official_source_url,
                LegalInstrumentVersion.language,
            )
            .join(
                LegalChunkEmbedding,
                LegalChunk.id == LegalChunkEmbedding.chunk_id,
            )
            .join(LegalInstrument, LegalChunk.instrument_id == LegalInstrument.id)
            .join(LegalInstrumentVersion, LegalChunk.version_id == LegalInstrumentVersion.id)
            .where(
                # Only indexed versions
                LegalInstrumentVersion.is_indexed == True  # noqa: E712
            )
        )

        # Apply user-specified filters
        if filters.jurisdiction:
            stmt = stmt.where(LegalInstrument.jurisdiction == filters.jurisdiction)
        if filters.instrument_type:
            stmt = stmt.where(LegalInstrument.instrument_type == filters.instrument_type)
        if filters.language:
            stmt = stmt.where(LegalInstrumentVersion.language == filters.language)

        # Apply policy filters (workspace restrictions)
        # Global ≠ unrestricted. Policy is still the gate.
        if policy_filters.allowed_jurisdictions:
            stmt = stmt.where(
                LegalInstrument.jurisdiction.in_(policy_filters.allowed_jurisdictions)
            )
        if policy_filters.allowed_input_languages:
            stmt = stmt.where(
                LegalInstrumentVersion.language.in_(policy_filters.allowed_input_languages)
            )

        # Order by similarity and limit
        stmt = stmt.order_by(text("similarity DESC")).limit(self.MAX_CANDIDATES)

        # Execute query
        result = await self.db.execute(stmt)
        rows = result.all()

        # Build results
        results: list[GlobalLegalSearchResult] = []
        for row in rows:
            chunk = row[0]
            similarity = float(row[1]) if row[1] is not None else 0.0
            instrument_title = row[2]
            instrument_title_ar = row[3]
            instrument_type = row[4]
            jurisdiction = row[5]
            published_at = row[6]
            effective_at = row[7]
            official_source_url = row[8]
            language = row[9]

            results.append(
                GlobalLegalSearchResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    snippet=self._truncate_snippet(chunk.text),
                    instrument_id=chunk.instrument_id,
                    version_id=chunk.version_id,
                    instrument_title=instrument_title,
                    instrument_title_ar=instrument_title_ar,
                    instrument_type=instrument_type,
                    jurisdiction=jurisdiction,
                    language=language,
                    published_at=published_at.isoformat() if published_at else None,
                    effective_at=effective_at.isoformat() if effective_at else None,
                    official_source_url=official_source_url,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    vector_score=similarity,
                    keyword_score=0.0,
                    final_score=similarity,
                )
            )

        return results

    async def _keyword_search(
        self,
        query: str,
        filters: GlobalLegalSearchFilters,
        policy_filters: PolicyFilters,
    ) -> list[GlobalLegalSearchResult]:
        """Perform keyword search using PostgreSQL full-text search.

        For English text, uses tsvector/tsquery.
        For Arabic/mixed, falls back to ILIKE.

        Args:
            query: Search query
            filters: User-specified search filters
            policy_filters: Policy-based filters from workspace configuration

        Returns:
            List of GlobalLegalSearchResult with keyword scores
        """
        # Detect if query contains Arabic
        has_arabic = bool(re.search(r"[\u0600-\u06FF]", query))

        if has_arabic:
            return await self._keyword_search_ilike(query, filters, policy_filters)
        else:
            return await self._keyword_search_fts(query, filters, policy_filters)

    async def _keyword_search_fts(
        self,
        query: str,
        filters: GlobalLegalSearchFilters,
        policy_filters: PolicyFilters,
    ) -> list[GlobalLegalSearchResult]:
        """Full-text search using PostgreSQL tsvector.

        Args:
            query: Search query (English)
            filters: User-specified search filters
            policy_filters: Policy-based filters from workspace configuration

        Returns:
            List of GlobalLegalSearchResult with keyword scores
        """
        stmt = (
            select(
                LegalChunk,
                func.ts_rank(
                    LegalChunk.text_search_vector,
                    func.plainto_tsquery("english", query),
                ).label("rank"),
                LegalInstrument.title.label("instrument_title"),
                LegalInstrument.title_ar.label("instrument_title_ar"),
                LegalInstrument.instrument_type,
                LegalInstrument.jurisdiction,
                LegalInstrument.published_at,
                LegalInstrument.effective_at,
                LegalInstrument.official_source_url,
                LegalInstrumentVersion.language,
            )
            .join(LegalInstrument, LegalChunk.instrument_id == LegalInstrument.id)
            .join(LegalInstrumentVersion, LegalChunk.version_id == LegalInstrumentVersion.id)
            .where(
                and_(
                    LegalInstrumentVersion.is_indexed == True,  # noqa: E712
                    LegalChunk.text_search_vector.op("@@")(
                        func.plainto_tsquery("english", query)
                    ),
                )
            )
        )

        # Apply user-specified filters
        if filters.jurisdiction:
            stmt = stmt.where(LegalInstrument.jurisdiction == filters.jurisdiction)
        if filters.instrument_type:
            stmt = stmt.where(LegalInstrument.instrument_type == filters.instrument_type)
        if filters.language:
            stmt = stmt.where(LegalInstrumentVersion.language == filters.language)

        # Apply policy filters (workspace restrictions)
        if policy_filters.allowed_jurisdictions:
            stmt = stmt.where(
                LegalInstrument.jurisdiction.in_(policy_filters.allowed_jurisdictions)
            )
        if policy_filters.allowed_input_languages:
            stmt = stmt.where(
                LegalInstrumentVersion.language.in_(policy_filters.allowed_input_languages)
            )

        stmt = stmt.order_by(text("rank DESC")).limit(self.MAX_CANDIDATES)

        result = await self.db.execute(stmt)
        rows = result.all()

        results: list[GlobalLegalSearchResult] = []
        for row in rows:
            chunk = row[0]
            rank = float(row[1]) if row[1] else 0.0
            instrument_title = row[2]
            instrument_title_ar = row[3]
            instrument_type = row[4]
            jurisdiction = row[5]
            published_at = row[6]
            effective_at = row[7]
            official_source_url = row[8]
            language = row[9]

            results.append(
                GlobalLegalSearchResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    snippet=self._truncate_snippet(chunk.text),
                    instrument_id=chunk.instrument_id,
                    version_id=chunk.version_id,
                    instrument_title=instrument_title,
                    instrument_title_ar=instrument_title_ar,
                    instrument_type=instrument_type,
                    jurisdiction=jurisdiction,
                    language=language,
                    published_at=published_at.isoformat() if published_at else None,
                    effective_at=effective_at.isoformat() if effective_at else None,
                    official_source_url=official_source_url,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    vector_score=0.0,
                    keyword_score=rank,
                    final_score=rank,
                )
            )

        return results

    async def _keyword_search_ilike(
        self,
        query: str,
        filters: GlobalLegalSearchFilters,
        policy_filters: PolicyFilters,
    ) -> list[GlobalLegalSearchResult]:
        """Fallback keyword search using ILIKE for Arabic text.

        Args:
            query: Search query (may contain Arabic)
            filters: User-specified search filters
            policy_filters: Policy-based filters from workspace configuration

        Returns:
            List of GlobalLegalSearchResult with keyword scores
        """
        tokens = [t.strip() for t in query.split() if t.strip()]
        if not tokens:
            return []

        like_conditions = [
            LegalChunk.text.ilike(f"%{token}%") for token in tokens
        ]

        stmt = (
            select(
                LegalChunk,
                LegalInstrument.title.label("instrument_title"),
                LegalInstrument.title_ar.label("instrument_title_ar"),
                LegalInstrument.instrument_type,
                LegalInstrument.jurisdiction,
                LegalInstrument.published_at,
                LegalInstrument.effective_at,
                LegalInstrument.official_source_url,
                LegalInstrumentVersion.language,
            )
            .join(LegalInstrument, LegalChunk.instrument_id == LegalInstrument.id)
            .join(LegalInstrumentVersion, LegalChunk.version_id == LegalInstrumentVersion.id)
            .where(
                and_(
                    LegalInstrumentVersion.is_indexed == True,  # noqa: E712
                    or_(*like_conditions),
                )
            )
        )

        # Apply user-specified filters
        if filters.jurisdiction:
            stmt = stmt.where(LegalInstrument.jurisdiction == filters.jurisdiction)
        if filters.instrument_type:
            stmt = stmt.where(LegalInstrument.instrument_type == filters.instrument_type)
        if filters.language:
            stmt = stmt.where(LegalInstrumentVersion.language == filters.language)

        # Apply policy filters (workspace restrictions)
        if policy_filters.allowed_jurisdictions:
            stmt = stmt.where(
                LegalInstrument.jurisdiction.in_(policy_filters.allowed_jurisdictions)
            )
        if policy_filters.allowed_input_languages:
            stmt = stmt.where(
                LegalInstrumentVersion.language.in_(policy_filters.allowed_input_languages)
            )

        stmt = stmt.limit(self.MAX_CANDIDATES)

        result = await self.db.execute(stmt)
        rows = result.all()

        results: list[GlobalLegalSearchResult] = []
        for row in rows:
            chunk = row[0]
            instrument_title = row[1]
            instrument_title_ar = row[2]
            instrument_type = row[3]
            jurisdiction = row[4]
            published_at = row[5]
            effective_at = row[6]
            official_source_url = row[7]
            language = row[8]

            # Score based on token match count
            text_lower = chunk.text.lower()
            match_count = sum(1 for t in tokens if t.lower() in text_lower)
            score = match_count / len(tokens) if tokens else 0.0

            results.append(
                GlobalLegalSearchResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    snippet=self._truncate_snippet(chunk.text),
                    instrument_id=chunk.instrument_id,
                    version_id=chunk.version_id,
                    instrument_title=instrument_title,
                    instrument_title_ar=instrument_title_ar,
                    instrument_type=instrument_type,
                    jurisdiction=jurisdiction,
                    language=language,
                    published_at=published_at.isoformat() if published_at else None,
                    effective_at=effective_at.isoformat() if effective_at else None,
                    official_source_url=official_source_url,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    vector_score=0.0,
                    keyword_score=score,
                    final_score=score,
                )
            )

        return results

    def _combine_results(
        self,
        vector_results: list[GlobalLegalSearchResult],
        keyword_results: list[GlobalLegalSearchResult],
    ) -> list[GlobalLegalSearchResult]:
        """Combine vector and keyword results using weighted score fusion.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search

        Returns:
            Combined results with final scores
        """
        combined: dict[str, GlobalLegalSearchResult] = {}

        # Normalize vector scores
        if vector_results:
            max_vec = max(r.vector_score for r in vector_results)
            min_vec = min(r.vector_score for r in vector_results)
            vec_range = max_vec - min_vec if max_vec != min_vec else 1.0

            for r in vector_results:
                norm_score = (r.vector_score - min_vec) / vec_range
                r.vector_score = norm_score
                combined[r.chunk_id] = r

        # Normalize keyword scores and merge
        if keyword_results:
            max_kw = max(r.keyword_score for r in keyword_results)
            min_kw = min(r.keyword_score for r in keyword_results)
            kw_range = max_kw - min_kw if max_kw != min_kw else 1.0

            for r in keyword_results:
                norm_score = (r.keyword_score - min_kw) / kw_range

                if r.chunk_id in combined:
                    existing = combined[r.chunk_id]
                    existing.keyword_score = norm_score
                else:
                    r.keyword_score = norm_score
                    combined[r.chunk_id] = r

        # Calculate final scores
        for r in combined.values():
            r.final_score = (
                self.VECTOR_WEIGHT * r.vector_score
                + self.KEYWORD_WEIGHT * r.keyword_score
            )

        return list(combined.values())

    def _truncate_snippet(self, text: str) -> str:
        """Truncate text to snippet length.

        Args:
            text: Full chunk text

        Returns:
            Truncated snippet with ellipsis if needed
        """
        if len(text) <= self.MAX_SNIPPET_LENGTH:
            return text
        return text[: self.MAX_SNIPPET_LENGTH - 3] + "..."
