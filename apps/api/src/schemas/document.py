"""Document schemas for API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Document types
DocumentType = Literal["contract", "policy", "memo", "regulatory", "other"]

# Jurisdictions
Jurisdiction = Literal["UAE", "DIFC", "ADGM", "KSA"]

# Languages
Language = Literal["en", "ar", "mixed"]

# Confidentiality levels
Confidentiality = Literal["public", "internal", "confidential", "highly_confidential"]


class DocumentVersionResponse(BaseModel):
    """Schema for document version response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    document_id: str
    version_number: int
    file_name: str
    content_type: str
    size_bytes: int
    storage_provider: str
    sha256: str
    uploaded_by_user_id: str
    created_at: datetime


class DocumentVersionSummary(BaseModel):
    """Summary of a document version (for listings)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version_number: int
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_by_user_id: str
    created_at: datetime
    # Indexing status fields
    is_indexed: bool = False
    indexed_at: datetime | None = None
    embedding_model: str | None = None


class DocumentResponse(BaseModel):
    """Schema for document response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    title: str
    document_type: str
    jurisdiction: str
    language: str
    confidentiality: str
    created_by_user_id: str
    created_at: datetime


class DocumentWithLatestVersionResponse(BaseModel):
    """Schema for document response with latest version info."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    title: str
    document_type: str
    jurisdiction: str
    language: str
    confidentiality: str
    created_by_user_id: str
    created_at: datetime
    latest_version: DocumentVersionSummary | None = None


class DocumentWithVersionsResponse(BaseModel):
    """Schema for document response with all versions."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    workspace_id: str
    title: str
    document_type: str
    jurisdiction: str
    language: str
    confidentiality: str
    created_by_user_id: str
    created_at: datetime
    versions: list[DocumentVersionSummary] = Field(default_factory=list)


class DocumentCreateResponse(BaseModel):
    """Schema for document creation response (includes initial version)."""

    model_config = ConfigDict(from_attributes=True)

    document: DocumentResponse
    version: DocumentVersionResponse


class DocumentVersionCreateResponse(BaseModel):
    """Schema for version creation response."""

    model_config = ConfigDict(from_attributes=True)

    version: DocumentVersionResponse
    document_id: str


class DocumentListResponse(BaseModel):
    """Schema for paginated document list response."""

    items: list[DocumentWithLatestVersionResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Text Extraction Schemas
# =============================================================================


class DocumentTextResponse(BaseModel):
    """Schema for extracted text response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version_id: str
    extraction_method: str
    page_count: int | None = None
    text_length: int = Field(description="Length of extracted text in characters")
    created_at: datetime
    extracted_text: str | None = Field(
        None, description="Full extracted text (only included if include_text=true)"
    )


class DocumentChunkResponse(BaseModel):
    """Schema for a single document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    chunk_index: int
    text: str
    char_start: int
    char_end: int
    page_start: int | None = None
    page_end: int | None = None


class DocumentChunksResponse(BaseModel):
    """Schema for document chunks list response."""

    version_id: str
    document_id: str
    chunk_count: int
    chunks: list[DocumentChunkResponse]
