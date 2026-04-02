"""Schemas for Global Legal Corpus API requests and responses."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Enums
# =============================================================================


class Jurisdiction(str, Enum):
    """GCC jurisdictions for legal instruments."""

    UAE = "UAE"
    DIFC = "DIFC"
    ADGM = "ADGM"
    KSA = "KSA"
    OMAN = "OMAN"
    BAHRAIN = "BAHRAIN"
    QATAR = "QATAR"
    KUWAIT = "KUWAIT"


class InstrumentType(str, Enum):
    """Types of legal instruments."""

    LAW = "law"
    FEDERAL_LAW = "federal_law"
    LOCAL_LAW = "local_law"
    DECREE = "decree"
    ROYAL_DECREE = "royal_decree"
    REGULATION = "regulation"
    MINISTERIAL_RESOLUTION = "ministerial_resolution"
    CIRCULAR = "circular"
    GUIDELINE = "guideline"
    DIRECTIVE = "directive"
    ORDER = "order"
    OTHER = "other"


class InstrumentStatus(str, Enum):
    """Status of legal instruments."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REPEALED = "repealed"
    DRAFT = "draft"


class Language(str, Enum):
    """Language of legal instrument version."""

    EN = "en"
    AR = "ar"
    MIXED = "mixed"


# =============================================================================
# Request Schemas
# =============================================================================


class LegalInstrumentCreate(BaseModel):
    """Request to create a legal instrument."""

    jurisdiction: Jurisdiction = Field(..., description="GCC jurisdiction")
    instrument_type: InstrumentType = Field(..., description="Type of legal instrument")
    title: str = Field(..., min_length=1, max_length=1000, description="Official title in English")
    title_ar: str | None = Field(None, max_length=1000, description="Official title in Arabic (optional)")
    official_source_url: str | None = Field(None, max_length=2000, description="URL to official source")
    published_at: date | None = Field(None, description="Date of publication")
    effective_at: date | None = Field(None, description="Effective date")
    status: InstrumentStatus = Field(InstrumentStatus.ACTIVE, description="Status of the instrument")


class LegalInstrumentUpdate(BaseModel):
    """Request to update a legal instrument."""

    title: str | None = Field(None, min_length=1, max_length=1000)
    title_ar: str | None = Field(None, max_length=1000)
    official_source_url: str | None = Field(None, max_length=2000)
    published_at: date | None = None
    effective_at: date | None = None
    status: InstrumentStatus | None = None


class LegalVersionCreate(BaseModel):
    """Metadata for creating a legal instrument version (file sent separately)."""

    version_label: str = Field(..., min_length=1, max_length=64, description="Version label (e.g., 'v1.0', '2024-amendment')")
    language: Language = Field(..., description="Language of the document")


# =============================================================================
# Response Schemas
# =============================================================================


class LegalVersionSummary(BaseModel):
    """Summary of a legal instrument version."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version_label: str
    file_name: str
    content_type: str
    size_bytes: int
    language: str
    is_indexed: bool
    indexed_at: datetime | None
    embedding_model: str | None
    created_at: datetime
    uploaded_by_user_id: str | None


class LegalInstrumentResponse(BaseModel):
    """Response for a legal instrument."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    jurisdiction: str
    instrument_type: str
    title: str
    title_ar: str | None
    official_source_url: str | None
    published_at: date | None
    effective_at: date | None
    status: str
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None


class LegalInstrumentWithVersions(LegalInstrumentResponse):
    """Legal instrument with all versions."""

    versions: list[LegalVersionSummary] = Field(default_factory=list)


class LegalInstrumentWithLatestVersion(LegalInstrumentResponse):
    """Legal instrument with latest version info."""

    latest_version: LegalVersionSummary | None = None


class LegalInstrumentListResponse(BaseModel):
    """Response for listing legal instruments."""

    model_config = ConfigDict(from_attributes=True)

    items: list[LegalInstrumentWithLatestVersion]
    total: int
    limit: int
    offset: int


class LegalInstrumentCreateResponse(BaseModel):
    """Response for creating a legal instrument."""

    model_config = ConfigDict(from_attributes=True)

    instrument: LegalInstrumentResponse
    version: LegalVersionSummary | None = None


class LegalVersionCreateResponse(BaseModel):
    """Response for creating a legal instrument version."""

    model_config = ConfigDict(from_attributes=True)

    version: LegalVersionSummary
    instrument_id: str


class ReindexLegalVersionResponse(BaseModel):
    """Response for reindexing a legal instrument version."""

    model_config = ConfigDict(from_attributes=True)

    instrument_id: str
    version_id: str
    chunks_indexed: int
    chunks_skipped: int
    embedding_model: str


# =============================================================================
# Search Schemas
# =============================================================================


