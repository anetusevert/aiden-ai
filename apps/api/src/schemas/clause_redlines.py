"""Schemas for Clause Redlines workflow (CLAUSE_REDLINES_V1).

This module defines the request/response models for the clause redlines workflow
which detects clauses in a contract and suggests redlines based on a clause library.

v2 additions:
- confidence_level: "high" | "medium" | "low" for calibrated confidence
- confidence_reason: Human-readable explanation of confidence score
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.workflow_status import WorkflowResultStatus


# Evidence scope options
EvidenceScope = Literal["workspace", "global", "both"]


# Clause type for the workflow
ClauseType = Literal[
    "governing_law",
    "termination",
    "liability",
    "indemnity",
    "confidentiality",
    "payment",
    "ip",
    "force_majeure",
]

# Jurisdiction options
Jurisdiction = Literal["UAE", "DIFC", "ADGM", "KSA"]

# Status of a clause redline item
ClauseStatus = Literal["found", "missing", "insufficient_evidence"]

# Severity levels
Severity = Literal["low", "medium", "high", "critical"]

# Confidence level (v2)
ConfidenceLevel = Literal["high", "medium", "low"]


class EvidenceChunkRef(BaseModel):
    """Reference to a contract chunk used as evidence for a clause detection.

    Supports both workspace documents and global legal corpus with explicit provenance.
    """

    model_config = ConfigDict(from_attributes=True)

    chunk_id: str = Field(..., description="ID of the source chunk")
    snippet: str = Field(..., description="Text snippet from the chunk")
    char_start: int = Field(..., description="Character offset start in document text")
    char_end: int = Field(..., description="Character offset end in document text")

    # Source provenance (required for user trust)
    source_type: Literal["workspace_document", "global_legal"] = Field(
        "workspace_document",
        description="Source type: workspace_document or global_legal",
    )
    source_label: str = Field(
        "",
        description="Human-readable source label",
    )

    # Global legal metadata (optional)
    instrument_id: str | None = Field(None, description="Legal instrument ID (global only)")
    jurisdiction: str | None = Field(None, description="Jurisdiction")
    official_source_url: str | None = Field(None, description="Official source URL (global only)")


class ClauseRedlineItem(BaseModel):
    """A single clause redline result.

    v2 additions:
    - confidence_level: Calibrated confidence ("high", "medium", "low")
    - confidence_reason: Explanation of how confidence was determined
    """

    model_config = ConfigDict(from_attributes=True)

    clause_type: ClauseType = Field(..., description="Type of the clause")
    status: ClauseStatus = Field(
        ..., description="Status: found, missing, or insufficient_evidence"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Detection confidence (0.0 to 1.0)"
    )
    confidence_level: ConfidenceLevel = Field(
        "medium",
        description="Calibrated confidence level: high, medium, or low (v2)",
    )
    confidence_reason: str = Field(
        "",
        description="Human-readable explanation of confidence score (v2)",
    )
    issue: str | None = Field(
        None,
        description="Description of issues found (must contain citations [n] if referencing contract)",
    )
    suggested_redline: str | None = Field(
        None,
        description="Suggested clause text or redline (template text, may be uncited)",
    )
    rationale: str | None = Field(
        None,
        description="Rationale for the suggestion (must cite if referencing contract)",
    )
    citations: list[int] = Field(
        default_factory=list,
        description="List of evidence indices (1-indexed) referenced by this item",
    )
    evidence: list[EvidenceChunkRef] = Field(
        default_factory=list,
        description="Evidence chunk references mapping citations to chunk metadata",
    )
    severity: Severity = Field("medium", description="Severity of the issue")


class ClauseRedlinesMeta(BaseModel):
    """Metadata about the clause redlines response."""

    model_config = ConfigDict(from_attributes=True)

    # Workflow result status (enterprise-ready)
    status: WorkflowResultStatus = Field(
        WorkflowResultStatus.SUCCESS,
        description="Explicit workflow result status for machine-readable outcomes",
    )

    model: str = Field(..., description="LLM model used")
    provider: str = Field(..., description="LLM provider used")
    evidence_chunk_count: int = Field(
        ..., description="Total number of evidence chunks analyzed"
    )
    request_id: str | None = Field(None, description="Request ID for tracing")
    output_language: str = Field(..., description="Output language used")
    jurisdiction: str = Field(..., description="Jurisdiction used for clause templates")
    # Strict citation enforcement fields
    downgraded_count: int = Field(
        0, description="Number of items downgraded due to invalid citations"
    )
    removed_count: int = Field(
        0, description="Number of items removed due to invalid citations"
    )
    strict_citations_failed: bool = Field(
        False,
        description="True if many items failed citation validation",
    )
    validation_warnings: list[str] | None = Field(
        None, description="Any validation warnings"
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


class ClauseRedlinesRequest(BaseModel):
    """Request body for clause redlines endpoint."""

    document_id: str = Field(..., description="ID of the document to analyze")
    version_id: str = Field(..., description="ID of the specific version to analyze")
    jurisdiction: Jurisdiction | None = Field(
        None,
        description="Jurisdiction for clause templates (defaults to document jurisdiction)",
    )
    playbook_hint: str | None = Field(
        None,
        description="Optional hint from a playbook to guide the analysis",
    )
    clause_types: list[ClauseType] | None = Field(
        None,
        description="Optional list of clause types to analyze (defaults to all)",
    )
    output_language: Literal["en", "ar"] = Field(
        "en",
        description="Language for the output",
    )
    evidence_scope: EvidenceScope = Field(
        "workspace",
        description="Evidence retrieval scope: workspace (default), global, or both",
    )


class ClauseRedlinesResponse(BaseModel):
    """Response from clause redlines endpoint."""

    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(
        ..., description="Executive summary (claims about contract must be cited)"
    )
    items: list[ClauseRedlineItem] = Field(
        ..., description="List of clause redline results"
    )
    meta: ClauseRedlinesMeta = Field(..., description="Response metadata")
    insufficient_sources: bool = Field(
        False,
        description="True if there were not enough sources to analyze confidently",
    )
