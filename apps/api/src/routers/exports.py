"""Export endpoints for Aiden.ai.

This module contains endpoints for exporting workflow results to DOCX format
with full traceability and audit support.

Security hardening:
- Evidence chunk IDs in payloads are validated against the database
- Workspace chunks must belong to the specified document/version/workspace
- Global legal chunks must exist in the legal_chunks table
- Invalid references are rejected with error_code="export_validation_failed"

Unified Evidence Support:
- Supports export of mixed evidence (workspace + global legal)
- Global legal chunks are validated against legal_chunks table
- Source type is preserved in the export for traceability
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, require_viewer
from src.middleware.request_id import get_request_id
from src.models.document_chunk import DocumentChunk
from src.models.legal_chunk import LegalChunk
from src.schemas.export import (
    ClauseRedlinesExportRequest,
    ContractReviewExportRequest,
)
from src.schemas.workflow_status import WorkflowResultStatus
from src.services import log_audit_event
from src.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])


# DOCX MIME type
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _generate_filename(document_title: str, workflow: str) -> str:
    """Generate a filename for the exported document.

    Args:
        document_title: Title of the source document
        workflow: Workflow type identifier

    Returns:
        Sanitized filename with date
    """
    # Sanitize document title for filename
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_" for c in document_title
    ).strip()
    safe_title = safe_title[:50]  # Limit length

    # Format: <title>_<workflow>_<date>.docx
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{safe_title}_{workflow}_{date_str}.docx"


def _validate_exportable_status(workflow_status: WorkflowResultStatus) -> None:
    """Validate that the workflow status is exportable.

    Exportable statuses: success, insufficient_sources

    Args:
        workflow_status: The workflow result status

    Raises:
        HTTPException: If status is not exportable
    """
    exportable_statuses = {
        WorkflowResultStatus.SUCCESS,
        WorkflowResultStatus.INSUFFICIENT_SOURCES,
    }

    if workflow_status not in exportable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow status '{workflow_status.value}' is not exportable. "
            f"Only 'success' and 'insufficient_sources' results can be exported.",
        )


async def _validate_evidence_chunks(
    db: AsyncSession,
    ctx: RequestContext,
    workspace_chunk_ids: set[str],
    global_chunk_ids: set[str],
    document_id: str,
    version_id: str,
) -> tuple[int, int, int, int]:
    """Validate evidence chunk IDs from both workspace and global sources.

    Workspace chunks must belong to the specified document/version/workspace.
    Global legal chunks must exist in the legal_chunks table.

    Args:
        db: Database session
        ctx: Request context with tenant/workspace info
        workspace_chunk_ids: Set of workspace chunk IDs from the export payload
        global_chunk_ids: Set of global legal chunk IDs from the export payload
        document_id: Document ID from metadata
        version_id: Version ID from metadata

    Returns:
        Tuple of (workspace_valid, workspace_invalid, global_valid, global_invalid)

    Raises:
        HTTPException: If any chunk IDs are invalid
    """
    workspace_valid = 0
    workspace_invalid = 0
    global_valid = 0
    global_invalid = 0

    # Validate workspace chunks
    if workspace_chunk_ids:
        stmt = select(DocumentChunk.id).where(
            DocumentChunk.id.in_(workspace_chunk_ids),
            DocumentChunk.document_id == document_id,
            DocumentChunk.version_id == version_id,
            DocumentChunk.workspace_id == ctx.workspace.id,
            DocumentChunk.tenant_id == ctx.tenant.id,
        )
        result = await db.execute(stmt)
        valid_ids = {row[0] for row in result.fetchall()}
        workspace_valid = len(valid_ids)
        workspace_invalid = len(workspace_chunk_ids) - workspace_valid

    # Validate global legal chunks (they just need to exist in legal_chunks)
    if global_chunk_ids:
        stmt = select(LegalChunk.id).where(
            LegalChunk.id.in_(global_chunk_ids),
        )
        result = await db.execute(stmt)
        valid_ids = {row[0] for row in result.fetchall()}
        global_valid = len(valid_ids)
        global_invalid = len(global_chunk_ids) - global_valid

    total_invalid = workspace_invalid + global_invalid
    if total_invalid > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "export_validation_failed",
                "message": "Export payload references invalid evidence chunks.",
                "workspace_invalid_count": workspace_invalid,
                "global_invalid_count": global_invalid,
                "workspace_valid_count": workspace_valid,
                "global_valid_count": global_valid,
            },
        )

    return workspace_valid, workspace_invalid, global_valid, global_invalid


def _extract_chunk_ids_from_contract_review(
    body: ContractReviewExportRequest,
) -> tuple[set[str], set[str]]:
    """Extract evidence chunk IDs from a contract review export request.

    Separates workspace chunks from global legal chunks based on source_type.

    Returns:
        Tuple of (workspace_chunk_ids, global_chunk_ids)
    """
    workspace_ids: set[str] = set()
    global_ids: set[str] = set()

    for finding in body.workflow_result.findings:
        for evidence in finding.evidence:
            if evidence.chunk_id:
                if evidence.source_type == "global_legal":
                    global_ids.add(evidence.chunk_id)
                else:
                    workspace_ids.add(evidence.chunk_id)

    return workspace_ids, global_ids


def _extract_chunk_ids_from_clause_redlines(
    body: ClauseRedlinesExportRequest,
) -> tuple[set[str], set[str]]:
    """Extract evidence chunk IDs from a clause redlines export request.

    Separates workspace chunks from global legal chunks based on source_type.

    Returns:
        Tuple of (workspace_chunk_ids, global_chunk_ids)
    """
    workspace_ids: set[str] = set()
    global_ids: set[str] = set()

    for item in body.workflow_result.items:
        for evidence in item.evidence:
            if evidence.chunk_id:
                if evidence.source_type == "global_legal":
                    global_ids.add(evidence.chunk_id)
                else:
                    workspace_ids.add(evidence.chunk_id)

    return workspace_ids, global_ids


@router.post(
    "/contract-review",
    summary="Export contract review results to DOCX",
    description="""
