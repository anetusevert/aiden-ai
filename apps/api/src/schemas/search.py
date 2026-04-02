"""Search schemas for retrieval API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SearchChunkResult(BaseModel):
    """A single chunk search result with scores and metadata.

    This schema provides clear provenance for user trust:
    - source_type: Always "workspace_document" for workspace documents
    - source_label: Human-readable source description (e.g., "Employment Agreement")
    """

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="Unique identifier of the chunk")
    chunk_index: int = Field(..., description="Index of chunk within the document version")
    snippet: str = Field(..., description="Truncated chunk text (max 300 chars)")

    # Document metadata
    document_id: str = Field(..., description="Document ID")
    version_id: str = Field(..., description="Version ID")
    document_title: str = Field(..., description="Document title")
    document_type: str = Field(..., description="Document type (contract, policy, etc.)")
    jurisdiction: str = Field(..., description="Jurisdiction (UAE, DIFC, etc.)")
    language: str = Field(..., description="Language (en, ar, mixed)")

    # Offsets for citation
    char_start: int = Field(..., description="Character offset start in document text")
    char_end: int = Field(..., description="Character offset end in document text")
    page_start: int | None = Field(None, description="Start page number (if available)")
    page_end: int | None = Field(None, description="End page number (if available)")

    # Scores
    vector_score: float = Field(..., description="Normalized vector similarity score (0-1)")
    keyword_score: float = Field(..., description="Normalized keyword match score (0-1)")
    final_score: float = Field(..., description="Combined final score (0-1)")

    # =========================================================================
    # Source Provenance Fields (User Trust / Transparency)
    # =========================================================================

    source_type: Literal["workspace_document"] = Field(
        default="workspace_document",
        description="Source type: always 'workspace_document' for workspace documents"
    )
    source_label: str = Field(
        default="",
        description="Human-readable source label (document title)"
    )


class SearchChunksResponse(BaseModel):
    """Response for chunk search endpoint."""

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="The search query")
    total: int = Field(..., description="Total number of results returned")
    results: list[SearchChunkResult] = Field(..., description="Search results ordered by relevance")


class ReindexRequest(BaseModel):
    """Request for reindex endpoint (empty - uses path params)."""

    pass


class ReindexResponse(BaseModel):
    """Response for reindex endpoint."""

    model_config = ConfigDict(from_attributes=True)

    document_id: str = Field(..., description="Document ID that was reindexed")
    version_id: str = Field(..., description="Version ID that was reindexed")
    chunks_indexed: int = Field(..., description="Number of chunks that were indexed")
    chunks_skipped: int = Field(..., description="Number of chunks that were skipped (already indexed)")
    embedding_model: str = Field(..., description="Embedding model used")
