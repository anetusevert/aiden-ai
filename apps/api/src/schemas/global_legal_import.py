"""Schemas for the global legal import endpoint.

These schemas define the request/response format for the snapshot import API.
See docs/IMPORT_CONTRACT.md for the full specification.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImportFailureSchema(BaseModel):
    """A single import failure."""

    record_index: int = Field(..., description="Index of the failed record in the snapshot")
    source_url: str | None = Field(None, description="Source URL of the failed record (if available)")
    error: str = Field(..., description="Error message describing the failure")


class SnapshotImportResponse(BaseModel):
    """Response from the snapshot import endpoint."""

    import_batch_id: str = Field(..., description="UUID identifying this import batch")
    instruments_created: int = Field(..., ge=0, description="Number of new instruments created")
    instruments_existing: int = Field(..., ge=0, description="Number of instruments that already existed")
    versions_created: int = Field(..., ge=0, description="Number of new versions created")
    versions_existing: int = Field(..., ge=0, description="Number of versions that already existed (skipped)")
    failures: list[ImportFailureSchema] = Field(
        default_factory=list,
        description="First 20 failures (for debugging)",
    )
    failure_count: int = Field(..., ge=0, description="Total number of failed records")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "instruments_created": 45,
                "instruments_existing": 5,
                "versions_created": 48,
                "versions_existing": 2,
                "failures": [
                    {
                        "record_index": 12,
                        "source_url": "https://example.com/law/123",
                        "error": "Missing raw artifact file",
                    }
                ],
                "failure_count": 3,
                "processing_time_ms": 12500,
            }
        }
    }


class ImportLimitsSchema(BaseModel):
    """Import limits for client information."""

    max_records_per_import: int = Field(..., description="Maximum number of records per import")
    max_zip_size_bytes: int = Field(..., description="Maximum ZIP file size in bytes")
    max_file_size_bytes: int = Field(..., description="Maximum individual file size in bytes")


class ImportInfoResponse(BaseModel):
    """Response with import endpoint information."""

    endpoint: str = Field(..., description="Import endpoint path")
    method: str = Field(..., description="HTTP method")
    content_type: str = Field(..., description="Expected content type")
    limits: ImportLimitsSchema = Field(..., description="Import limits")
    docs_url: str = Field(..., description="URL to import contract documentation")


# =============================================================================
# Batch Reindex Schemas
# =============================================================================

class BatchReindexRequest(BaseModel):
    """Request to reindex versions from a specific import batch."""

    import_batch_id: str = Field(..., description="UUID of the import batch to reindex")
    max_versions: int = Field(
        default=25,
        ge=1,
        le=5000,
        description="Maximum number of versions to reindex in this request (1-5000, default 25)",
    )
    index_all: bool = Field(
        default=False,
        description="If true, index ALL pending versions regardless of max_versions limit",
    )


class ReindexFailureSchema(BaseModel):
    """A single reindex failure."""

    version_id: str = Field(..., description="Version ID that failed to reindex")
    instrument_id: str = Field(..., description="Parent instrument ID")
    error: str = Field(..., description="Error message describing the failure")


class BatchReindexResponse(BaseModel):
    """Response from the batch reindex endpoint."""

    import_batch_id: str = Field(..., description="UUID of the import batch")
    attempted: int = Field(..., ge=0, description="Number of versions attempted")
    indexed: int = Field(..., ge=0, description="Number of versions successfully indexed")
    failed: int = Field(..., ge=0, description="Number of versions that failed to index")
    failures: list[ReindexFailureSchema] = Field(
        default_factory=list,
        description="First 20 failures (for debugging)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "attempted": 25,
                "indexed": 23,
                "failed": 2,
                "failures": [
                    {
                        "version_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                        "instrument_id": "550e8400-e29b-41d4-a716-446655440000",
                        "error": "Failed to extract text from PDF",
                    }
                ],
            }
        }
    }


class BatchStatusResponse(BaseModel):
    """Status of an import batch for indexing progress."""

    import_batch_id: str = Field(..., description="UUID of the import batch")
    total_versions: int = Field(..., ge=0, description="Total versions in this batch")
    indexed_versions: int = Field(..., ge=0, description="Number of indexed versions")
    pending_versions: int = Field(..., ge=0, description="Number of versions awaiting indexing")
    last_imported_at: datetime | None = Field(None, description="Most recent import timestamp in batch")

    model_config = {
        "json_schema_extra": {
            "example": {
                "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_versions": 150,
                "indexed_versions": 75,
                "pending_versions": 75,
                "last_imported_at": "2025-01-27T12:00:00Z",
            }
        }
    }


# =============================================================================
# Purge Schemas
# =============================================================================


class PurgeResponse(BaseModel):
    """Response from the purge-all endpoint."""

    instruments_deleted: int = Field(..., ge=0, description="Number of instruments deleted")
    versions_deleted: int = Field(..., ge=0, description="Number of versions deleted")
    chunks_deleted: int = Field(..., ge=0, description="Number of chunks deleted")
    embeddings_deleted: int = Field(..., ge=0, description="Number of embeddings deleted")
    texts_deleted: int = Field(..., ge=0, description="Number of texts deleted")
    message: str = Field(..., description="Summary message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "instruments_deleted": 100,
                "versions_deleted": 100,
                "chunks_deleted": 5000,
                "embeddings_deleted": 5000,
                "texts_deleted": 100,
                "message": "Successfully purged all legal corpus data. S3 files were NOT deleted.",
            }
        }
    }
