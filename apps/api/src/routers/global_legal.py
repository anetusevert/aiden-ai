"""Global Legal Corpus routes for operator management.

Endpoints for managing the global law corpus (legal instruments, versions, search).
All management endpoints require platform admin privileges.
Search endpoint is available to authenticated users BUT respects workspace policy.

Policy-Aware Design:
- Global legal search respects workspace policy constraints
- allowed_jurisdictions filter restricts which jurisdictions can be returned
- allowed_input_languages filter restricts which languages can be returned
- Design principle: Global ≠ unrestricted. Policy is still the gate.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import RequestContext, get_workspace_context
from src.dependencies.platform_admin import PlatformAdminContext, require_platform_admin
from src.embeddings import get_embedding_provider
from src.schemas.global_legal import (
    GlobalLegalChunkResult,
    GlobalLegalSearchRequest,
    GlobalLegalSearchResponse,
    InstrumentStatus,
    InstrumentType,
    Jurisdiction,
    Language,
    LegalChunkDetail,
    LegalChunkPreview,
    LegalChunkWithContext,
    LegalInstrumentCreate,
    LegalInstrumentCreateResponse,
    LegalInstrumentListResponse,
    LegalInstrumentResponse,
    LegalInstrumentWithLatestVersion,
    LegalInstrumentWithVersions,
    LegalVersionCreate,
    LegalVersionCreateResponse,
    LegalVersionSummary,
    ReindexLegalVersionResponse,
    ViewerChunksResponse,
    ViewerInstrumentDetail,
    ViewerInstrumentListItem,
    ViewerInstrumentListResponse,
    ViewerVersionDetail,
    ViewerVersionSummary,
)
from src.services import log_audit_event
from src.services.global_legal_retrieval_service import (
    GlobalLegalRetrievalService,
    GlobalLegalSearchFilters,
    PolicyFilters,
)
from src.services.global_legal_service import (
    GlobalLegalService,
    LegalInstrumentNotFoundError,
    LegalUploadError,
    LegalVersionNotFoundError,
)
from src.services.policy_service import PolicyService
from src.storage.s3 import get_storage_client

# Management router - requires platform admin
router = APIRouter(prefix="/global/legal-instruments", tags=["global-legal"])

# Search router - available to authenticated users
search_router = APIRouter(prefix="/global/search", tags=["global-legal-search"])

# Viewer router - read-only access for authenticated users (respects workspace policy)
viewer_router = APIRouter(prefix="/global/legal", tags=["global-legal-viewer"])


# =============================================================================
# Helper Functions
# =============================================================================


def _instrument_to_response(instrument) -> LegalInstrumentResponse:
    """Convert LegalInstrument to response schema."""
    return LegalInstrumentResponse(
        id=instrument.id,
        jurisdiction=instrument.jurisdiction,
        instrument_type=instrument.instrument_type,
        title=instrument.title,
        title_ar=instrument.title_ar,
        official_source_url=instrument.official_source_url,
        published_at=instrument.published_at,
        effective_at=instrument.effective_at,
        status=instrument.status,
        created_at=instrument.created_at,
        updated_at=instrument.updated_at,
        created_by_user_id=instrument.created_by_user_id,
    )


def _version_to_summary(version) -> LegalVersionSummary:
    """Convert LegalInstrumentVersion to summary schema."""
    return LegalVersionSummary(
        id=version.id,
        version_label=version.version_label,
        file_name=version.file_name,
        content_type=version.content_type,
        size_bytes=version.size_bytes,
        language=version.language,
        is_indexed=version.is_indexed,
        indexed_at=version.indexed_at,
        embedding_model=version.embedding_model,
        created_at=version.created_at,
        uploaded_by_user_id=version.uploaded_by_user_id,
    )


def _instrument_with_latest_version(instrument) -> LegalInstrumentWithLatestVersion:
    """Convert LegalInstrument to response with latest version."""
    base = _instrument_to_response(instrument)
    latest_version = None
    if instrument.versions:
        # versions are already sorted by created_at desc
        latest_version = _version_to_summary(instrument.versions[0])
    return LegalInstrumentWithLatestVersion(
        **base.model_dump(),
        latest_version=latest_version,
    )


def _instrument_with_versions(instrument) -> LegalInstrumentWithVersions:
    """Convert LegalInstrument to response with all versions."""
    base = _instrument_to_response(instrument)
    versions = [_version_to_summary(v) for v in instrument.versions]
    return LegalInstrumentWithVersions(
        **base.model_dump(),
        versions=versions,
    )


# =============================================================================
# Management Endpoints (Platform Admin Only)
# =============================================================================


@router.post(
    "",
    response_model=LegalInstrumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create legal instrument",
    description="Create a new legal instrument with optional initial version. Platform admin only.",
)
async def create_legal_instrument(
    request: Request,
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    # Instrument metadata via form fields (since we may have file upload)
    jurisdiction: Annotated[Jurisdiction, Form(description="GCC jurisdiction")],
    instrument_type: Annotated[InstrumentType, Form(description="Type of legal instrument")],
    title: Annotated[str, Form(min_length=1, max_length=1000, description="Official title in English")],
    title_ar: Annotated[str | None, Form(max_length=1000, description="Official title in Arabic")] = None,
    official_source_url: Annotated[str | None, Form(max_length=2000, description="URL to official source")] = None,
    published_at: Annotated[str | None, Form(description="Date of publication (YYYY-MM-DD)")] = None,
    effective_at: Annotated[str | None, Form(description="Effective date (YYYY-MM-DD)")] = None,
    instrument_status: Annotated[InstrumentStatus, Form(alias="status", description="Status")] = InstrumentStatus.ACTIVE,
    # Optional initial version
    version_label: Annotated[str | None, Form(description="Version label (required if file provided)")] = None,
    language: Annotated[Language | None, Form(description="Language (required if file provided)")] = None,
    file: Annotated[UploadFile | None, File(description="Document file (PDF, DOCX)")] = None,
) -> LegalInstrumentCreateResponse:
    """Create a new legal instrument with optional initial version upload."""
    from datetime import date

    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)

    # Parse dates
    parsed_published_at = None
    parsed_effective_at = None
    if published_at:
        try:
            parsed_published_at = date.fromisoformat(published_at)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid published_at date format. Use YYYY-MM-DD.",
            )
    if effective_at:
        try:
            parsed_effective_at = date.fromisoformat(effective_at)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid effective_at date format. Use YYYY-MM-DD.",
            )

    try:
        # Create instrument
        instrument = await service.create_instrument(
            ctx=ctx,
            jurisdiction=jurisdiction.value,
            instrument_type=instrument_type.value,
            title=title,
            title_ar=title_ar,
            official_source_url=official_source_url,
            published_at=parsed_published_at,
            effective_at=parsed_effective_at,
            status=instrument_status.value,
        )

        version_response = None

        # Create initial version if file provided
        if file:
            if not version_label:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="version_label is required when uploading a file",
                )
            if not language:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="language is required when uploading a file",
                )

            file_data = await file.read()
            version = await service.create_version(
                ctx=ctx,
                instrument_id=instrument.id,
                version_label=version_label,
                language=language.value,
                file_name=file.filename or "unknown",
                content_type=file.content_type or "application/octet-stream",
                file_data=file_data,
            )
            version_response = _version_to_summary(version)

        await db.commit()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=None,  # No workspace context
            action="global_legal.create",
            status="success",
            resource_type="legal_instrument",
            resource_id=instrument.id,
            meta={
                "title": title,
                "jurisdiction": jurisdiction.value,
                "instrument_type": instrument_type.value,
                "has_initial_version": version_response is not None,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )

        return LegalInstrumentCreateResponse(
            instrument=_instrument_to_response(instrument),
            version=version_response,
        )

    except LegalUploadError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/{instrument_id}/versions",
    response_model=LegalVersionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload new version",
    description="Upload a new version for an existing legal instrument. Platform admin only.",
)
async def upload_legal_version(
    request: Request,
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    version_label: Annotated[str, Form(min_length=1, max_length=64, description="Version label")],
    language: Annotated[Language, Form(description="Language of the document")],
    file: Annotated[UploadFile, File(description="Document file (PDF, DOCX)")],
) -> LegalVersionCreateResponse:
    """Upload a new version for a legal instrument."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)

    try:
        file_data = await file.read()
        version = await service.create_version(
            ctx=ctx,
            instrument_id=instrument_id,
            version_label=version_label,
            language=language.value,
            file_name=file.filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            file_data=file_data,
        )

        await db.commit()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.version.upload",
            status="success",
            resource_type="legal_instrument_version",
            resource_id=version.id,
            meta={
                "instrument_id": instrument_id,
                "version_label": version_label,
                "language": language.value,
                "file_name": file.filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )

        return LegalVersionCreateResponse(
            version=_version_to_summary(version),
            instrument_id=instrument_id,
        )

    except LegalInstrumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal instrument '{instrument_id}' not found",
        )
    except LegalUploadError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "",
    response_model=LegalInstrumentListResponse,
    summary="List legal instruments",
    description="List all legal instruments with optional filters. Platform admin only.",
)
async def list_legal_instruments(
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    jurisdiction: Annotated[Jurisdiction | None, Query(description="Filter by jurisdiction")] = None,
    instrument_type: Annotated[InstrumentType | None, Query(description="Filter by type")] = None,
    instrument_status: Annotated[InstrumentStatus | None, Query(alias="status", description="Filter by status")] = None,
) -> LegalInstrumentListResponse:
    """List legal instruments with pagination and filters."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)

    instruments, total = await service.list_instruments(
        limit=limit,
        offset=offset,
        jurisdiction=jurisdiction.value if jurisdiction else None,
        instrument_type=instrument_type.value if instrument_type else None,
        status=instrument_status.value if instrument_status else None,
    )

    items = [_instrument_with_latest_version(i) for i in instruments]

    return LegalInstrumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{instrument_id}",
    response_model=LegalInstrumentWithVersions,
    summary="Get legal instrument",
    description="Get a legal instrument with all versions. Platform admin only.",
)
async def get_legal_instrument(
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LegalInstrumentWithVersions:
    """Get a legal instrument by ID with all versions."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)

    instrument = await service.get_instrument(instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal instrument '{instrument_id}' not found",
        )

    return _instrument_with_versions(instrument)


