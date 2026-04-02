"""Schemas for Legal Research workflow."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.workflow_status import WorkflowResultStatus


# Evidence scope options
EvidenceScope = Literal["workspace", "global", "both"]


class ResearchFilters(BaseModel):
    """Filters for the research query."""

    document_type: str | None = Field(
        None,
        description="Filter by document type (contract, policy, memo, regulatory, other)",
    )
    jurisdiction: str | None = Field(
        None,
        description="Filter by jurisdiction (UAE, DIFC, ADGM, KSA)",
    )
    language: str | None = Field(
        None,
        description="Filter by language (en, ar, mixed)",
    )


class LegalResearchRequest(BaseModel):
    """Request body for legal research endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The legal question to research",
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of evidence chunks to retrieve",
    )
    filters: ResearchFilters | None = Field(
        None,
        description="Optional filters for document retrieval",
    )
    output_language: Literal["en", "ar"] = Field(
        "en",
        description="Language for the answer output",
    )
    evidence_scope: EvidenceScope = Field(
        "workspace",
        description="Evidence retrieval scope: workspace (default), global, or both",
    )


class CitationReference(BaseModel):
    """A citation reference mapping [n] to source details."""

    model_config = ConfigDict(from_attributes=True)

    citation_index: int = Field(
        ..., description="Citation number (1-indexed, corresponds to [1], [2], etc.)"
    )
    chunk_id: str = Field(..., description="ID of the source chunk")
    document_id: str = Field(..., description="ID of the source document")
    version_id: str = Field(..., description="ID of the document version")
    document_title: str = Field(..., description="Title of the source document")
    char_start: int = Field(..., description="Character offset start in document text")
    char_end: int = Field(..., description="Character offset end in document text")
    page_start: int | None = Field(None, description="Start page (if available)")
    page_end: int | None = Field(None, description="End page (if available)")


class EvidenceChunk(BaseModel):
    """An evidence chunk returned from retrieval.

    Supports both workspace documents and global legal corpus with explicit provenance.
    """

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="Unique identifier of the chunk")
    chunk_index: int = Field(
        ..., description="Index of chunk within the document version"
    )
    snippet: str = Field(..., description="Chunk text content")

    # Source provenance (required for user trust)
    source_type: Literal["workspace_document", "global_legal"] = Field(
        "workspace_document",
        description="Source type: workspace_document or global_legal",
    )
    source_label: str = Field(
        "",
        description="Human-readable source label (e.g., 'Saudi Companies Law (2022)')",
    )

    # Document metadata (workspace documents)
    document_id: str | None = Field(None, description="Document ID (workspace only)")
    version_id: str | None = Field(None, description="Version ID")
    document_title: str | None = Field(None, description="Document title (workspace only)")
    document_type: str | None = Field(None, description="Document type (workspace only)")

    # Instrument metadata (global legal)
    instrument_id: str | None = Field(None, description="Legal instrument ID (global only)")
    instrument_title: str | None = Field(None, description="Instrument title (global only)")
    instrument_title_ar: str | None = Field(None, description="Instrument title in Arabic (global only)")
    instrument_type: str | None = Field(None, description="Instrument type (global only)")

    # Common metadata
    jurisdiction: str | None = Field(None, description="Jurisdiction")
    language: str | None = Field(None, description="Language")
    char_start: int = Field(0, description="Character offset start")
    char_end: int = Field(0, description="Character offset end")
    page_start: int | None = Field(None, description="Start page")
    page_end: int | None = Field(None, description="End page")
    final_score: float = Field(0.0, description="Relevance score")

    # Legal provenance (global legal)
    published_at: str | None = Field(None, description="Publication date (global only)")
    effective_at: str | None = Field(None, description="Effective date (global only)")
    official_source_url: str | None = Field(None, description="Official source URL (global only)")


class ResearchMeta(BaseModel):
    """Metadata about the research response."""

    model_config = ConfigDict(from_attributes=True)

    # Workflow result status (enterprise-ready)
    status: WorkflowResultStatus = Field(
        WorkflowResultStatus.SUCCESS,
        description="Explicit workflow result status for machine-readable outcomes",
    )

    model: str = Field(..., description="LLM model used")
    provider: str = Field(..., description="LLM provider used")
    chunk_count: int = Field(..., description="Number of evidence chunks retrieved")
    request_id: str | None = Field(None, description="Request ID for tracing")
    output_language: str = Field(..., description="Output language used")
    validation_warnings: list[str] | None = Field(
        None, description="Any validation warnings (e.g., invalid citations stripped)"
    )
    # Strict citation enforcement fields
    strict_citation_enforced: bool = Field(
        True, description="Whether strict citation enforcement was applied"
    )
    removed_paragraph_count: int = Field(
        0, description="Number of paragraphs removed due to missing citations"
    )
    strict_citations_failed: bool = Field(
        False,
        description="True if answer was downgraded to insufficient due to strict citation rules",
    )
    citation_count_used: int = Field(
        0, description="Number of unique citations used in the final answer"
    )

    # Prompt/model fingerprinting (enterprise traceability)
    prompt_hash: str | None = Field(
        None, description="SHA256 hash of the final prompt sent to LLM (for traceability)"
    )
    llm_provider: str | None = Field(
        None, description="LLM provider identifier for fingerprinting"
    )
    llm_model: str | None = Field(
        None, description="LLM model identifier for fingerprinting"
    )

    # Evidence scope and counts (unified retrieval)
    evidence_scope: EvidenceScope = Field(
        "workspace",
        description="Evidence retrieval scope used",
    )
    workspace_evidence_count: int = Field(
        0, description="Number of evidence chunks from workspace documents"
    )
    global_evidence_count: int = Field(
        0, description="Number of evidence chunks from global legal corpus"
    )

    # Policy metadata
    policy_jurisdictions_count: int = Field(
        0, description="Number of jurisdictions allowed by policy"
    )
    policy_languages_count: int = Field(
        0, description="Number of languages allowed by policy"
    )
    policy_denied_reason: str | None = Field(
        None, description="Reason if global search was denied by policy"
    )


class LegalResearchResponse(BaseModel):
    """Response from legal research endpoint."""

    model_config = ConfigDict(from_attributes=True)

    answer_text: str = Field(..., description="The generated answer with inline citations")
    citations: list[CitationReference] = Field(
        ..., description="List of citation references mapping [n] to source details"
    )
    evidence: list[EvidenceChunk] = Field(
        ..., description="Evidence chunks used for the answer"
    )
    meta: ResearchMeta = Field(..., description="Response metadata")
    insufficient_sources: bool = Field(
        False,
        description="True if there were not enough sources to answer confidently",
    )