class GlobalLegalSearchRequest(BaseModel):
    """Request for searching global legal corpus."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")
    jurisdiction: Jurisdiction | None = Field(None, description="Filter by jurisdiction")
    instrument_type: InstrumentType | None = Field(None, description="Filter by instrument type")
    language: Language | None = Field(None, description="Filter by language")


class SourceType(str, Enum):
    """Source types for evidence/search results."""

    WORKSPACE_DOCUMENT = "workspace_document"
    GLOBAL_LEGAL = "global_legal"


class GlobalLegalChunkResult(BaseModel):
    """A single search result from the global legal corpus.

    This schema provides clear provenance for user trust:
    - source_type: Always "global_legal" for global law corpus
    - source_label: Human-readable source description (e.g., "Saudi Companies Law (2022)")
    - All global legal results include jurisdiction, instrument dates, and official source URL
    """

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="Unique identifier of the chunk")
    chunk_index: int = Field(..., description="Index of chunk within the version")
    snippet: str = Field(..., description="Truncated chunk text (max 300 chars)")

    # Instrument metadata
    instrument_id: str = Field(..., description="Legal instrument ID")
    version_id: str = Field(..., description="Version ID")
    instrument_title: str = Field(..., description="Instrument title")
    instrument_title_ar: str | None = Field(None, description="Instrument title in Arabic")
    instrument_type: str = Field(..., description="Type of legal instrument")
    jurisdiction: str = Field(..., description="Jurisdiction (required for global legal)")
    language: str = Field(..., description="Language of the version")

    # Dates (critical for legal provenance)
    published_at: date | None = Field(None, description="Publication date")
    effective_at: date | None = Field(None, description="Effective date")

    # Official source (required for global legal for trust)
    official_source_url: str | None = Field(None, description="URL to official source")

    # Offsets for citation
    char_start: int = Field(..., description="Character offset start")
    char_end: int = Field(..., description="Character offset end")
    page_start: int | None = Field(None, description="Start page number (if available)")
    page_end: int | None = Field(None, description="End page number (if available)")

    # Scores
    vector_score: float = Field(..., description="Normalized vector similarity score (0-1)")
    keyword_score: float = Field(..., description="Normalized keyword match score (0-1)")
    final_score: float = Field(..., description="Combined final score (0-1)")

    # =========================================================================
    # Source Provenance Fields (User Trust / Transparency)
    # =========================================================================

    source_type: str = Field(
        default="global_legal",
        description="Source type: 'global_legal' for global law corpus, 'workspace_document' for workspace docs"
    )
    source_label: str = Field(
        ...,
        description="Human-readable source label (e.g., 'Saudi Companies Law (2022)')"
    )

    @field_validator("source_label", mode="before")
    @classmethod
    def generate_source_label(cls, v, info):
        """Generate source_label from instrument title and date if not provided."""
        if v is not None:
            return v
        # Will be set by the service layer
        return ""


class GlobalLegalSearchResponse(BaseModel):
    """Response for global legal corpus search."""

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(..., description="The search query")
    total: int = Field(..., description="Total number of results returned")
    results: list[GlobalLegalChunkResult] = Field(..., description="Search results ordered by relevance")


# =============================================================================
# Read-Only Viewer Schemas (User-Facing)
# =============================================================================


class LegalChunkPreview(BaseModel):
    """Preview of a legal chunk for the viewer sidebar."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Chunk ID")
    chunk_index: int = Field(..., description="Index of chunk within the version")
    preview: str = Field(..., description="First 150 characters of chunk text")
    page_start: int | None = Field(None, description="Start page number")


class LegalChunkDetail(BaseModel):
    """Full chunk detail for the viewer main pane."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Chunk ID")
    chunk_index: int = Field(..., description="Index of chunk within the version")
    text: str = Field(..., description="Full chunk text")
    char_start: int = Field(..., description="Character offset start")
    char_end: int = Field(..., description="Character offset end")
    page_start: int | None = Field(None, description="Start page number")
    page_end: int | None = Field(None, description="End page number")


class LegalChunkWithContext(BaseModel):
    """Chunk with neighbor context for viewer navigation."""

    model_config = ConfigDict(from_attributes=True)

    chunk: LegalChunkDetail = Field(..., description="The selected chunk")
    prev_chunk: LegalChunkPreview | None = Field(None, description="Previous chunk preview")
    next_chunk: LegalChunkPreview | None = Field(None, description="Next chunk preview")


class ViewerVersionSummary(BaseModel):
    """Version summary for the viewer."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version_label: str
    language: str
    is_indexed: bool
    created_at: datetime


class ViewerInstrumentListItem(BaseModel):
    """Legal instrument item for the viewer index page."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    title_ar: str | None = None
    jurisdiction: str
    instrument_type: str
    status: str
    published_at: date | None = None
    effective_at: date | None = None
    official_source_url: str | None = None
    latest_version_date: datetime | None = Field(None, description="Date of the latest version")


class ViewerInstrumentListResponse(BaseModel):
    """Response for listing instruments in the viewer."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ViewerInstrumentListItem]
    total: int
    limit: int
    offset: int


class ViewerInstrumentDetail(BaseModel):
    """Full instrument detail for the viewer instrument page."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    title_ar: str | None = None
    jurisdiction: str
    instrument_type: str
    status: str
    published_at: date | None = None
    effective_at: date | None = None
    official_source_url: str | None = None
    created_at: datetime
    versions: list[ViewerVersionSummary] = Field(default_factory=list, description="All versions, ordered desc by created_at")


class ViewerVersionDetail(BaseModel):
    """Version detail for the viewer version page."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version_label: str
    language: str
    is_indexed: bool
    indexed_at: datetime | None = None
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime
    # Instrument context
    instrument_id: str
    instrument_title: str
    instrument_title_ar: str | None = None
    jurisdiction: str
    instrument_type: str
    official_source_url: str | None = None
    published_at: date | None = None
    effective_at: date | None = None


class ViewerChunksResponse(BaseModel):
    """Response for listing chunks in the viewer."""

    model_config = ConfigDict(from_attributes=True)

    version_id: str
    instrument_id: str
    chunk_count: int
    chunks: list[LegalChunkPreview]
