"""Static clause library for CLAUSE_REDLINES_V1 workflow.

This module provides a static clause library with:
- Clause type definitions
- Jurisdiction-specific recommended clause text
- Risk triggers (keywords) for clause detection
- Notes for legal context
"""

from src.clause_library.library import (
    CLAUSE_LIBRARY,
    RISK_TRIGGERS,
    ClauseType,
    ClauseTypeEnum,
    JurisdictionEnum,
    get_clause_for_jurisdiction,
    get_clause_types,
    get_risk_triggers,
)

__all__ = [
    "CLAUSE_LIBRARY",
    "ClauseType",
    "ClauseTypeEnum",
    "JurisdictionEnum",
    "RISK_TRIGGERS",
    "get_clause_for_jurisdiction",
    "get_clause_types",
    "get_risk_triggers",
]
