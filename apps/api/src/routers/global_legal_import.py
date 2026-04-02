"""Global Legal Import routes for ingesting gcc-harvester snapshots.

Platform admin only endpoint for bulk importing legal instruments from snapshots.
See docs/IMPORT_CONTRACT.md for the full specification.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.platform_admin import PlatformAdminContext, require_platform_admin
from src.schemas.global_legal_import import (
    BatchReindexRequest,
    BatchReindexResponse,
    BatchStatusResponse,
    ImportInfoResponse,
    ImportLimitsSchema,
    PurgeResponse,
    SnapshotImportResponse,
    ImportFailureSchema,
    ReindexFailureSchema,
)
from src.services import log_audit_event
from src.services.global_legal_import_service import (
    MAX_FILE_SIZE_BYTES,
    MAX_RECORDS_PER_IMPORT,
    MAX_ZIP_SIZE_BYTES,
    GlobalLegalImportService,
    InvalidManifestError,
    RecordLimitExceededError,
    SnapshotImportError,
    ZipSizeLimitExceededError,
    ZipSlipError,
    batch_reindex_versions,
    get_batch_status,
    purge_all_legal_corpus,
)
from src.storage.s3 import get_storage_client


def is_valid_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))

router = APIRouter(prefix="/global/legal-import", tags=["global-legal-import"])


@router.get(
    "/info",
    response_model=ImportInfoResponse,
    summary="Get import endpoint information",
    description="Returns information about the import endpoint, including limits and documentation.",
)
async def get_import_info(
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
) -> ImportInfoResponse:
    """Get information about the import endpoint."""
    return ImportInfoResponse(
        endpoint="/global/legal-import/snapshot",
        method="POST",
        content_type="multipart/form-data",
        limits=ImportLimitsSchema(
            max_records_per_import=MAX_RECORDS_PER_IMPORT,
            max_zip_size_bytes=MAX_ZIP_SIZE_BYTES,
            max_file_size_bytes=MAX_FILE_SIZE_BYTES,
        ),
        docs_url="/docs/IMPORT_CONTRACT.md",
    )


@router.post(
    "/snapshot",
    response_model=SnapshotImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Import gcc-harvester snapshot",
    description=(
        "Import a gcc-harvester snapshot ZIP file into the global legal corpus. "
        "This endpoint is idempotent: re-importing the same snapshot will not create duplicates. "
        "Platform admin only. See docs/IMPORT_CONTRACT.md for format specification."
    ),
)
async def import_snapshot(
    request: Request,
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
    snapshot_zip: Annotated[UploadFile, File(description="GCC harvester snapshot ZIP file")],
) -> SnapshotImportResponse:
    """Import a gcc-harvester snapshot ZIP file.

    The ZIP file should contain:
    - manifest.json - Metadata about the snapshot
    - records/<connector>.jsonl - Legal instrument records
    - raw/<sha256>.<ext> - Raw artifact files (PDF, DOCX, etc.)

    Each import is idempotent:
    - Instruments are upserted by (jurisdiction, instrument_key)
    - Versions are created only if version_key doesn't exist

    Returns a summary of created/existing counts and any failures.
    """
    storage_client = get_storage_client()
    service = GlobalLegalImportService(db, storage_client)

    filename = snapshot_zip.filename or "unknown.zip"

    try:
        # Import the snapshot
        result = await service.import_snapshot(
            zip_file=snapshot_zip.file,
            filename=filename,
            user_id=ctx.user.id,
        )

        # Commit the transaction
        await db.commit()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import",
            status="success",
            resource_type="snapshot_import",
            resource_id=result.import_batch_id,
            meta={
                "import_batch_id": result.import_batch_id,
                "instruments_created": result.instruments_created,
                "instruments_existing": result.instruments_existing,
                "versions_created": result.versions_created,
                "versions_existing": result.versions_existing,
                "failure_count": result.failure_count,
                "processing_time_ms": result.processing_time_ms,
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )

        # Convert to response schema
        return SnapshotImportResponse(
            import_batch_id=result.import_batch_id,
            instruments_created=result.instruments_created,
            instruments_existing=result.instruments_existing,
            versions_created=result.versions_created,
            versions_existing=result.versions_existing,
            failures=[
                ImportFailureSchema(
                    record_index=f.record_index,
                    source_url=f.source_url,
                    error=f.error,
                )
                for f in result.failures
            ],
            failure_count=result.failure_count,
            processing_time_ms=result.processing_time_ms,
        )

    except ZipSlipError as e:
        await db.rollback()
        # Audit log security event
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import.security",
            status="fail",
            resource_type="snapshot_import",
            meta={
                "error": str(e),
                "reason": "zip_slip_attack",
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security error: {e}",
        )

    except ZipSizeLimitExceededError as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import",
            status="fail",
            resource_type="snapshot_import",
            meta={
                "error": str(e),
                "reason": "zip_size_limit_exceeded",
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except RecordLimitExceededError as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import",
            status="fail",
            resource_type="snapshot_import",
            meta={
                "error": str(e),
                "reason": "record_limit_exceeded",
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except InvalidManifestError as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import",
            status="fail",
            resource_type="snapshot_import",
            meta={
                "error": str(e),
                "reason": "invalid_manifest",
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except SnapshotImportError as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import",
            status="fail",
            resource_type="snapshot_import",
            meta={
                "error": str(e),
                "reason": "import_error",
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.import",
            status="fail",
            resource_type="snapshot_import",
            meta={
                "error": str(e)[:500],
                "reason": "unexpected_error",
                "source_file": filename,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


# =============================================================================
# Batch Reindex Endpoints
# =============================================================================


@router.get(
    "/batches/{import_batch_id}/status",
    response_model=BatchStatusResponse,
    summary="Get import batch indexing status",
    description="Returns the indexing status of an import batch, including counts of indexed and pending versions.",
)
async def get_batch_indexing_status(
    import_batch_id: str,
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchStatusResponse:
    """Get the indexing status of an import batch.

    Returns counts of total, indexed, and pending versions.
    """
    # Validate UUID format
    if not is_valid_uuid(import_batch_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid import_batch_id: must be a valid UUID",
        )

    batch_status = await get_batch_status(db, import_batch_id)

    if batch_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No versions found for import_batch_id: {import_batch_id}",
        )

    return BatchStatusResponse(
        import_batch_id=batch_status.import_batch_id,
        total_versions=batch_status.total_versions,
        indexed_versions=batch_status.indexed_versions,
        pending_versions=batch_status.pending_versions,
        last_imported_at=batch_status.last_imported_at,
    )


@router.post(
    "/reindex",
    response_model=BatchReindexResponse,
    status_code=status.HTTP_200_OK,
    summary="Reindex versions from an import batch",
    description=(
        "Reindex up to max_versions unindexed versions from a specific import batch. "
        "Platform admin only. Continues on failures and returns a summary."
    ),
)
async def reindex_batch_versions(
    request: Request,
    body: BatchReindexRequest,
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BatchReindexResponse:
    """Reindex versions from an import batch.

    Finds up to max_versions LegalInstrumentVersion rows where:
    - import_batch_id matches
    - is_indexed=false

    For each version, runs extraction/chunking/embedding using existing logic.
    Continues on failures and returns a summary.
    """
    # Validate UUID format
    if not is_valid_uuid(body.import_batch_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid import_batch_id: must be a valid UUID",
        )

    storage_client = get_storage_client()

    try:
        result = await batch_reindex_versions(
            db=db,
            storage_client=storage_client,
            import_batch_id=body.import_batch_id,
            max_versions=body.max_versions,
            index_all=body.index_all,
        )

        # Commit any changes
        await db.commit()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.reindex_batch",
            status="success" if result.failed == 0 else "partial",
            resource_type="batch_reindex",
            resource_id=body.import_batch_id,
            meta={
                "import_batch_id": body.import_batch_id,
                "attempted": result.attempted,
                "indexed": result.indexed,
                "failed": result.failed,
                "max_versions": body.max_versions,
                "index_all": body.index_all,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )

        return BatchReindexResponse(
            import_batch_id=result.import_batch_id,
            attempted=result.attempted,
            indexed=result.indexed,
            failed=result.failed,
            failures=[
                ReindexFailureSchema(
                    version_id=f.version_id,
                    instrument_id=f.instrument_id,
                    error=f.error,
                )
                for f in result.failures
            ],
        )

    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.reindex_batch",
            status="fail",
            resource_type="batch_reindex",
            resource_id=body.import_batch_id,
            meta={
                "import_batch_id": body.import_batch_id,
                "error": str(e)[:500],
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}",
        )


# =============================================================================
# Purge All Endpoint
# =============================================================================


@router.delete(
    "/purge-all",
    response_model=PurgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Purge all legal corpus data",
    description=(
        "Delete ALL legal instruments, versions, chunks, embeddings, and texts from the database. "
        "This is a destructive operation and cannot be undone. "
        "Platform admin only. S3 files are NOT deleted."
    ),
)
async def purge_all_legal_data(
    request: Request,
    ctx: Annotated[PlatformAdminContext, Depends(require_platform_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PurgeResponse:
    """Purge all legal corpus data from the database.

    This endpoint deletes:
    - All legal instruments
    - All legal instrument versions
    - All legal chunks
    - All legal chunk embeddings
    - All legal texts

    WARNING: This is a destructive operation and cannot be undone.
    S3 files are NOT deleted by this operation.
    """
    try:
        result = await purge_all_legal_corpus(db)

        # Commit the transaction
        await db.commit()

        # Audit log
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.purge_all",
            status="success",
            resource_type="legal_corpus",
            meta={
                "instruments_deleted": result.instruments_deleted,
                "versions_deleted": result.versions_deleted,
                "chunks_deleted": result.chunks_deleted,
                "embeddings_deleted": result.embeddings_deleted,
                "texts_deleted": result.texts_deleted,
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )

        return PurgeResponse(
            instruments_deleted=result.instruments_deleted,
            versions_deleted=result.versions_deleted,
            chunks_deleted=result.chunks_deleted,
            embeddings_deleted=result.embeddings_deleted,
            texts_deleted=result.texts_deleted,
            message="Successfully purged all legal corpus data. S3 files were NOT deleted.",
        )

    except Exception as e:
        await db.rollback()
        await log_audit_event(
            db=db,
            ctx=None,
            action="global_legal.purge_all",
            status="fail",
            resource_type="legal_corpus",
            meta={
                "error": str(e)[:500],
            },
            request=request,
            tenant_id=ctx.tenant.id,
            user_id=ctx.user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Purge failed: {str(e)}",
        )
