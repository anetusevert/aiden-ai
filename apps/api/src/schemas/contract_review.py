"""Schemas for Contract Review workflow (CONTRACT_REVIEW_V1).

This module defines the request/response models for the contract review workflow
which analyzes a specific contract document and produces structured findings.
"""

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.workflow_status import WorkflowResultStatus


# Evidence scope options
EvidenceScope = Literal["workspace", "global", "both"]


# Focus area categories for contract review
FocusArea = Literal[
    "liability",
    "termination",
    "governing_law",
    "payment",
    "ip",
    "confidentiality",
    "other",
]

# Severity levels for findings
Severity = Literal["low", "medium", "high", "critical"]

# Review depth modes
ReviewMode = Literal["quick", "standard", "deep"]


class EvidenceChunkRef(BaseModel):
    """Reference to a contract chunk used as evidence for a finding.

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


class Finding(BaseModel):
    """A single finding from the contract review."""

    model_config = ConfigDict(from_attributes=True)

    finding_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this finding",
    )
    title: str = Field(..., description="Brief title of the finding")
    severity: Severity = Field(..., description="Severity level of the finding")
    category: FocusArea = Field(..., description="Category of the finding")
    issue: str = Field(
        ..., description="Description of the issue (must contain citations like [1])"
    )
    recommendation: str = Field(
        ..., description="Recommendation to address the issue (must contain citations)"
    )
    citations: list[int] = Field(
        ..., description="List of evidence indices (1-indexed) referenced by this finding"
    )
    evidence: list[EvidenceChunkRef] = Field(
        default_factory=list,
        description="Evidence chunk references mapping citations to chunk metadata",
    )


class ContractReviewRequest(BaseModel):
    """Request body for contract review endpoint."""

    document_id: str = Field(..., description="ID of the document to review")
    version_id: str = Field(..., description="ID of the specific version to review")
    review_mode: ReviewMode = Field(
        "standard",
        description="Review depth: quick (20 chunks), standard (40 chunks), deep (80 chunks)",
    )
    focus_areas: list[FocusArea] | None = Field(
        None,
        description="Optional focus areas to prioritize in the review",
    )
    output_language: Literal["en", "ar"] = Field(
        "en",
        description="Language for the review output",
    )
    playbook_hint: str | None = Field(
        None,
        description="Optional hint from a playbook to guide the review focus (prepended to prompt)",
    )
    evidence_scope: EvidenceScope = Field(
        "workspace",
        description="Evidence retrieval scope: workspace (default), global, or both",
    )


class ContractReviewMeta(BaseModel):
    """Metadata about the contract review response."""

    model_config = ConfigDict(from_attributes=True)

    # Workflow result status (enterprise-ready)
    status: WorkflowResultStatus = Field(
        WorkflowResultStatus.SUCCESS,
        description="Explicit workflow result status for machine-readable outcomes",
    )

    model: str = Field(..., description="LLM model used")
    provider: str = Field(..., description="LLM provider used")
    evidence_chunk_count: int = Field(
        ..., description="Number of evidence chunks selected for review"
    )
    request_id: str | None = Field(None, description="Request ID for tracing")
    output_language: str = Field(..., description="Output language used")
    review_mode: str = Field(..., description="Review mode used")
    # Strict citation enforcement fields
    removed_findings_count: int = Field(
        0, description="Number of findings removed due to invalid citations"
    )
    strict_citations_failed: bool = Field(
        False,
        description="True if response was downgraded due to all findings having invalid citations",
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


class ContractReviewResponse(BaseModel):
    """Response from contract review endpoint."""

    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(
        ..., description="Executive summary of the review (must contain citations)"
    )
    findings: list[Finding] = Field(
        ..., description="List of findings from the review"
    )
    meta: ContractReviewMeta = Field(..., description="Response metadata")
    insufficient_sources: bool = Field(
        False,
        description="True if there were not enough sources to review confidently",
    )