Export a completed contract review workflow result to a DOCX document.

The exported document includes:
- Cover page with document metadata
- Executive summary (with disclaimer if insufficient sources)
- Detailed findings with severity, category, issue, and recommendation
- Numbered citations section
- Evidence appendix with full snippets
- Traceability footer with LLM provider, model, and prompt hash

**Exportable statuses**: Only `success` and `insufficient_sources` results can be exported.

**Role required**: VIEWER or higher.

**Important**: This endpoint does NOT re-run the LLM. It only serializes existing results.
""",
    response_class=Response,
    responses={
        200: {
            "content": {DOCX_MIME_TYPE: {}},
            "description": "DOCX file download",
        },
        400: {"description": "Workflow status not exportable"},
        403: {"description": "Access denied"},
    },
)
async def export_contract_review(
    request: Request,
    body: ContractReviewExportRequest,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export contract review results to DOCX.

    This endpoint:
    1. Validates the workflow result is exportable
    2. Generates a DOCX document in-memory
    3. Returns the document as a download

    No LLM calls are made - this only serializes existing results.
    """
    request_id = get_request_id(request)
    workspace_evidence_count = 0
    global_evidence_count = 0
    invalid_reference_count = 0

    try:
        # Validate status is exportable
        _validate_exportable_status(body.workflow_result.meta.status)

        # Server-side validation: verify evidence chunks exist in DB
        workspace_ids, global_ids = _extract_chunk_ids_from_contract_review(body)
        if workspace_ids or global_ids:
            ws_valid, ws_invalid, gl_valid, gl_invalid = await _validate_evidence_chunks(
                db=db,
                ctx=ctx,
                workspace_chunk_ids=workspace_ids,
                global_chunk_ids=global_ids,
                document_id=body.document_metadata.document_id,
                version_id=body.document_metadata.version_id,
            )
            workspace_evidence_count = ws_valid
            global_evidence_count = gl_valid
            invalid_reference_count = ws_invalid + gl_invalid

        # Generate DOCX
        export_service = ExportService()
        docx_bytes = export_service.generate_contract_review_docx(
            result=body.workflow_result,
            metadata=body.document_metadata,
        )

        # Generate filename
        filename = _generate_filename(
            body.document_metadata.document_title,
            "contract-review",
        )

        # Audit log success
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="export.contract_review.success",
            status="success",
            resource_type="document",
            resource_id=body.document_metadata.document_id,
            meta={
                "workflow": "CONTRACT_REVIEW_V1",
                "result_status": body.workflow_result.meta.status.value,
                "prompt_hash": body.workflow_result.meta.prompt_hash,
                "document_id": body.document_metadata.document_id,
                "version_id": body.document_metadata.version_id,
                "filename": filename,
                "file_size_bytes": len(docx_bytes),
                "findings_count": len(body.workflow_result.findings),
                "workspace_evidence_count": workspace_evidence_count,
                "global_evidence_count": global_evidence_count,
                "invalid_reference_count": invalid_reference_count,
                "evidence_scope": body.workflow_result.meta.evidence_scope,
            },
            request=request,
        )

        # Return DOCX file
        return Response(
            content=docx_bytes,
            media_type=DOCX_MIME_TYPE,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Request-Id": request_id or "",
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        # Log failure and re-raise
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="export.contract_review.fail",
            status="fail",
            resource_type="document",
            resource_id=body.document_metadata.document_id,
            meta={
                "workflow": "CONTRACT_REVIEW_V1",
                "prompt_hash": body.workflow_result.meta.prompt_hash,
                "document_id": body.document_metadata.document_id,
                "version_id": body.document_metadata.version_id,
                "error": str(e)[:200],
                "workspace_evidence_count": workspace_evidence_count,
                "global_evidence_count": global_evidence_count,
                "invalid_reference_count": invalid_reference_count,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )


@router.post(
    "/clause-redlines",
    summary="Export clause redlines results to DOCX",
    description="""
Export a completed clause redlines workflow result to a DOCX document.

The exported document includes:
- Cover page with document metadata
- Executive summary (with disclaimer if insufficient sources)
- Clause analysis with status, severity, confidence, and recommended text
- Numbered citations section
- Evidence appendix with full snippets
- Traceability footer with LLM provider, model, and prompt hash

**Exportable statuses**: Only `success` and `insufficient_sources` results can be exported.

**Role required**: VIEWER or higher.

**Important**: This endpoint does NOT re-run the LLM. It only serializes existing results.
""",
    response_class=Response,
    responses={
        200: {
            "content": {DOCX_MIME_TYPE: {}},
            "description": "DOCX file download",
        },
        400: {"description": "Workflow status not exportable"},
        403: {"description": "Access denied"},
    },
)
async def export_clause_redlines(
    request: Request,
    body: ClauseRedlinesExportRequest,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Export clause redlines results to DOCX.

    This endpoint:
    1. Validates the workflow result is exportable
    2. Validates evidence chunks exist in the database
    3. Generates a DOCX document in-memory
    4. Returns the document as a download

    No LLM calls are made - this only serializes existing results.
    """
    request_id = get_request_id(request)
    workspace_evidence_count = 0
    global_evidence_count = 0
    invalid_reference_count = 0

    try:
        # Validate status is exportable
        _validate_exportable_status(body.workflow_result.meta.status)

        # Server-side validation: verify evidence chunks exist in DB
        workspace_ids, global_ids = _extract_chunk_ids_from_clause_redlines(body)
        if workspace_ids or global_ids:
            ws_valid, ws_invalid, gl_valid, gl_invalid = await _validate_evidence_chunks(
                db=db,
                ctx=ctx,
                workspace_chunk_ids=workspace_ids,
                global_chunk_ids=global_ids,
                document_id=body.document_metadata.document_id,
                version_id=body.document_metadata.version_id,
            )
            workspace_evidence_count = ws_valid
            global_evidence_count = gl_valid
            invalid_reference_count = ws_invalid + gl_invalid

        # Generate DOCX
        export_service = ExportService()
        docx_bytes = export_service.generate_clause_redlines_docx(
            result=body.workflow_result,
            metadata=body.document_metadata,
        )

        # Generate filename
        filename = _generate_filename(
            body.document_metadata.document_title,
            "clause-redlines",
        )

        # Audit log success
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="export.clause_redlines.success",
            status="success",
            resource_type="document",
            resource_id=body.document_metadata.document_id,
            meta={
                "workflow": "CLAUSE_REDLINES_V1",
                "result_status": body.workflow_result.meta.status.value,
                "prompt_hash": body.workflow_result.meta.prompt_hash,
                "document_id": body.document_metadata.document_id,
                "version_id": body.document_metadata.version_id,
                "filename": filename,
                "file_size_bytes": len(docx_bytes),
                "items_count": len(body.workflow_result.items),
                "jurisdiction": body.workflow_result.meta.jurisdiction,
                "workspace_evidence_count": workspace_evidence_count,
                "global_evidence_count": global_evidence_count,
                "invalid_reference_count": invalid_reference_count,
                "evidence_scope": body.workflow_result.meta.evidence_scope,
            },
            request=request,
        )

        # Return DOCX file
        return Response(
            content=docx_bytes,
            media_type=DOCX_MIME_TYPE,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Request-Id": request_id or "",
            },
        )

    except HTTPException:
        raise

    except Exception as e:
        # Log failure and re-raise
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="export.clause_redlines.fail",
            status="fail",
            resource_type="document",
            resource_id=body.document_metadata.document_id,
            meta={
                "workflow": "CLAUSE_REDLINES_V1",
                "prompt_hash": body.workflow_result.meta.prompt_hash,
                "document_id": body.document_metadata.document_id,
                "version_id": body.document_metadata.version_id,
                "error": str(e)[:200],
                "workspace_evidence_count": workspace_evidence_count,
                "global_evidence_count": global_evidence_count,
                "invalid_reference_count": invalid_reference_count,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}",
        )
