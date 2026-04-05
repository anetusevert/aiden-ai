"""Instrument type guessing utilities for Arabic legal documents.

Valid instrument types (from Aiden.ai):
- law, federal_law, local_law
- decree, royal_decree
- regulation
- ministerial_resolution
- circular
- guideline
- directive
- order
- other
"""

from __future__ import annotations

ARABIC_INSTRUMENT_KEYWORDS: list[tuple[str, str]] = [
    ("مرسوم ملكي", "royal_decree"),
    ("أمر ملكي", "order"),
    ("نظام", "law"),
    ("قانون", "law"),
    ("لائحة تنفيذية", "regulation"),
    ("لائحة", "regulation"),
    ("تنظيم", "regulation"),
    ("مرسوم", "decree"),
    ("قرار وزاري", "ministerial_resolution"),
    ("قرار مجلس", "order"),
    ("قرار", "order"),
    ("تعميم", "circular"),
    ("منشور", "circular"),
    ("توجيه", "directive"),
    ("قواعد", "guideline"),
    ("ضوابط", "guideline"),
    ("إرشادات", "guideline"),
    ("دليل", "guideline"),
]


def guess_instrument_type_ar(
    title: str | None,
    content_sample: str | None = None,
    default: str = "other",
) -> str:
    """Guess the instrument type from Arabic text using keyword matching."""
    if title:
        for keyword, inst_type in ARABIC_INSTRUMENT_KEYWORDS:
            if keyword in title:
                return inst_type

    if content_sample:
        sample = content_sample[:500] if len(content_sample) > 500 else content_sample
        for keyword, inst_type in ARABIC_INSTRUMENT_KEYWORDS:
            if keyword in sample:
                return inst_type

    return default


def normalize_instrument_type(type_guess: str | None) -> str:
    """Normalize an instrument type string to a valid enum value."""
    if not type_guess:
        return "other"

    valid_types = frozenset({
        "law", "federal_law", "local_law", "decree", "royal_decree",
        "regulation", "ministerial_resolution", "circular", "guideline",
        "directive", "order", "other",
    })

    normalized = type_guess.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in valid_types:
        return normalized

    legacy_map: dict[str, str] = {
        "system": "law",
        "organization": "regulation",
        "resolution": "order",
        "royal_order": "order",
        "portal_item": "other",
    }

    return legacy_map.get(normalized, "other")