@router.post(
    "/{instrument_id}/versions/{version_id}/reindex",
    response_model=ReindexLegalVersionResponse,
    summary="Reindex version",
    description="Re-run extraction/chunking/embedding for a version. Platform admin only.",
)
async def reindex_legal_version(
    request: Request,
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    replace: Annotated[bool, Query(description="Replace existing chunks/embeddings")] = True,
) -> ReindexLegalVersionResponse:
    """Re-run extraction/chunking/embedding for a legal instrument version."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)

    try:
        chunks_indexed, chunks_skipped = await service.reindex_version(
            version_id=version_id,
            replace_existing=replace,
        )

        await db.commit()

        provider = get_embedding_provider()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.reindex",
            status="success",
            resource_type="legal_instrument_version",
            resource_id=version_id,
            meta={
                "instrument_id": instrument_id,
                "chunks_indexed": chunks_indexed,
                "chunks_skipped": chunks_skipped,
                "replace": replace,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )

        return ReindexLegalVersionResponse(
            instrument_id=instrument_id,
            version_id=version_id,
            chunks_indexed=chunks_indexed,
            chunks_skipped=chunks_skipped,
            embedding_model=provider.model_name,
        )

    except LegalVersionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}",
        )


# =============================================================================
# Search Endpoint (Authenticated Users)
# =============================================================================


@search_router.post(
    "/chunks",
    response_model=GlobalLegalSearchResponse,
    summary="Search global legal corpus",
    description=(
        "Hybrid semantic + keyword search over the global legal corpus. "
        "Available to all authenticated users but respects workspace policy constraints. "
        "Results are filtered by allowed_jurisdictions and allowed_input_languages from workspace policy."
    ),
)
async def search_global_legal_chunks(
    request: Request,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: GlobalLegalSearchRequest,
) -> GlobalLegalSearchResponse:
    """Search global legal corpus using hybrid vector + keyword search.

    Results are ranked by a combination of semantic similarity and keyword matching.
    This endpoint is available to all authenticated users (not just platform admins).

    Policy-Aware Behavior:
    - Results are filtered by workspace policy (allowed_jurisdictions, allowed_input_languages)
    - A KSA-only workspace cannot retrieve UAE laws
    - Design principle: Global ≠ unrestricted. Policy is still the gate.
    """
    service = GlobalLegalRetrievalService(db)
    policy_service = PolicyService(db)

    try:
        # Resolve workspace policy for filtering
        resolved_policy = await policy_service.resolve(ctx)
        policy_config = resolved_policy.config

        # Build user-specified filters
        filters = GlobalLegalSearchFilters(
            jurisdiction=body.jurisdiction.value if body.jurisdiction else None,
            instrument_type=body.instrument_type.value if body.instrument_type else None,
            language=body.language.value if body.language else None,
        )

        # Build policy-based filters from workspace configuration
        # Global ≠ unrestricted. Policy is still the gate.
        policy_filters = PolicyFilters(
            allowed_jurisdictions=policy_config.allowed_jurisdictions,
            allowed_input_languages=policy_config.allowed_input_languages,
        )

        # Search returns GlobalLegalSearchServiceResponse with typed fields
        search_response = await service.search_chunks(
            query=body.query,
            limit=body.limit,
            filters=filters,
            policy_filters=policy_filters,
        )

        response_results = [
            GlobalLegalChunkResult(
                chunk_id=r.chunk_id,
                chunk_index=r.chunk_index,
                snippet=r.snippet,
                instrument_id=r.instrument_id,
                version_id=r.version_id,
                instrument_title=r.instrument_title,
                instrument_title_ar=r.instrument_title_ar,
                instrument_type=r.instrument_type,
                jurisdiction=r.jurisdiction,
                language=r.language,
                published_at=r.published_at,
                effective_at=r.effective_at,
                official_source_url=r.official_source_url,
                char_start=r.char_start,
                char_end=r.char_end,
                page_start=r.page_start,
                page_end=r.page_end,
                vector_score=r.vector_score,
                keyword_score=r.keyword_score,
                final_score=r.final_score,
                source_type=r.source_type,
                source_label=r.source_label,
            )
            for r in search_response.items
        ]

        # Audit log with comprehensive policy enforcement metadata
        policy_meta = search_response.policy_meta
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="global_legal.search",
            status="success",
            resource_type="search",
            meta={
                "query": body.query[:100],
                "result_count": len(search_response.items),
                "limit": body.limit,
                "filters": {
                    "jurisdiction": body.jurisdiction.value if body.jurisdiction else None,
                    "instrument_type": body.instrument_type.value if body.instrument_type else None,
                    "language": body.language.value if body.language else None,
                },
                # Policy enforcement details for audit (typed PolicyMeta)
                "policy_applied": policy_meta.policy_applied,
                "policy_jurisdictions_count": policy_meta.policy_jurisdictions_count,
                "policy_languages_count": policy_meta.policy_languages_count,
                "policy_denied_reason": policy_meta.policy_denied_reason,
                "policy_source": resolved_policy.source,
                "policy_allowed_jurisdictions": policy_config.allowed_jurisdictions,
                "policy_allowed_input_languages": policy_config.allowed_input_languages,
            },
            request=request,
        )

        return GlobalLegalSearchResponse(
            query=body.query,
            total=len(response_results),
            results=response_results,
        )

    except Exception as e:
        # Audit log failure
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="global_legal.search.fail",
            status="fail",
            resource_type="search",
            meta={
                "query": body.query[:100] if body.query else "",
                "error": str(e)[:200],
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


# =============================================================================
# Viewer Endpoints (Read-Only, Authenticated Users, Policy-Aware)
# =============================================================================


@viewer_router.get(
    "/instruments",
    response_model=ViewerInstrumentListResponse,
    summary="List global legal instruments (read-only)",
    description=(
        "Browse the global legal corpus. Read-only access for all authenticated users. "
        "Results are filtered by workspace policy (allowed_jurisdictions). "
        "Clear distinction from workspace documents: these are global law references."
    ),
)
async def list_global_legal_instruments(
    request: Request,
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum results")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
    jurisdiction: Annotated[Jurisdiction | None, Query(description="Filter by jurisdiction")] = None,
    instrument_type: Annotated[InstrumentType | None, Query(description="Filter by type")] = None,
) -> ViewerInstrumentListResponse:
    """List global legal instruments with policy enforcement."""
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from src.models.legal_instrument import LegalInstrument

    policy_service = PolicyService(db)
    resolved_policy = await policy_service.resolve(ctx)
    policy_config = resolved_policy.config
    allowed_jurisdictions = policy_config.allowed_jurisdictions

    # Deny if no jurisdictions are allowed
    if not allowed_jurisdictions:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="global.legal.view",
            status="fail",
            resource_type="legal_instrument",
            meta={
                "reason": "policy_denied",
                "policy_source": resolved_policy.source,
            },
            request=request,
        )
        return ViewerInstrumentListResponse(items=[], total=0, limit=limit, offset=offset)

    # Build query with policy filter
    base_query = select(LegalInstrument).where(
        LegalInstrument.jurisdiction.in_(allowed_jurisdictions),
        LegalInstrument.status == "active",  # Only show active instruments
    )

    # User filters
    if jurisdiction:
        # Ensure user-requested jurisdiction is in policy
        if jurisdiction.value not in allowed_jurisdictions:
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="global.legal.view",
                status="fail",
                resource_type="legal_instrument",
                meta={
                    "reason": "jurisdiction_denied",
                    "requested_jurisdiction": jurisdiction.value,
                    "allowed_jurisdictions": allowed_jurisdictions,
                },
                request=request,
            )
            return ViewerInstrumentListResponse(items=[], total=0, limit=limit, offset=offset)
        base_query = base_query.where(LegalInstrument.jurisdiction == jurisdiction.value)

    if instrument_type:
        base_query = base_query.where(LegalInstrument.instrument_type == instrument_type.value)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar() or 0

    # Get paginated instruments with versions
    result = await db.execute(
        base_query.order_by(LegalInstrument.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(LegalInstrument.versions))
    )
    instruments = result.scalars().all()

    # Convert to response
    items = []
    for inst in instruments:
        latest_version_date = None
        if inst.versions:
            # versions are ordered by created_at desc via relationship
            sorted_versions = sorted(inst.versions, key=lambda v: v.created_at, reverse=True)
            latest_version_date = sorted_versions[0].created_at

        items.append(ViewerInstrumentListItem(
            id=inst.id,
            title=inst.title,
            title_ar=inst.title_ar,
            jurisdiction=inst.jurisdiction,
            instrument_type=inst.instrument_type,
            status=inst.status,
            published_at=inst.published_at,
            effective_at=inst.effective_at,
            official_source_url=inst.official_source_url,
            latest_version_date=latest_version_date,
        ))

    # Audit log success
    await log_audit_event(
        db=db,
        ctx=ctx,
        action="global.legal.view",
        status="success",
        resource_type="legal_instrument",
        meta={
            "result_count": len(items),
            "total": total,
            "policy_source": resolved_policy.source,
            "policy_jurisdictions_count": len(allowed_jurisdictions),
        },
        request=request,
    )

    return ViewerInstrumentListResponse(items=items, total=total, limit=limit, offset=offset)


@viewer_router.get(
    "/instruments/{instrument_id}",
    response_model=ViewerInstrumentDetail,
    summary="Get global legal instrument detail (read-only)",
    description=(
        "View a global legal instrument with all versions. Read-only access. "
        "Policy enforcement: access denied if instrument jurisdiction not in workspace policy."
    ),
)
async def get_global_legal_instrument(
    request: Request,
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ViewerInstrumentDetail:
    """Get a global legal instrument by ID with policy enforcement."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)
    policy_service = PolicyService(db)

    # Get instrument
    instrument = await service.get_instrument(instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal instrument '{instrument_id}' not found",
        )

    # Policy check
    resolved_policy = await policy_service.resolve(ctx)
    policy_config = resolved_policy.config
    allowed_jurisdictions = policy_config.allowed_jurisdictions

    if instrument.jurisdiction not in allowed_jurisdictions:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="global.legal.view",
            status="fail",
            resource_type="legal_instrument",
            resource_id=instrument_id,
            meta={
                "reason": "jurisdiction_denied",
                "instrument_jurisdiction": instrument.jurisdiction,
                "allowed_jurisdictions": allowed_jurisdictions,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: instrument jurisdiction '{instrument.jurisdiction}' not in workspace policy",
        )

    # Convert versions
    versions = [
        ViewerVersionSummary(
            id=v.id,
            version_label=v.version_label,
            language=v.language,
            is_indexed=v.is_indexed,
            created_at=v.created_at,
        )
        for v in sorted(instrument.versions, key=lambda x: x.created_at, reverse=True)
    ]

    # Audit log
    await log_audit_event(
        db=db,
        ctx=ctx,
        action="global.legal.view",
        status="success",
        resource_type="legal_instrument",
        resource_id=instrument_id,
        meta={
            "title": instrument.title,
            "jurisdiction": instrument.jurisdiction,
            "version_count": len(versions),
        },
        request=request,
    )

    return ViewerInstrumentDetail(
        id=instrument.id,
        title=instrument.title,
        title_ar=instrument.title_ar,
        jurisdiction=instrument.jurisdiction,
        instrument_type=instrument.instrument_type,
        status=instrument.status,
        published_at=instrument.published_at,
        effective_at=instrument.effective_at,
        official_source_url=instrument.official_source_url,
        created_at=instrument.created_at,
        versions=versions,
    )


