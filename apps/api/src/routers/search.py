"""Search routes for document chunk retrieval.

Endpoints for hybrid semantic + keyword search over document chunks.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, require_admin, require_viewer
from src.schemas.search import ReindexResponse, SearchChunkResult, SearchChunksResponse
from src.services import log_audit_event
from src.services.embedding_service import EmbeddingService
from src.services.retrieval_service import RetrievalService, SearchFilters

router = APIRouter(prefix="/search", tags=["search"])


# =============================================================================
# Search Chunks
# =============================================================================


@router.get(
    "/chunks",
    response_model=SearchChunksResponse,
    summary="Search document chunks",
    description="Hybrid semantic + keyword search over document chunks. Returns results with citation metadata. Requires VIEWER role or higher.",
)
async def search_chunks(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str, Query(description="Search query", min_length=1, max_length=1000)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Maximum number of results (default 10, max 50)",
        ),
    ] = 10,
    document_type: Annotated[
        str | None,
        Query(description="Filter by document type (contract, policy, memo, regulatory, other)"),
    ] = None,
    jurisdiction: Annotated[
        str | None,
        Query(description="Filter by jurisdiction (UAE, DIFC, ADGM, KSA)"),
    ] = None,
    language: Annotated[
        str | None,
        Query(description="Filter by language (en, ar, mixed)"),
    ] = None,
    include_unindexed: Annotated[
        bool,
        Query(
            description="Include unindexed document versions in results (default: false, only indexed versions)",
        ),
    ] = False,
) -> SearchChunksResponse:
    """Search document chunks using hybrid vector + keyword search.

    Results are ranked by a combination of semantic similarity and keyword matching.
    Policy constraints (allowed jurisdictions, languages) are automatically enforced.

    By default, only searches indexed versions (is_indexed=True). Set include_unindexed=true
    to include versions that haven't been indexed yet.
    """
    service = RetrievalService(db)

    try:
        # Build filters
        filters = SearchFilters(
            document_type=document_type,
            jurisdiction=jurisdiction,
            language=language,
            include_unindexed=include_unindexed,
        )

        # Perform search
        results = await service.search_chunks(ctx, q, limit=limit, filters=filters)

        # Convert to response with source provenance fields
        # source_type is always "workspace_document" for workspace search
        # source_label is the document title (human-readable identifier)
        response_results = [
            SearchChunkResult(
                chunk_id=r.chunk_id,
                chunk_index=r.chunk_index,
                snippet=r.snippet,
                document_id=r.document_id,
                version_id=r.version_id,
                document_title=r.document_title,
                document_type=r.document_type,
                jurisdiction=r.jurisdiction,
                language=r.language,
                char_start=r.char_start,
                char_end=r.char_end,
                page_start=r.page_start,
                page_end=r.page_end,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score,
                final_score=r.final_score,
                # Source provenance fields (always included for every result)
                source_type="workspace_document",
                source_label=r.document_title,
            )
            for r in results
        ]

        # Audit log
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="search.chunks.success",
            status="success",
            resource_type="search",
            meta={
                "query": q[:100],  # Truncate query for audit
                "result_count": len(results),
                "limit": limit,
                "filters": {
                    "document_type": document_type,
                    "jurisdiction": jurisdiction,
                    "language": language,
                    "include_unindexed": include_unindexed,
                },
            },
            request=request,
        )

        return SearchChunksResponse(
            query=q,
            total=len(response_results),
            results=response_results,
        )

    except Exception as e:
        # Audit log failure
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="search.chunks.fail",
            status="fail",
            resource_type="search",
            meta={
                "query": q[:100] if q else "",
                "error": str(e)[:200],
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


# =============================================================================
# Admin: Reindex Document Version
# =============================================================================


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post(
    "/reindex/{document_id}/{version_id}",
    response_model=ReindexResponse,
    summary="Reindex document version",
    description="Regenerate embeddings for a document version. Admin-only. Idempotent.",
)
async def reindex_version(
    request: Request,
    document_id: Annotated[str, Path(description="Document ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    replace: Annotated[
        bool,
        Query(
            description="Replace existing embeddings (default: skip existing)",
        ),
    ] = False,
) -> ReindexResponse:
    """Regenerate embeddings for all chunks in a document version.

    This is idempotent - by default, chunks that already have embeddings are skipped.
    Set replace=true to force regeneration of all embeddings.
    """
    from src.embeddings import get_embedding_provider

    service = EmbeddingService(db)

    try:
        created, skipped = await service.generate_embeddings_for_version(
            ctx,
            document_id,
            version_id,
            replace_existing=replace,
        )

        await db.commit()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="embeddings.reindex.success",
            status="success",
            resource_type="document_version",
            resource_id=version_id,
            meta={
                "document_id": document_id,
                "version_id": version_id,
                "chunks_indexed": created,
                "chunks_skipped": skipped,
                "replace_existing": replace,
            },
            request=request,
        )

        provider = get_embedding_provider()
        return ReindexResponse(
            document_id=document_id,
            version_id=version_id,
            chunks_indexed=created,
            chunks_skipped=skipped,
            embedding_model=provider.model_name,
        )

    except Exception as e:
        await db.rollback()

        # Mark version as not indexed on failure
        try:
            from sqlalchemy import select
            from src.models.document_version import DocumentVersion

            result = await db.execute(
                select(DocumentVersion).where(DocumentVersion.id == version_id)
            )
            version = result.scalar_one_or_none()
            if version:
                version.is_indexed = False
                await db.commit()
        except Exception:
            pass  # Don't fail on status update failure

        # Audit log failure
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="embeddings.reindex.fail",
            status="fail",
            resource_type="document_version",
            resource_id=version_id,
            meta={
                "document_id": document_id,
                "version_id": version_id,
                "error": str(e)[:200],
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}",
        )
