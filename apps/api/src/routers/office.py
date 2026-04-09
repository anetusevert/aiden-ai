"""Authenticated API routes for Office documents."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, require_editor, require_viewer
from src.schemas.office import (
    OfficeDocumentAminEditRequest,
    OfficeDocumentAminEditResponse,
    OfficeDocumentCountResponse,
    OfficeDocumentCreate,
    OfficeDocumentListResponse,
    OfficeDocumentResponse,
    OfficeDocumentUpdate,
    WopiTokenResponse,
)
from src.services.office_service import (
    OfficeDocumentNotFoundError,
    OfficeService,
    build_collabora_base_url,
    build_collabora_editor_url,
    build_wopi_url,
)

router = APIRouter(prefix="/api/v1/office", tags=["office"])


def _to_response(document, request: Request) -> OfficeDocumentResponse:
    return OfficeDocumentResponse(
        id=document.id,
        org_id=document.org_id,
        owner_id=document.owner_id,
        title=document.title,
        doc_type=document.doc_type,
        storage_key=document.storage_key,
        size_bytes=document.size_bytes,
        last_modified_by=document.last_modified_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
        metadata_=document.metadata_ or {},
        wopi_url=build_wopi_url(document.id),
        collabora_url=build_collabora_base_url(request),
    )


@router.post(
    "/documents",
    response_model=OfficeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_office_document(
    payload: OfficeDocumentCreate,
    request: Request,
    ctx: RequestContext = Depends(require_editor()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    document = await service.create_document(
        ctx=ctx,
        title=payload.title,
        doc_type=payload.doc_type,
        template=payload.template,
    )
    return _to_response(document, request)


@router.get(
    "/documents",
    response_model=OfficeDocumentListResponse | OfficeDocumentCountResponse,
)
async def list_office_documents(
    request: Request,
    ctx: RequestContext = Depends(require_viewer()),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    doc_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    count_only: bool = Query(default=False),
):
    service = OfficeService(db)
    documents, total = await service.list_documents(
        ctx,
        limit=limit,
        offset=offset,
        doc_type=doc_type,
        search=search,
    )
    if count_only:
        return OfficeDocumentCountResponse(count=total)
    return OfficeDocumentListResponse(
        items=[_to_response(document, request) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/documents/{doc_id}", response_model=OfficeDocumentResponse)
async def get_office_document(
    doc_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_viewer()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        document = await service.get_document(ctx, doc_id)
    except OfficeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(document, request)


@router.patch("/documents/{doc_id}", response_model=OfficeDocumentResponse)
async def update_office_document(
    doc_id: str,
    payload: OfficeDocumentUpdate,
    request: Request,
    ctx: RequestContext = Depends(require_editor()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        document = await service.rename_document(ctx, doc_id, payload.title)
    except OfficeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(document, request)


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_office_document(
    doc_id: str,
    ctx: RequestContext = Depends(require_viewer()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        await service.delete_document(ctx, doc_id)
    except OfficeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/documents/{doc_id}/download")
async def download_office_document(
    doc_id: str,
    ctx: RequestContext = Depends(require_viewer()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        document = await service.get_document(ctx, doc_id)
    except OfficeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    file_bytes, content_type = await service.download_document(document)
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{document.title}.{document.doc_type}"',
        },
    )


@router.post("/documents/{doc_id}/wopi-token", response_model=WopiTokenResponse)
async def create_wopi_token(
    doc_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_viewer()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        document = await service.get_document(ctx, doc_id)
    except OfficeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    token = await service.generate_wopi_token(
        document,
        user_id=ctx.user.id,
        can_write=ctx.has_role("EDITOR") and document.doc_type != "pdf",
    )
    return WopiTokenResponse(
        token=token.token,
        collabora_editor_url=build_collabora_editor_url(request, doc_id, token.token),
        expires_at=token.expires_at,
    )


@router.post(
    "/documents/{doc_id}/amin-edit",
    response_model=OfficeDocumentAminEditResponse,
)
async def amin_edit_office_document(
    doc_id: str,
    payload: OfficeDocumentAminEditRequest,
    ctx: RequestContext = Depends(require_editor()),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        _document, ops_applied, summary = await service.apply_amin_edit(
            ctx,
            doc_id,
            payload.instruction,
        )
    except OfficeDocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return OfficeDocumentAminEditResponse(
        success=True,
        ops_applied=ops_applied,
        summary=summary,
    )
