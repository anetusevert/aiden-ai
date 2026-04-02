"""Policy profile schemas for configuration and API requests/responses."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RetrievalConfig(BaseModel):
    """Retrieval configuration stub for future RAG implementation."""

    max_chunks: int = Field(default=12, ge=1, le=100, description="Maximum chunks to retrieve")
    # Future: add retrieval-related settings here


class GenerationConfig(BaseModel):
    """Generation configuration stub for future LLM generation settings."""

    require_citations: bool = Field(default=True, description="Require citations in output")
    # Future: add generation-related settings here


class PolicyConfig(BaseModel):
    """Policy configuration schema - validates the config JSONB field.

    This defines what is allowed within a workspace that references this policy profile.
    All lists are allow-lists (deny by default if not listed).
    """

    allowed_workflows: list[str] = Field(
        default_factory=list,
        description="List of allowed workflow identifiers (e.g., CONTRACT_REVIEW_V1)",
        examples=[["CONTRACT_REVIEW_V1", "LEGAL_RESEARCH_V1"]],
    )
    allowed_input_languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="List of allowed input languages",
        examples=[["en", "ar", "mixed"]],
    )
    allowed_output_languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="List of allowed output languages",
        examples=[["en", "ar"]],
    )
    allowed_jurisdictions: list[str] = Field(
        default_factory=lambda: ["UAE"],
        description="List of allowed jurisdictions",
        examples=[["UAE", "DIFC", "ADGM", "KSA"]],
    )
    feature_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags for enabling/disabling specific features",
        examples=[{"law_firm_mode": False, "advanced_analytics": True}],
    )
    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval configuration (stub)",
    )
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig,
        description="Generation configuration (stub)",
    )

    @field_validator("allowed_workflows", "allowed_input_languages", "allowed_output_languages", "allowed_jurisdictions")
    @classmethod
    def ensure_list_elements_are_strings(cls, v: list[Any]) -> list[str]:
        """Ensure all list elements are strings."""
        if not isinstance(v, list):
            raise ValueError("Must be a list")
        return [str(item) for item in v]


class PolicyProfileCreate(BaseModel):
    """Schema for creating a policy profile."""

    name: str = Field(..., min_length=1, max_length=255, description="Policy profile name")
    description: str | None = Field(None, max_length=1000, description="Policy profile description")
    config: PolicyConfig = Field(..., description="Policy configuration")
    is_default: bool = Field(False, description="Whether this is the default profile for the tenant")


class PolicyProfileUpdate(BaseModel):
    """Schema for updating a policy profile."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Policy profile name")
    description: str | None = Field(None, max_length=1000, description="Policy profile description")
    config: PolicyConfig | None = Field(None, description="Policy configuration")
    is_default: bool | None = Field(None, description="Whether this is the default profile for the tenant")


class PolicyProfileResponse(BaseModel):
    """Schema for policy profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    description: str | None
    config: dict[str, Any]  # Raw JSONB, can be validated as PolicyConfig
    is_default: bool
    created_at: datetime


class AttachPolicyRequest(BaseModel):
    """Schema for attaching a policy profile to a workspace."""

    policy_profile_id: str = Field(..., description="Policy profile ID to attach")


class ResolvedPolicy(BaseModel):
    """Schema for resolved policy returned by the resolver.

    This represents the effective policy for a given request context.
    """

    policy_profile_id: str | None = Field(
        None, description="ID of the resolved policy profile (None if using built-in default)"
    )
    policy_profile_name: str = Field(..., description="Name of the policy profile")
    source: Literal["workspace", "tenant_default", "builtin_default"] = Field(
        ..., description="Where the policy was resolved from"
    )
    config: PolicyConfig = Field(..., description="The effective policy configuration")
    workflow_allowed: bool = Field(True, description="Whether the requested workflow is allowed")
    workflow_denied_reason: str | None = Field(
        None, description="Reason if workflow was denied"
    )


class PolicyResolveResponse(BaseModel):
    """Schema for policy resolve endpoint response."""

    model_config = ConfigDict(from_attributes=True)

    policy_profile_id: str | None
    policy_profile_name: str
    source: str
    config: dict[str, Any]
    workflow_allowed: bool
    workflow_denied_reason: str | None
