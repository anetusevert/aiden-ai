"""Shared workflow status definitions for enterprise readiness.

This module defines the WorkflowResultStatus enum used across all workflow responses.
It provides deterministic, machine-readable status values for enterprise integrations.
"""

from enum import Enum


class WorkflowResultStatus(str, Enum):
    """Explicit status for workflow execution outcomes.

    Status values (in order of precedence):
    - success: Workflow completed successfully with valid output
    - insufficient_sources: Not enough evidence/sources to produce confident output
    - policy_denied: Request blocked by policy enforcement (HTTP 403)
    - citation_violation: Output reduced/failed due to strict citation enforcement
    - validation_failed: LLM returned invalid JSON or parse failed
    - generation_failed: LLM provider error or other generation failure
    """

    SUCCESS = "success"
    INSUFFICIENT_SOURCES = "insufficient_sources"
    POLICY_DENIED = "policy_denied"
    CITATION_VIOLATION = "citation_violation"
    VALIDATION_FAILED = "validation_failed"
    GENERATION_FAILED = "generation_failed"
