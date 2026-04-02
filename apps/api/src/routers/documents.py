"""Document vault routes.

Endpoints for document upload, versioning, listing, download, and text extraction.
All endpoints require JWT auth and workspace context.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, get_workspace_context, require_editor, require_viewer
from src.schemas.document import (
    DocumentChunkResponse,
    DocumentChunksResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentTextResponse,
    DocumentVersionCreateResponse,
    DocumentVersionResponse,
    DocumentVersionSummary,
    DocumentWithLatestVersionResponse,
    DocumentWithVersionsResponse,
)
from src.services import (
    DocumentNotFoundError,
    DocumentService,
    DocumentUploadError,
    DocumentVersionNotFoundError,
    ExtractionService,
    PolicyViolationError,
    log_audit_event,
)
from src.storage.s3 import get_storage_client

router = APIRouter(prefix="/documents", tags=["documents"])


def _version_to_summary(version) -> DocumentVersionSummary:
    """Convert a DocumentVersion to a summary."""
    return DocumentVersionSummary(
        id=version.id,
        version_number=version.version_number,
        file_name=version.file_name,
        content_type=version.content_type,
        size_bytes=version.size_bytes,
        uploaded_by_user_id=version.uploaded_by_user_id,
        created_at=version.created_at,
        is_indexed=version.is_indexed,
        indexed_at=version.indexed_at,
        embedding_model=version.embedding_model,
    )


# =============================================================================
# Create Document with Initial Version
# =============================================================================


@router.post(
    "",
    response_model=DocumentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new document",
    description="Create a new document with initial version. Requires EDITOR role or higher.",
)
async def create_document(
    request: Request,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Document file to upload")],
    title: Annotated[str, Form(description="Document title")],
    document_type: Annotated[
        str, Form(description="Document type (contract, policy, memo, regulatory, other)")
    ],
    jurisdiction: Annotated[str, Form(description="Jurisdiction (UAE, DIFC, ADGM, KSA)")],
    language: Annotated[str, Form(description="Language (en, ar, mixed)")],
    confidentiality: Annotated[
        str,
        Form(
            description="Confidentiality level (public, internal, confidential, highly_confidential)"
        ),
    ],
) -> DocumentCreateResponse:
    """Upload a new document with initial version.

    The document metadata is validated against the workspace policy.
    File is stored in S3/MinIO.
    """
    storage_client = get_storage_client()
    service = DocumentService(db, storage_client)

    # Read file content
    file_content = await file.read()
    file_name = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"

    try:
        document, version = await service.create_document(
            ctx=ctx,
            title=title,
            document_type=document_type,
            jurisdiction=jurisdiction,
            language=language,
            confidentiality=confidentiality,
            file_name=file_name,
            content_type=content_type,
            file_data=file_content,
        )

        # Audit log
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.upload",
            status="success",
            resource_type="document",
            resource_id=document.id,
            meta={
                "title": title,
                "document_type": document_type,
                "jurisdiction": jurisdiction,
                "language": language,
                "confidentiality": confidentiality,
                "file_name": file_name,
                "file_size_bytes": len(file_content),
                "version_number": version.version_number,
            },
            request=request,
        )

        # Perform text extraction (async, after successful upload)
        extraction_success, extraction_meta = await service.extract_version_text(
            ctx=ctx,
            version=version,
            file_bytes=file_content,
            content_type=content_type,
        )

        if extraction_success:
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="document.extract.success",
                status="success",
                resource_type="document_version",
                resource_id=version.id,
                meta=extraction_meta,
                request=request,
            )
        else:
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="document.extract.fail",
                status="fail",
                resource_type="document_version",
                resource_id=version.id,
                meta=extraction_meta,
                request=request,
            )

        return DocumentCreateResponse(
            document=DocumentResponse.model_validate(document),
            version=DocumentVersionResponse.model_validate(version),
        )

    except PolicyViolationError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.upload",
            status="fail",
            resource_type="document",
            meta={
                "reason": e.reason,
                "error_message": str(e),
                "title": title,
                "document_type": document_type,
                "jurisdiction": jurisdiction,
                "language": language,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except DocumentUploadError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.upload",
            status="fail",
            resource_type="document",
            meta={
                "reason": "upload_failed",
                "error_message": str(e),
                "title": title,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# Create New Version
# =============================================================================


@router.post(
    "/{document_id}/versions",
    response_model=DocumentVersionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new version",
    description="Upload a new version for an existing document. Requires EDITOR role or higher.",
)
async def create_version(
    request: Request,
    document_id: Annotated[str, Path(description="Document ID")],
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(description="Document file to upload")],
) -> DocumentVersionCreateResponse:
    """Upload a new version for an existing document.

    Version number is automatically incremented.
    File is stored in S3/MinIO.
    """
    storage_client = get_storage_client()
    service = DocumentService(db, storage_client)

    # Read file content
    file_content = await file.read()
    file_name = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"

    try:
        version = await service.create_version(
            ctx=ctx,
            document_id=document_id,
            file_name=file_name,
            content_type=content_type,
            file_data=file_content,
        )

        # Audit log
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.version.upload",
            status="success",
            resource_type="document_version",
            resource_id=version.id,
            meta={
                "document_id": document_id,
                "file_name": file_name,
                "file_size_bytes": len(file_content),
                "version_number": version.version_number,
            },
            request=request,
        )

        # Perform text extraction (async, after successful upload)
        extraction_success, extraction_meta = await service.extract_version_text(
            ctx=ctx,
            version=version,
            file_bytes=file_content,
            content_type=content_type,
        )

        if extraction_success:
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="document.extract.success",
                status="success",
                resource_type="document_version",
                resource_id=version.id,
                meta=extraction_meta,
                request=request,
            )
        else:
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="document.extract.fail",
                status="fail",
                resource_type="document_version",
                resource_id=version.id,
                meta=extraction_meta,
                request=request,
            )

        return DocumentVersionCreateResponse(
            version=DocumentVersionResponse.model_validate(version),
            document_id=document_id,
        )

    except DocumentNotFoundError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.version.upload",
            status="fail",
            resource_type="document_version",
            meta={
                "reason": "document_not_found",
                "document_id": document_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except DocumentUploadError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.version.upload",
            status="fail",
            resource_type="document_version",
            meta={
                "reason": "upload_failed",
                "error_message": str(e),
                "document_id": document_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# =============================================================================
# List Documents
# =============================================================================


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List all documents in the workspace. Requires VIEWER role or higher.",
)
async def list_documents(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of documents")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of documents to skip")] = 0,
) -> DocumentListResponse:
    """List all documents in the workspace with their latest version."""
    storage_client = get_storage_client()
    service = DocumentService(db, storage_client)

    documents, total = await service.list_documents(ctx, limit=limit, offset=offset)

    # Build response with latest version for each document
    items = []
    for doc in documents:
        latest_version = None
        if doc.versions:
            # Versions are ordered by version_number desc
            latest = doc.versions[0]
            latest_version = _version_to_summary(latest)

        items.append(
            DocumentWithLatestVersionResponse(
                id=doc.id,
                tenant_id=doc.tenant_id,
                workspace_id=doc.workspace_id,
                title=doc.title,
                document_type=doc.document_type,
                jurisdiction=doc.jurisdiction,
                language=doc.language,
                confidentiality=doc.confidentiality,
                created_by_user_id=doc.created_by_user_id,
                created_at=doc.created_at,
                latest_version=latest_version,
            )
        )

    return DocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# Get Document with Versions
# =============================================================================


@router.get(
    "/{document_id}",
    response_model=DocumentWithVersionsResponse,
    summary="Get document details",
    description="Get document details with all versions. Requires VIEWER role or higher.",
)
async def get_document(
    document_id: Annotated[str, Path(description="Document ID")],
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentWithVersionsResponse:
    """Get document details with all versions."""
    storage_client = get_storage_client()
    service = DocumentService(db, storage_client)

    document = await service.get_document_with_versions(ctx, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )

    # Convert versions to summaries
    versions = [_version_to_summary(v) for v in document.versions]

    return DocumentWithVersionsResponse(
        id=document.id,
        tenant_id=document.tenant_id,
        workspace_id=document.workspace_id,
        title=document.title,
        document_type=document.document_type,
        jurisdiction=document.jurisdiction,
        language=document.language,
        confidentiality=document.confidentiality,
        created_by_user_id=document.created_by_user_id,
        created_at=document.created_at,
        versions=versions,
    )


# =============================================================================
# Download Version
# =============================================================================


@router.get(
    "/{document_id}/versions/{version_id}/download",
    summary="Download document version",
    description="Download a specific version of a document. Requires VIEWER role or higher.",
    responses={
        200: {
            "description": "File content",
            "content": {"application/octet-stream": {}},
        },
        404: {"description": "Document or version not found"},
    },
)
async def download_version(
    request: Request,
    document_id: Annotated[str, Path(description="Document ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Download a specific version of a document."""
    storage_client = get_storage_client()
    service = DocumentService(db, storage_client)

    try:
        data, content_type, filename = await service.download_version(
            ctx=ctx,
            document_id=document_id,
            version_id=version_id,
        )

        # Audit log
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.download",
            status="success",
            resource_type="document_version",
            resource_id=version_id,
            meta={
                "document_id": document_id,
                "version_id": version_id,
                "file_name": filename,
                "file_size_bytes": len(data),
            },
            request=request,
        )

        # Build response with proper headers
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }

        return Response(
            content=data,
            media_type=content_type,
            headers=headers,
        )

    except DocumentVersionNotFoundError as e:
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="document.download",
            status="fail",
            resource_type="document_version",
            resource_id=version_id,
            meta={
                "reason": "version_not_found",
                "document_id": document_id,
                "version_id": version_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# =============================================================================
# Get Extracted Text
# =============================================================================


@router.get(
    "/{document_id}/versions/{version_id}/text",
    response_model=DocumentTextResponse,
    summary="Get extracted text",
    description="Get extracted text metadata for a document version. Requires VIEWER role or higher.",
)
async def get_version_text(
    document_id: Annotated[str, Path(description="Document ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_text: Annotated[
        bool, Query(description="Include the full extracted text in response")
    ] = False,
) -> DocumentTextResponse:
    """Get extracted text for a document version.

    By default, only metadata is returned. Set include_text=true to get the full text.
    """
    storage_client = get_storage_client()
    doc_service = DocumentService(db, storage_client)

    # First verify the version exists and belongs to the document/workspace
    version = await doc_service.get_version(ctx, document_id, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found for document '{document_id}'",
        )

    # Get extracted text
    extraction_service = ExtractionService(db)
    doc_text = await extraction_service.get_document_text(ctx, document_id, version_id)

    if doc_text is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No extracted text found for version '{version_id}'",
        )

    return DocumentTextResponse(
        id=doc_text.id,
        version_id=doc_text.version_id,
        extraction_method=doc_text.extraction_method,
        page_count=doc_text.page_count,
        text_length=len(doc_text.extracted_text),
        created_at=doc_text.created_at,
        extracted_text=doc_text.extracted_text if include_text else None,
    )


# =============================================================================
# Get Document Chunks
# =============================================================================


@router.get(
    "/{document_id}/versions/{version_id}/chunks",
    response_model=DocumentChunksResponse,
    summary="Get document chunks",
    description="Get text chunks for a document version. Requires VIEWER role or higher.",
)
async def get_version_chunks(
    document_id: Annotated[str, Path(description="Document ID")],
    version_id: Annotated[str, Path(description="Version ID")],
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentChunksResponse:
    """Get all chunks for a document version.

    Chunks are ordered by chunk_index and include character offsets.
    """
    storage_client = get_storage_client()
    doc_service = DocumentService(db, storage_client)

    # First verify the version exists and belongs to the document/workspace
    version = await doc_service.get_version(ctx, document_id, version_id)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version '{version_id}' not found for document '{document_id}'",
        )

    # Get chunks
    extraction_service = ExtractionService(db)
    chunks = await extraction_service.get_document_chunks(ctx, document_id, version_id)

    return DocumentChunksResponse(
        version_id=version_id,
        document_id=document_id,
        chunk_count=len(chunks),
        chunks=[
            DocumentChunkResponse(
                id=chunk.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
            )
            for chunk in chunks
        ],
    )
