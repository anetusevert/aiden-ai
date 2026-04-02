"""Retrieval service for hybrid search over document chunks.

This service implements:
- Semantic vector search using pgvector (PostgreSQL-native)
- Keyword search using PostgreSQL full-text search
- Hybrid combination with score fusion
- Tenant/workspace isolation
- Policy constraint enforcement

Vector similarity is computed IN PostgreSQL using pgvector operators,
not in Python. This ensures efficient, scalable search.
"""

import logging
import re
from dataclasses import dataclass

from sqlalchemy import and_, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.embeddings import EmbeddingProvider, get_embedding_provider
from src.models.document import Document
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_embedding import DocumentChunkEmbedding
from src.models.document_version import DocumentVersion
from src.schemas.policy import ResolvedPolicy
from src.services.policy_service import PolicyService

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result with scores and metadata."""

    chunk_id: str
    chunk_index: int
    snippet: str
    document_id: str
    version_id: str
    document_title: str
    document_type: str
    jurisdiction: str
    language: str
    char_start: int
    char_end: int
    page_start: int | None
    page_end: int | None
    vector_score: float
    keyword_score: float
    final_score: float


@dataclass
class SearchFilters:
    """Optional filters for search queries."""

    document_type: str | None = None
    jurisdiction: str | None = None
    language: str | None = None
    include_unindexed: bool = False  # If True, include unindexed versions


class RetrievalService:
    """Service for hybrid search over document chunks."""

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
        self.policy_service = PolicyService(db)

    async def search_chunks(
        self,
        ctx: RequestContext,
        query: str,
        *,
        limit: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]:
        """Search for relevant chunks using hybrid vector + keyword search.

        This method:
        1. Resolves policy constraints for the workspace
        2. Runs both vector and keyword search (only indexed versions by default)
        3. Combines results using weighted score fusion
        4. Enforces tenant/workspace isolation and policy constraints

        By default, only searches indexed versions (is_indexed=True).
        Set filters.include_unindexed=True to include unindexed versions.

        Args:
            ctx: Request context with tenant/workspace info
            query: Search query string
            limit: Maximum number of results (default 10, max 50)
            filters: Optional search filters including include_unindexed

        Returns:
            List of SearchResult objects ordered by relevance
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        # Clamp limit
        limit = min(max(1, limit), 50)

        if not query or not query.strip():
            return []

        # Ensure filters exist
        if filters is None:
            filters = SearchFilters()

        # Resolve policy for constraint checking
        resolved_policy = await self.policy_service.resolve(ctx)

        # Run both searches in parallel-ish (async)
        vector_results = await self._vector_search(
            ctx, query, resolved_policy, filters
        )
        keyword_results = await self._keyword_search(
            ctx, query, resolved_policy, filters
        )

        # Combine results using reciprocal rank fusion
        combined = self._combine_results(vector_results, keyword_results)

        # Sort by final score and limit
        combined.sort(key=lambda r: r.final_score, reverse=True)
        return combined[:limit]

    async def _vector_search(
        self,
        ctx: RequestContext,
        query: str,
        policy: ResolvedPolicy,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Perform vector similarity search using pgvector in PostgreSQL.

        Vector similarity is computed directly in PostgreSQL using pgvector's
        cosine distance operator (<=>), not in Python. This is efficient and scalable.

        Args:
            ctx: Request context
            query: Search query
            policy: Resolved policy for constraints
            filters: Optional filters

        Returns:
            List of SearchResult with vector scores
        """
        # Generate query embedding
        query_embedding = self.provider.embed_query(query)

        # Format query vector for pgvector (as string '[v1,v2,...]')
        query_vector_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Compute cosine similarity in PostgreSQL using pgvector
        # pgvector's <=> operator returns cosine DISTANCE (0 = identical, 2 = opposite)
        # We convert to similarity: 1 - (distance / 2) for [0,1] range
        # Or simply: 1 - distance for cosine distance where distance is in [0,2]
        cosine_distance = DocumentChunkEmbedding.embedding.op("<=>")(
            text(f"'{query_vector_str}'::vector")
        )
        # Convert distance to similarity score (1 = identical, 0 = orthogonal, -1 = opposite)
        cosine_similarity = (literal(1) - cosine_distance).label("similarity")

        # Build query with similarity computed in PostgreSQL
        stmt = (
            select(
                DocumentChunk,
                cosine_similarity,
                Document.title.label("document_title"),
                Document.document_type,
                Document.jurisdiction,
                Document.language,
            )
            .join(
                DocumentChunkEmbedding,
                DocumentChunk.id == DocumentChunkEmbedding.chunk_id,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(
                and_(
                    DocumentChunk.tenant_id == ctx.tenant.id,
                    DocumentChunk.workspace_id == ctx.workspace.id,
                )
            )
        )

        # Filter by indexed status (default: only indexed versions)
        if filters is None or not filters.include_unindexed:
            stmt = stmt.where(DocumentVersion.is_indexed == True)  # noqa: E712

        # Apply policy constraints
        if policy.config.allowed_jurisdictions:
            stmt = stmt.where(
                Document.jurisdiction.in_(policy.config.allowed_jurisdictions)
            )
        if policy.config.allowed_input_languages:
            stmt = stmt.where(
                Document.language.in_(policy.config.allowed_input_languages)
            )

        # Apply filters
        if filters:
            if filters.document_type:
                stmt = stmt.where(Document.document_type == filters.document_type)
            if filters.jurisdiction:
                stmt = stmt.where(Document.jurisdiction == filters.jurisdiction)
            if filters.language:
                stmt = stmt.where(Document.language == filters.language)

        # Order by similarity (descending) and limit
        stmt = stmt.order_by(text("similarity DESC")).limit(self.MAX_CANDIDATES)

        # Execute query - similarity computed in PostgreSQL
        result = await self.db.execute(stmt)
        rows = result.all()

        # Build results from database response
        results: list[SearchResult] = []
        for row in rows:
            chunk = row[0]
            similarity = float(row[1]) if row[1] is not None else 0.0
            doc_title = row[2]
            doc_type = row[3]
            jurisdiction = row[4]
            language = row[5]

            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    snippet=self._truncate_snippet(chunk.text),
                    document_id=chunk.document_id,
                    version_id=chunk.version_id,
                    document_title=doc_title,
                    document_type=doc_type,
                    jurisdiction=jurisdiction,
                    language=language,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    vector_score=similarity,
                    keyword_score=0.0,
                    final_score=similarity,  # Will be recalculated in combine
                )
            )

        return results

    async def _keyword_search(
        self,
        ctx: RequestContext,
        query: str,
        policy: ResolvedPolicy,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Perform keyword search using PostgreSQL full-text search.

        For English text, uses tsvector/tsquery.
        For Arabic/mixed, falls back to ILIKE.

        Args:
            ctx: Request context
            query: Search query
            policy: Resolved policy for constraints
            filters: Optional filters

        Returns:
            List of SearchResult with keyword scores
        """
        # Detect if query contains Arabic
        has_arabic = bool(re.search(r"[\u0600-\u06FF]", query))

        if has_arabic:
            return await self._keyword_search_ilike(ctx, query, policy, filters)
        else:
            return await self._keyword_search_fts(ctx, query, policy, filters)

    async def _keyword_search_fts(
        self,
        ctx: RequestContext,
        query: str,
        policy: ResolvedPolicy,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Full-text search using PostgreSQL tsvector.

        Args:
            ctx: Request context
            query: Search query (English)
            policy: Resolved policy
            filters: Optional filters

        Returns:
            List of SearchResult with keyword scores
        """
        # Build tsquery from search terms
        # Use plainto_tsquery for simple queries
        stmt = (
            select(
                DocumentChunk,
                func.ts_rank(
                    DocumentChunk.text_search_vector,
                    func.plainto_tsquery("english", query),
                ).label("rank"),
                Document.title.label("document_title"),
                Document.document_type,
                Document.jurisdiction,
                Document.language,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(
                and_(
                    DocumentChunk.tenant_id == ctx.tenant.id,
                    DocumentChunk.workspace_id == ctx.workspace.id,
                    DocumentChunk.text_search_vector.op("@@")(
                        func.plainto_tsquery("english", query)
                    ),
                )
            )
        )

        # Filter by indexed status (default: only indexed versions)
        if filters is None or not filters.include_unindexed:
            stmt = stmt.where(DocumentVersion.is_indexed == True)  # noqa: E712

        # Apply policy constraints
        if policy.config.allowed_jurisdictions:
            stmt = stmt.where(
                Document.jurisdiction.in_(policy.config.allowed_jurisdictions)
            )
        if policy.config.allowed_input_languages:
            stmt = stmt.where(
                Document.language.in_(policy.config.allowed_input_languages)
            )

        # Apply filters
        if filters:
            if filters.document_type:
                stmt = stmt.where(Document.document_type == filters.document_type)
            if filters.jurisdiction:
                stmt = stmt.where(Document.jurisdiction == filters.jurisdiction)
            if filters.language:
                stmt = stmt.where(Document.language == filters.language)

        stmt = stmt.order_by(text("rank DESC")).limit(self.MAX_CANDIDATES)

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build results
        results: list[SearchResult] = []
        for row in rows:
            chunk = row[0]
            rank = float(row[1]) if row[1] else 0.0
            doc_title = row[2]
            doc_type = row[3]
            jurisdiction = row[4]
            language = row[5]

            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    snippet=self._truncate_snippet(chunk.text),
                    document_id=chunk.document_id,
                    version_id=chunk.version_id,
                    document_title=doc_title,
                    document_type=doc_type,
                    jurisdiction=jurisdiction,
                    language=language,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    vector_score=0.0,
                    keyword_score=rank,
                    final_score=rank,  # Will be recalculated
                )
            )

        return results

    async def _keyword_search_ilike(
        self,
        ctx: RequestContext,
        query: str,
        policy: ResolvedPolicy,
        filters: SearchFilters | None,
    ) -> list[SearchResult]:
        """Fallback keyword search using ILIKE for Arabic text.

        Args:
            ctx: Request context
            query: Search query (may contain Arabic)
            policy: Resolved policy
            filters: Optional filters

        Returns:
            List of SearchResult with keyword scores
        """
        # Simple tokenization
        tokens = [t.strip() for t in query.split() if t.strip()]
        if not tokens:
            return []

        # Build ILIKE conditions for each token
        like_conditions = [
            DocumentChunk.text.ilike(f"%{token}%") for token in tokens
        ]

        stmt = (
            select(
                DocumentChunk,
                Document.title.label("document_title"),
                Document.document_type,
                Document.jurisdiction,
                Document.language,
            )
            .join(Document, DocumentChunk.document_id == Document.id)
            .join(DocumentVersion, DocumentChunk.version_id == DocumentVersion.id)
            .where(
                and_(
                    DocumentChunk.tenant_id == ctx.tenant.id,
                    DocumentChunk.workspace_id == ctx.workspace.id,
                    or_(*like_conditions),
                )
            )
        )

        # Filter by indexed status (default: only indexed versions)
        if filters is None or not filters.include_unindexed:
            stmt = stmt.where(DocumentVersion.is_indexed == True)  # noqa: E712

        # Apply policy constraints
        if policy.config.allowed_jurisdictions:
            stmt = stmt.where(
                Document.jurisdiction.in_(policy.config.allowed_jurisdictions)
            )
        if policy.config.allowed_input_languages:
            stmt = stmt.where(
                Document.language.in_(policy.config.allowed_input_languages)
            )

        # Apply filters
        if filters:
            if filters.document_type:
                stmt = stmt.where(Document.document_type == filters.document_type)
            if filters.jurisdiction:
                stmt = stmt.where(Document.jurisdiction == filters.jurisdiction)
            if filters.language:
                stmt = stmt.where(Document.language == filters.language)

        stmt = stmt.limit(self.MAX_CANDIDATES)

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build results - score based on token match count
        results: list[SearchResult] = []
        for row in rows:
            chunk = row[0]
            doc_title = row[1]
            doc_type = row[2]
            jurisdiction = row[3]
            language = row[4]

            # Count matching tokens for score
            text_lower = chunk.text.lower()
            match_count = sum(1 for t in tokens if t.lower() in text_lower)
            score = match_count / len(tokens) if tokens else 0.0

            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    chunk_index=chunk.chunk_index,
                    snippet=self._truncate_snippet(chunk.text),
                    document_id=chunk.document_id,
                    version_id=chunk.version_id,
                    document_title=doc_title,
                    document_type=doc_type,
                    jurisdiction=jurisdiction,
                    language=language,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    vector_score=0.0,
                    keyword_score=score,
                    final_score=score,  # Will be recalculated
                )
            )

        return results

    def _combine_results(
        self,
        vector_results: list[SearchResult],
        keyword_results: list[SearchResult],
    ) -> list[SearchResult]:
        """Combine vector and keyword results using weighted score fusion.

        Args:
            vector_results: Results from vector search
            keyword_results: Results from keyword search

        Returns:
            Combined results with final scores
        """
        # Build lookup by chunk_id
        combined: dict[str, SearchResult] = {}

        # Normalize vector scores (min-max)
        if vector_results:
            max_vec = max(r.vector_score for r in vector_results)
            min_vec = min(r.vector_score for r in vector_results)
            vec_range = max_vec - min_vec if max_vec != min_vec else 1.0

            for r in vector_results:
                norm_score = (r.vector_score - min_vec) / vec_range
                r.vector_score = norm_score
                combined[r.chunk_id] = r

        # Normalize keyword scores (min-max) and merge
        if keyword_results:
            max_kw = max(r.keyword_score for r in keyword_results)
            min_kw = min(r.keyword_score for r in keyword_results)
            kw_range = max_kw - min_kw if max_kw != min_kw else 1.0

            for r in keyword_results:
                norm_score = (r.keyword_score - min_kw) / kw_range

                if r.chunk_id in combined:
                    # Merge scores
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