@viewer_router.get(
    "/instruments/{instrument_id}/versions/{version_id}",
    response_model=ViewerVersionDetail,
    summary="Get global legal version detail (read-only)",
    description=(
        "View version metadata and chunk list for reading. "
        "Policy enforcement: access denied if instrument jurisdiction not in workspace policy."
    ),
)
async def get_global_legal_version(
    request: Request,
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ViewerVersionDetail:
    """Get a global legal version by ID with policy enforcement."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)
    policy_service = PolicyService(db)

    # Get instrument
    instrument = await service.get_instrument(instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal instrument '{instrument_id}' not found",
        )

    # Policy check
    resolved_policy = await policy_service.resolve(ctx)
    policy_config = resolved_policy.config
    allowed_jurisdictions = policy_config.allowed_jurisdictions

    if instrument.jurisdiction not in allowed_jurisdictions:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="global.legal.view",
            status="fail",
            resource_type="legal_instrument_version",
            resource_id=version_id,
            meta={
                "reason": "jurisdiction_denied",
                "instrument_id": instrument_id,
                "instrument_jurisdiction": instrument.jurisdiction,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: instrument jurisdiction '{instrument.jurisdiction}' not in workspace policy",
        )

    # Get version
    version = await service.get_version(version_id)
    if not version or version.legal_instrument_id != instrument_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found for instrument '{instrument_id}'",
        )

    # Audit log
    await log_audit_event(
        db=db,
        ctx=ctx,
        action="global.legal.view",
        status="success",
        resource_type="legal_instrument_version",
        resource_id=version_id,
        meta={
            "instrument_id": instrument_id,
            "version_label": version.version_label,
            "is_indexed": version.is_indexed,
        },
        request=request,
    )

    return ViewerVersionDetail(
        id=version.id,
        version_label=version.version_label,
        language=version.language,
        is_indexed=version.is_indexed,
        indexed_at=version.indexed_at,
        file_name=version.file_name,
        content_type=version.content_type,
        size_bytes=version.size_bytes,
        created_at=version.created_at,
        instrument_id=instrument.id,
        instrument_title=instrument.title,
        instrument_title_ar=instrument.title_ar,
        jurisdiction=instrument.jurisdiction,
        instrument_type=instrument.instrument_type,
        official_source_url=instrument.official_source_url,
        published_at=instrument.published_at,
        effective_at=instrument.effective_at,
    )


@viewer_router.get(
    "/instruments/{instrument_id}/versions/{version_id}/chunks",
    response_model=ViewerChunksResponse,
    summary="List chunks for a global legal version (read-only)",
    description="Get all chunk previews for viewer sidebar. Policy enforcement applies.",
)
async def list_global_legal_chunks(
    request: Request,
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ViewerChunksResponse:
    """List all chunks for a global legal version."""
    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)
    policy_service = PolicyService(db)

    # Get instrument for policy check
    instrument = await service.get_instrument(instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal instrument '{instrument_id}' not found",
        )

    # Policy check
    resolved_policy = await policy_service.resolve(ctx)
    policy_config = resolved_policy.config
    allowed_jurisdictions = policy_config.allowed_jurisdictions

    if instrument.jurisdiction not in allowed_jurisdictions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: instrument jurisdiction '{instrument.jurisdiction}' not in workspace policy",
        )

    # Get chunks
    chunks = await service.get_version_chunks(version_id)

    chunk_previews = [
        LegalChunkPreview(
            id=c.id,
            chunk_index=c.chunk_index,
            preview=c.text[:150] + ("..." if len(c.text) > 150 else ""),
            page_start=c.page_start,
        )
        for c in chunks
    ]

    # Audit log
    await log_audit_event(
        db=db,
        ctx=ctx,
        action="global.legal.view",
        status="success",
        resource_type="legal_chunks",
        meta={
            "instrument_id": instrument_id,
            "version_id": version_id,
            "chunk_count": len(chunk_previews),
        },
        request=request,
    )

    return ViewerChunksResponse(
        version_id=version_id,
        instrument_id=instrument_id,
        chunk_count=len(chunk_previews),
        chunks=chunk_previews,
    )


@viewer_router.get(
    "/instruments/{instrument_id}/versions/{version_id}/chunks/{chunk_id}",
    response_model=LegalChunkWithContext,
    summary="Get a single chunk with context (read-only)",
    description="Get full chunk text with prev/next neighbor previews for navigation.",
)
async def get_global_legal_chunk(
    request: Request,
    instrument_id: Annotated[str, Path(description="Legal instrument ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    chunk_id: Annotated[str, Path(description="Chunk ID")],
    ctx: Annotated[RequestContext, Depends(get_workspace_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LegalChunkWithContext:
    """Get a single chunk with neighbor context."""
    from sqlalchemy import select

    from src.models.legal_chunk import LegalChunk

    storage_client = get_storage_client()
    service = GlobalLegalService(db, storage_client)
    policy_service = PolicyService(db)

    # Get instrument for policy check
    instrument = await service.get_instrument(instrument_id)
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal instrument '{instrument_id}' not found",
        )

    # Policy check
    resolved_policy = await policy_service.resolve(ctx)
    policy_config = resolved_policy.config
    allowed_jurisdictions = policy_config.allowed_jurisdictions

    if instrument.jurisdiction not in allowed_jurisdictions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: instrument jurisdiction '{instrument.jurisdiction}' not in workspace policy",
        )

    # Get the specific chunk
    result = await db.execute(
        select(LegalChunk).where(
            LegalChunk.id == chunk_id,
            LegalChunk.version_id == version_id,
        )
    )
    chunk = result.scalar_one_or_none()

    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk '{chunk_id}' not found",
        )

    # Get all chunks for neighbor context
    all_chunks = await service.get_version_chunks(version_id)
    chunk_list = list(all_chunks)

    # Find neighbors
    prev_chunk = None
    next_chunk = None
    for i, c in enumerate(chunk_list):
        if c.id == chunk_id:
            if i > 0:
                prev_c = chunk_list[i - 1]
                prev_chunk = LegalChunkPreview(
                    id=prev_c.id,
                    chunk_index=prev_c.chunk_index,
                    preview=prev_c.text[:150] + ("..." if len(prev_c.text) > 150 else ""),
                    page_start=prev_c.page_start,
                )
            if i < len(chunk_list) - 1:
                next_c = chunk_list[i + 1]
                next_chunk = LegalChunkPreview(
                    id=next_c.id,
                    chunk_index=next_c.chunk_index,
                    preview=next_c.text[:150] + ("..." if len(next_c.text) > 150 else ""),
                    page_start=next_c.page_start,
                )
            break

    # Audit log
    await log_audit_event(
        db=db,
        ctx=ctx,
        action="global.legal.view",
        status="success",
        resource_type="legal_chunk",
        resource_id=chunk_id,
        meta={
            "instrument_id": instrument_id,
            "version_id": version_id,
            "chunk_index": chunk.chunk_index,
        },
        request=request,
    )

    return LegalChunkWithContext(
        chunk=LegalChunkDetail(
            id=chunk.id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
        ),
        prev_chunk=prev_chunk,
        next_chunk=next_chunk,
    )
