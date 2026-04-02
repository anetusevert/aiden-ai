"""Static clause library with jurisdiction-specific clause templates.

This module defines a small library of clause types with:
- Recommended clause text per jurisdiction
- Risk triggers (keywords) for detection
- Notes for context

Jurisdictions supported:
- UAE: United Arab Emirates (Federal)
- DIFC: Dubai International Financial Centre
- ADGM: Abu Dhabi Global Market
- KSA: Kingdom of Saudi Arabia
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class ClauseTypeEnum(str, Enum):
    """Enumeration of supported clause types."""

    GOVERNING_LAW = "governing_law"
    TERMINATION = "termination"
    LIABILITY = "liability"
    INDEMNITY = "indemnity"
    CONFIDENTIALITY = "confidentiality"
    PAYMENT = "payment"
    IP = "ip"
    FORCE_MAJEURE = "force_majeure"


class JurisdictionEnum(str, Enum):
    """Enumeration of supported jurisdictions."""

    UAE = "UAE"
    DIFC = "DIFC"
    ADGM = "ADGM"
    KSA = "KSA"


# Type aliases for clarity
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

Jurisdiction = Literal["UAE", "DIFC", "ADGM", "KSA"]


@dataclass
class ClauseTemplate:
    """A clause template for a specific jurisdiction."""

    clause_type: ClauseType
    jurisdiction: Jurisdiction
    recommended_clause_text: str
    notes: str
    risk_triggers: list[str]


# =============================================================================
# Risk Triggers per Clause Type (used for detection)
# =============================================================================

RISK_TRIGGERS: dict[ClauseType, list[str]] = {
    "governing_law": [
        "governing law",
        "governed by",
        "applicable law",
        "jurisdiction",
        "courts of",
        "laws of",
        "subject to the laws",
        "legal framework",
        "dispute resolution",
    ],
    "termination": [
        "termination",
        "terminate",
        "terminates",
        "notice period",
        "days notice",
        "upon notice",
        "breach",
        "material breach",
        "right to terminate",
        "effective date of termination",
        "termination for cause",
        "termination for convenience",
    ],
    "liability": [
        "liability",
        "liable",
        "liabilities",
        "limitation of liability",
        "limited to",
        "cap on liability",
        "maximum liability",
        "aggregate liability",
        "shall not exceed",
        "consequential damages",
        "direct damages",
        "indirect damages",
    ],
    "indemnity": [
        "indemnify",
        "indemnification",
        "indemnities",
        "hold harmless",
        "defend and indemnify",
        "indemnifying party",
        "indemnified party",
        "third party claims",
        "losses and damages",
    ],
    "confidentiality": [
        "confidential",
        "confidentiality",
        "confidential information",
        "non-disclosure",
        "nda",
        "proprietary information",
        "trade secrets",
        "disclose",
        "disclosure",
        "keep confidential",
    ],
    "payment": [
        "payment",
        "pay",
        "payable",
        "invoice",
        "net 30",
        "net 60",
        "payment terms",
        "late payment",
        "interest on",
        "fees",
        "compensation",
        "remuneration",
    ],
    "ip": [
        "intellectual property",
        "ip rights",
        "copyright",
        "patent",
        "trademark",
        "trade mark",
        "ownership of",
        "license",
        "licensing",
        "work product",
        "deliverables",
        "background ip",
        "foreground ip",
    ],
    "force_majeure": [
        "force majeure",
        "act of god",
        "beyond reasonable control",
        "unforeseeable",
        "natural disaster",
        "pandemic",
        "epidemic",
        "war",
        "terrorism",
        "government action",
        "impossibility",
    ],
}


# =============================================================================
# Clause Library: Recommended Text per Jurisdiction
# =============================================================================

CLAUSE_LIBRARY: list[ClauseTemplate] = [
    # =========================================================================
    # GOVERNING LAW
    # =========================================================================
    ClauseTemplate(
        clause_type="governing_law",
        jurisdiction="UAE",
        recommended_clause_text=(
            "This Agreement shall be governed by and construed in accordance with the "
            "laws of the United Arab Emirates. Any dispute arising out of or in "
            "connection with this Agreement shall be referred to and finally resolved "
            "by the courts of Dubai, United Arab Emirates."
        ),
        notes="UAE Federal law applies. Consider arbitration for commercial disputes.",
        risk_triggers=RISK_TRIGGERS["governing_law"],
    ),
    ClauseTemplate(
        clause_type="governing_law",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "This Agreement shall be governed by and construed in accordance with the "
            "laws of the Dubai International Financial Centre. Any dispute arising out "
            "of or in connection with this Agreement shall be subject to the exclusive "
            "jurisdiction of the DIFC Courts."
        ),
        notes="DIFC has its own common law legal system separate from UAE Federal law.",
        risk_triggers=RISK_TRIGGERS["governing_law"],
    ),
    ClauseTemplate(
        clause_type="governing_law",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "This Agreement shall be governed by and construed in accordance with the "
            "laws of the Abu Dhabi Global Market. Any dispute arising out of or in "
            "connection with this Agreement shall be subject to the exclusive "
            "jurisdiction of the ADGM Courts."
        ),
        notes="ADGM applies English common law principles. ADGM Courts apply English law.",
        risk_triggers=RISK_TRIGGERS["governing_law"],
    ),
    ClauseTemplate(
        clause_type="governing_law",
        jurisdiction="KSA",
        recommended_clause_text=(
            "This Agreement shall be governed by and construed in accordance with the "
            "laws of the Kingdom of Saudi Arabia, including Sharia law principles. "
            "Any dispute arising out of or in connection with this Agreement shall be "
            "referred to the competent courts in the Kingdom of Saudi Arabia."
        ),
        notes="Saudi law is based on Sharia. Interest provisions require careful drafting.",
        risk_triggers=RISK_TRIGGERS["governing_law"],
    ),
    # =========================================================================
    # TERMINATION
    # =========================================================================
    ClauseTemplate(
        clause_type="termination",
        jurisdiction="UAE",
        recommended_clause_text=(
            "Either Party may terminate this Agreement: (a) for convenience upon "
            "thirty (30) days' prior written notice to the other Party; or (b) "
            "immediately upon written notice if the other Party commits a material "
            "breach of this Agreement and fails to remedy such breach within fifteen "
            "(15) days of receiving written notice specifying the breach."
        ),
        notes="UAE law may impose mandatory notice periods for certain contract types.",
        risk_triggers=RISK_TRIGGERS["termination"],
    ),
    ClauseTemplate(
        clause_type="termination",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "Either Party may terminate this Agreement: (a) for convenience upon "
            "thirty (30) days' prior written notice to the other Party; or (b) "
            "immediately upon written notice if the other Party commits a material "
            "breach of this Agreement and fails to remedy such breach within fourteen "
            "(14) days of receiving written notice specifying the breach."
        ),
        notes="DIFC follows common law principles. Ensure clear breach definitions.",
        risk_triggers=RISK_TRIGGERS["termination"],
    ),
    ClauseTemplate(
        clause_type="termination",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "Either Party may terminate this Agreement: (a) for convenience upon "
            "thirty (30) days' prior written notice to the other Party; or (b) "
            "immediately upon written notice if the other Party commits a material "
            "breach of this Agreement and fails to remedy such breach within fourteen "
            "(14) days of receiving written notice specifying the breach."
        ),
        notes="ADGM applies English common law. Include cure periods for breaches.",
        risk_triggers=RISK_TRIGGERS["termination"],
    ),
    ClauseTemplate(
        clause_type="termination",
        jurisdiction="KSA",
        recommended_clause_text=(
            "Either Party may terminate this Agreement: (a) for convenience upon "
            "sixty (60) days' prior written notice to the other Party; or (b) "
            "immediately upon written notice if the other Party commits a material "
            "breach of this Agreement and fails to remedy such breach within thirty "
            "(30) days of receiving written notice specifying the breach."
        ),
        notes="KSA courts may require longer notice periods. Agency laws apply special rules.",
        risk_triggers=RISK_TRIGGERS["termination"],
    ),
    # =========================================================================
    # LIABILITY
    # =========================================================================
    ClauseTemplate(
        clause_type="liability",
        jurisdiction="UAE",
        recommended_clause_text=(
            "Neither Party shall be liable to the other for any indirect, incidental, "
            "special, consequential, or punitive damages. Each Party's total aggregate "
            "liability under this Agreement shall not exceed the total fees paid or "
            "payable under this Agreement in the twelve (12) months preceding the claim."
        ),
        notes="UAE courts may not enforce caps on liability in all cases. Review case law.",
        risk_triggers=RISK_TRIGGERS["liability"],
    ),
    ClauseTemplate(
        clause_type="liability",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "Neither Party shall be liable to the other for any indirect, incidental, "
            "special, consequential, or punitive damages. Each Party's total aggregate "
            "liability under this Agreement shall not exceed the total fees paid or "
            "payable under this Agreement in the twelve (12) months preceding the claim. "
            "Nothing in this clause shall limit liability for fraud, death, or personal injury."
        ),
        notes="DIFC follows English law. Liability caps are generally enforceable.",
        risk_triggers=RISK_TRIGGERS["liability"],
    ),
    ClauseTemplate(
        clause_type="liability",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "Neither Party shall be liable to the other for any indirect, incidental, "
            "special, consequential, or punitive damages. Each Party's total aggregate "
            "liability under this Agreement shall not exceed the total fees paid or "
            "payable under this Agreement in the twelve (12) months preceding the claim. "
            "Nothing in this clause shall limit liability for fraud, death, or personal injury."
        ),
        notes="ADGM applies English law. Include carve-outs for non-excludable liabilities.",
        risk_triggers=RISK_TRIGGERS["liability"],
    ),
    ClauseTemplate(
        clause_type="liability",
        jurisdiction="KSA",
        recommended_clause_text=(
            "Neither Party shall be liable to the other for any indirect, incidental, "
            "special, consequential, or punitive damages to the extent permitted by law. "
            "Each Party's total aggregate liability under this Agreement shall not exceed "
            "the total fees paid or payable under this Agreement."
        ),
        notes="Saudi courts may not enforce all liability limitations. Review carefully.",
        risk_triggers=RISK_TRIGGERS["liability"],
    ),
    # =========================================================================
    # INDEMNITY
    # =========================================================================
    ClauseTemplate(
        clause_type="indemnity",
        jurisdiction="UAE",
        recommended_clause_text=(
            "Each Party (the 'Indemnifying Party') shall indemnify, defend, and hold "
            "harmless the other Party (the 'Indemnified Party') from and against any "
            "and all claims, damages, losses, liabilities, costs, and expenses "
            "(including reasonable legal fees) arising out of or in connection with: "
            "(a) any breach of this Agreement by the Indemnifying Party; or "
            "(b) any negligent or wrongful act or omission of the Indemnifying Party."
        ),
        notes="UAE law recognizes indemnification. Ensure clear triggers and scope.",
        risk_triggers=RISK_TRIGGERS["indemnity"],
    ),
    ClauseTemplate(
        clause_type="indemnity",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "Each Party (the 'Indemnifying Party') shall indemnify, defend, and hold "
            "harmless the other Party (the 'Indemnified Party') from and against any "
            "and all claims, damages, losses, liabilities, costs, and expenses "
            "(including reasonable legal fees) arising out of or in connection with: "
            "(a) any breach of this Agreement by the Indemnifying Party; "
            "(b) any negligent or wrongful act or omission of the Indemnifying Party; or "
            "(c) any third-party intellectual property infringement claims."
        ),
        notes="DIFC follows English law indemnity principles. Include IP indemnities.",
        risk_triggers=RISK_TRIGGERS["indemnity"],
    ),
    ClauseTemplate(
        clause_type="indemnity",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "Each Party (the 'Indemnifying Party') shall indemnify, defend, and hold "
            "harmless the other Party (the 'Indemnified Party') from and against any "
            "and all claims, damages, losses, liabilities, costs, and expenses "
            "(including reasonable legal fees) arising out of or in connection with: "
            "(a) any breach of this Agreement by the Indemnifying Party; "
            "(b) any negligent or wrongful act or omission of the Indemnifying Party; or "
            "(c) any third-party intellectual property infringement claims."
        ),
        notes="ADGM applies English law. Indemnities are broadly enforceable.",
        risk_triggers=RISK_TRIGGERS["indemnity"],
    ),
    ClauseTemplate(
        clause_type="indemnity",
        jurisdiction="KSA",
        recommended_clause_text=(
            "Each Party (the 'Indemnifying Party') shall indemnify and hold harmless "
            "the other Party (the 'Indemnified Party') from and against any and all "
            "claims, damages, losses, liabilities, costs, and expenses arising out of "
            "or in connection with any breach of this Agreement by the Indemnifying Party "
            "or any negligent act or omission of the Indemnifying Party."
        ),
        notes="KSA courts may limit indemnity scope. Avoid overly broad language.",
        risk_triggers=RISK_TRIGGERS["indemnity"],
    ),
    # =========================================================================
    # CONFIDENTIALITY
    # =========================================================================
    ClauseTemplate(
        clause_type="confidentiality",
        jurisdiction="UAE",
        recommended_clause_text=(
            "Each Party agrees to keep confidential all Confidential Information "
            "disclosed by the other Party and shall not disclose such information to "
            "any third party without the prior written consent of the disclosing Party. "
            "Confidential Information does not include information that: (a) is or becomes "
            "publicly available; (b) was known prior to disclosure; (c) is independently "
            "developed; or (d) is lawfully obtained from a third party."
        ),
        notes="UAE law protects trade secrets. Define Confidential Information clearly.",
        risk_triggers=RISK_TRIGGERS["confidentiality"],
    ),
    ClauseTemplate(
        clause_type="confidentiality",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "Each Party agrees to keep confidential all Confidential Information "
            "disclosed by the other Party and shall not disclose such information to "
            "any third party without the prior written consent of the disclosing Party. "
            "Confidential Information does not include information that: (a) is or becomes "
            "publicly available through no fault of the receiving party; (b) was known "
            "prior to disclosure; (c) is independently developed without reference to "
            "Confidential Information; or (d) is lawfully obtained from a third party. "
            "This obligation shall survive termination for a period of five (5) years."
        ),
        notes="DIFC follows English law. Include survival period and clear exceptions.",
        risk_triggers=RISK_TRIGGERS["confidentiality"],
    ),
    ClauseTemplate(
        clause_type="confidentiality",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "Each Party agrees to keep confidential all Confidential Information "
            "disclosed by the other Party and shall not disclose such information to "
            "any third party without the prior written consent of the disclosing Party. "
            "Confidential Information does not include information that: (a) is or becomes "
            "publicly available through no fault of the receiving party; (b) was known "
            "prior to disclosure; (c) is independently developed without reference to "
            "Confidential Information; or (d) is lawfully obtained from a third party. "
            "This obligation shall survive termination for a period of five (5) years."
        ),
        notes="ADGM applies English law. Standard English-style confidentiality applies.",
        risk_triggers=RISK_TRIGGERS["confidentiality"],
    ),
    ClauseTemplate(
        clause_type="confidentiality",
        jurisdiction="KSA",
        recommended_clause_text=(
            "Each Party agrees to keep confidential all Confidential Information "
            "disclosed by the other Party and shall not disclose such information to "
            "any third party without the prior written consent of the disclosing Party. "
            "Confidential Information does not include information that: (a) is or becomes "
            "publicly available; (b) was known prior to disclosure; (c) is independently "
            "developed; or (d) is lawfully obtained from a third party."
        ),
        notes="KSA protects confidential information. Define scope carefully.",
        risk_triggers=RISK_TRIGGERS["confidentiality"],
    ),
    # =========================================================================
    # PAYMENT
    # =========================================================================
    ClauseTemplate(
        clause_type="payment",
        jurisdiction="UAE",
        recommended_clause_text=(
            "All invoices shall be payable within thirty (30) days of the invoice date. "
            "Late payments shall bear a late payment fee of 1% per month or the maximum "
            "rate permitted by law, whichever is lower. All payments shall be made in "
            "United Arab Emirates Dirhams (AED) unless otherwise agreed in writing."
        ),
        notes="UAE Federal Law permits late payment fees. Specify currency clearly.",
        risk_triggers=RISK_TRIGGERS["payment"],
    ),
    ClauseTemplate(
        clause_type="payment",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "All invoices shall be payable within thirty (30) days of the invoice date. "
            "Late payments shall bear interest at the rate of 4% per annum above the "
            "Bank of England base rate. All payments shall be made in United States "
            "Dollars (USD) or United Arab Emirates Dirhams (AED) as specified in the invoice."
        ),
        notes="DIFC permits interest on late payments. Standard commercial terms apply.",
        risk_triggers=RISK_TRIGGERS["payment"],
    ),
    ClauseTemplate(
        clause_type="payment",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "All invoices shall be payable within thirty (30) days of the invoice date. "
            "Late payments shall bear interest at the rate of 4% per annum above the "
            "Bank of England base rate. All payments shall be made in United States "
            "Dollars (USD) or United Arab Emirates Dirhams (AED) as specified in the invoice."
        ),
        notes="ADGM permits interest on late payments. English law principles apply.",
        risk_triggers=RISK_TRIGGERS["payment"],
    ),
    ClauseTemplate(
        clause_type="payment",
        jurisdiction="KSA",
        recommended_clause_text=(
            "All invoices shall be payable within thirty (30) days of the invoice date. "
            "Late payments may incur administrative fees as permitted by applicable law. "
            "All payments shall be made in Saudi Riyals (SAR) unless otherwise agreed "
            "in writing. Interest-based late payment fees may not be enforceable under "
            "Saudi law."
        ),
        notes="Saudi Sharia law prohibits riba (interest). Use administrative fees instead.",
        risk_triggers=RISK_TRIGGERS["payment"],
    ),
    # =========================================================================
    # INTELLECTUAL PROPERTY (IP)
    # =========================================================================
    ClauseTemplate(
        clause_type="ip",
        jurisdiction="UAE",
        recommended_clause_text=(
            "All intellectual property rights in any work product, deliverables, or "
            "materials created under this Agreement shall vest in the Client upon full "
            "payment. The Service Provider retains ownership of all pre-existing "
            "intellectual property and grants the Client a non-exclusive license to use "
            "such pre-existing IP solely as necessary to use the deliverables."
        ),
        notes="UAE IP law follows international standards. Clearly define work product.",
        risk_triggers=RISK_TRIGGERS["ip"],
    ),
    ClauseTemplate(
        clause_type="ip",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "All intellectual property rights in any work product, deliverables, or "
            "materials created under this Agreement shall vest in the Client upon full "
            "payment. The Service Provider retains ownership of all pre-existing "
            "intellectual property ('Background IP') and grants the Client a perpetual, "
            "royalty-free, non-exclusive license to use such Background IP solely as "
            "necessary to use the deliverables."
        ),
        notes="DIFC follows English IP law. Define Background IP and assignment clearly.",
        risk_triggers=RISK_TRIGGERS["ip"],
    ),
    ClauseTemplate(
        clause_type="ip",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "All intellectual property rights in any work product, deliverables, or "
            "materials created under this Agreement shall vest in the Client upon full "
            "payment. The Service Provider retains ownership of all pre-existing "
            "intellectual property ('Background IP') and grants the Client a perpetual, "
            "royalty-free, non-exclusive license to use such Background IP solely as "
            "necessary to use the deliverables."
        ),
        notes="ADGM applies English IP law. Standard IP assignment language is enforceable.",
        risk_triggers=RISK_TRIGGERS["ip"],
    ),
    ClauseTemplate(
        clause_type="ip",
        jurisdiction="KSA",
        recommended_clause_text=(
            "All intellectual property rights in any work product, deliverables, or "
            "materials created under this Agreement shall vest in the Client upon full "
            "payment. The Service Provider retains ownership of all pre-existing "
            "intellectual property and grants the Client a license to use such "
            "pre-existing IP solely as necessary to use the deliverables."
        ),
        notes="KSA IP law is developing. Ensure clear assignment and registration.",
        risk_triggers=RISK_TRIGGERS["ip"],
    ),
    # =========================================================================
    # FORCE MAJEURE
    # =========================================================================
    ClauseTemplate(
        clause_type="force_majeure",
        jurisdiction="UAE",
        recommended_clause_text=(
            "Neither Party shall be liable for any failure or delay in performing its "
            "obligations under this Agreement due to circumstances beyond its reasonable "
            "control, including but not limited to acts of God, natural disasters, war, "
            "terrorism, pandemic, epidemic, government actions, or civil unrest. The "
            "affected Party shall notify the other Party promptly and use reasonable "
            "efforts to mitigate the effects of the force majeure event."
        ),
        notes="UAE Civil Code recognizes force majeure. Include notice requirements.",
        risk_triggers=RISK_TRIGGERS["force_majeure"],
    ),
    ClauseTemplate(
        clause_type="force_majeure",
        jurisdiction="DIFC",
        recommended_clause_text=(
            "Neither Party shall be liable for any failure or delay in performing its "
            "obligations under this Agreement due to circumstances beyond its reasonable "
            "control, including but not limited to acts of God, natural disasters, war, "
            "terrorism, pandemic, epidemic, government actions, or civil unrest. The "
            "affected Party shall: (a) notify the other Party promptly; (b) use reasonable "
            "efforts to mitigate the effects; and (c) if the force majeure continues for "
            "more than ninety (90) days, either Party may terminate this Agreement."
        ),
        notes="DIFC follows English law. Include termination rights for prolonged events.",
        risk_triggers=RISK_TRIGGERS["force_majeure"],
    ),
    ClauseTemplate(
        clause_type="force_majeure",
        jurisdiction="ADGM",
        recommended_clause_text=(
            "Neither Party shall be liable for any failure or delay in performing its "
            "obligations under this Agreement due to circumstances beyond its reasonable "
            "control, including but not limited to acts of God, natural disasters, war, "
            "terrorism, pandemic, epidemic, government actions, or civil unrest. The "
            "affected Party shall: (a) notify the other Party promptly; (b) use reasonable "
            "efforts to mitigate the effects; and (c) if the force majeure continues for "
            "more than ninety (90) days, either Party may terminate this Agreement."
        ),
        notes="ADGM applies English law. Standard force majeure clauses are enforceable.",
        risk_triggers=RISK_TRIGGERS["force_majeure"],
    ),
    ClauseTemplate(
        clause_type="force_majeure",
        jurisdiction="KSA",
        recommended_clause_text=(
            "Neither Party shall be liable for any failure or delay in performing its "
            "obligations under this Agreement due to circumstances beyond its reasonable "
            "control, including but not limited to acts of God, natural disasters, war, "
            "terrorism, pandemic, epidemic, government actions, or civil unrest. The "
            "affected Party shall notify the other Party promptly and use reasonable "
            "efforts to mitigate the effects of the force majeure event."
        ),
        notes="Saudi law recognizes force majeure. Ensure clear definitions.",
        risk_triggers=RISK_TRIGGERS["force_majeure"],
    ),
]


# =============================================================================
# Helper Functions
# =============================================================================


def get_clause_types() -> list[ClauseType]:
    """Get list of all supported clause types."""
    return [e.value for e in ClauseTypeEnum]


def get_risk_triggers(clause_type: ClauseType) -> list[str]:
    """Get risk trigger keywords for a clause type.

    Args:
        clause_type: The clause type to get triggers for

    Returns:
        List of trigger keywords (lowercase)
    """
    return RISK_TRIGGERS.get(clause_type, [])


def get_clause_for_jurisdiction(
    clause_type: ClauseType, jurisdiction: Jurisdiction
) -> ClauseTemplate | None:
    """Get the recommended clause template for a specific type and jurisdiction.

    Args:
        clause_type: The clause type
        jurisdiction: The jurisdiction

    Returns:
        ClauseTemplate if found, None otherwise
    """
    for template in CLAUSE_LIBRARY:
        if template.clause_type == clause_type and template.jurisdiction == jurisdiction:
            return template
    return None
