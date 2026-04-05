"""KSA Ministry of Justice (MOJ) connector for scraping Saudi judicial circulars.

Note: The MOJ portal only provides Hijri dates. published_at_guess is set to null.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from src.harvesters.connectors.base import Connector
from src.harvesters.models import ParsedRecord, SourceItem
from src.harvesters.storage import save_artifact

if TYPE_CHECKING:
    from src.harvesters.http import HttpClient

logger = logging.getLogger(__name__)

MOJ_BASE_URL = "https://portaleservices.moj.gov.sa"
MOJ_CIRCULARS_URL = "https://portaleservices.moj.gov.sa/TameemPortal/TameemList.aspx"

MIN_GREGORIAN_YEAR = 1900


def _is_valid_gregorian_year(year: int) -> bool:
    current_year = datetime.now(timezone.utc).year
    max_year = current_year + 1
    return MIN_GREGORIAN_YEAR <= year <= max_year


def _parse_explicit_gregorian_date(text: str, source_url: str | None = None) -> str | None:
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if match:
        day, month, year_str = match.groups()
        year = int(year_str)
        if _is_valid_gregorian_year(year):
            try:
                dt = datetime(year, int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if match:
        year_str, month, day = match.groups()
        year = int(year_str)
        if _is_valid_gregorian_year(year):
            try:
                dt = datetime(year, int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', text)
    if match:
        year_str, month, day = match.groups()
        year = int(year_str)
        if _is_valid_gregorian_year(year) and year >= 1900:
            try:
                dt = datetime(year, int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


class CircularEntry:
    """Represents a circular entry parsed from the listing page."""

    def __init__(
        self,
        circular_id: str,
        circular_number: str,
        hijri_date: str,
        category: str,
        text_snippet: str,
    ) -> None:
        self.circular_id = circular_id
        self.circular_number = circular_number
        self.hijri_date = hijri_date
        self.category = category
        self.text_snippet = text_snippet


def _parse_circular_entries(html: bytes) -> list[CircularEntry]:
    entries: list[CircularEntry] = []
    seen_ids: set[str] = set()

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse listing HTML: %s", e)
        return []

    text_content = soup.get_text()
    date_matches = list(re.finditer(r'(\d{4}/\d{1,2}/\d{1,2})', text_content))

    for i, match in enumerate(date_matches):
        date_str = match.group(1)
        pos = match.start()

        start = max(0, pos - 150)
        end = min(len(text_content), pos + 300)
        context_before = text_content[start:pos]
        context_after = text_content[pos + len(date_str):end]

        circular_patterns = [
            r'(\d+/\d+/[تكبجخصعقم])',
            r'(\d+/[تكبجخصعقم]/\d+)',
            r'(\d+/\d+/\d+/[تكبجخصعقم])',
            r'(\d+/[تكبجخصعقم])',
        ]

        circular_num = None
        for pattern in circular_patterns:
            circular_match = re.search(pattern, context_before)
            if circular_match:
                circular_num = circular_match.group(1)
                break

        if not circular_num:
            general_match = re.search(r'(\d[\d/]*[/][تكبجخصعقم][\d/]*|\d[\d/]*[تكبجخصعقم])', context_before[-60:])
            if general_match:
                circular_num = general_match.group(1).strip()
            else:
                circular_num = f"تعميم_{i+1}"

        id_match = re.search(r'\b(\d{5})\b', context_after)
        circular_id = id_match.group(1) if id_match else str(10000 + i)

        if circular_id in seen_ids:
            continue
        seen_ids.add(circular_id)

        categories = [
            "تعويضات", "جنسية وجوازات", "أراض", "أروش", "استحكام",
            "إقـرار", "أنظمة التمييز", "بلديات", "بنـوك", "بيـع",
            "تركات", "تصديقات", "تعزير", "حدود", "حصر الإرث",
            "دعـوى", "الديـات", "زنــا", "سجناء", "شركات",
            "الصكوك", "الوكالة", "الوقف", "النكاح", "تنظيم",
            "المنح", "أجانب", "الطرق", "قتل الخطأ", "قتل العمد",
            "القسمة", "كتاب العدل", "الولاية والوصاية", "رهـن",
            "الحق العام", "حوادث السيارات", "المسكرات والمخدرات"
        ]
        category = "عام"
        for cat in categories:
            if cat in context_after[:100]:
                category = cat
                break

        snippet_match = re.search(r'[«\(]\.{0,3}([^»\)]{10,200})', context_after)
        if snippet_match:
            text_snippet = snippet_match.group(1).strip()[:150]
        else:
            text_snippet = context_after[:150].strip()

        entry = CircularEntry(
            circular_id=circular_id,
            circular_number=circular_num,
            hijri_date=date_str,
            category=category,
            text_snippet=text_snippet,
        )
        entries.append(entry)

    return entries


class KsaMojConnector(Connector):
    """Connector for KSA Ministry of Justice (MOJ) judicial circulars."""

    name = "ksa_moj"
    jurisdiction = "KSA"
    source_name = "moj"

    _diagnostic_info: dict[str, list[str] | bool | int]
    _failure_reasons: list[str]
    _cached_html: bytes | None

    def __init__(self, http: HttpClient, out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._diagnostic_info = {
            "urls_tried": [],
            "http_statuses": [],
            "js_only_detected": False,
            "auth_detected": False,
            "content_length": 0,
        }
        self._failure_reasons = []
        self._cached_html = None

    def list_items(self, limit: int) -> list[SourceItem]:
        """Discover circular URLs from MOJ listing page."""
        if limit < 1:
            return []

        items: list[SourceItem] = []

        logger.info("Fetching MOJ circulars from %s", MOJ_CIRCULARS_URL)
        urls_tried = self._diagnostic_info["urls_tried"]
        assert isinstance(urls_tried, list)
        urls_tried.append(MOJ_CIRCULARS_URL)

        try:
            html = self.http.get(MOJ_CIRCULARS_URL)
            self._cached_html = html
            self._diagnostic_info["content_length"] = len(html)
            http_statuses = self._diagnostic_info["http_statuses"]
            assert isinstance(http_statuses, list)
            http_statuses.append("200")

            html_str = html.decode("utf-8", errors="replace")
            if len(html_str) < 1000 and ("script" in html_str.lower() or "angular" in html_str.lower()):
                self._diagnostic_info["js_only_detected"] = True
                logger.warning("Page appears to be JavaScript-only")

            if "login" in html_str.lower() or "authenticate" in html_str.lower():
                if "LoginForm" in html_str or "password" in html_str.lower():
                    self._diagnostic_info["auth_detected"] = True
                    logger.warning("Authentication may be required")

            entries = _parse_circular_entries(html)
            logger.info("Found %d circular entries", len(entries))

            for entry in entries[:limit]:
                source_url = f"{MOJ_CIRCULARS_URL}#circular_{entry.circular_id}"
                items.append(SourceItem(
                    source_url=source_url,
                    meta={
                        "connector": self.name,
                        "circular_id": entry.circular_id,
                        "circular_number": entry.circular_number,
                        "hijri_date": entry.hijri_date,
                        "category": entry.category,
                        "text_snippet": entry.text_snippet,
                    }
                ))

            items.sort(key=lambda x: x.source_url)
            logger.info("Returning %d items (sorted by source_url)", len(items))

        except Exception as e:
            error_msg = str(e)
            logger.warning("Failed to fetch MOJ circulars: %s", error_msg)
            self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}: {error_msg}")

        if not items:
            self._print_diagnostic_summary()

        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        """Fetch and parse a circular entry."""
        logger.info("Processing circular: %s", item.source_url)

        if self._cached_html is not None:
            html = self._cached_html
        else:
            html = self.http.get(MOJ_CIRCULARS_URL)

        raw_artifact_path, raw_sha256 = save_artifact(self.out_dir, html, "html")
        logger.debug("Saved real HTML artifact: %s", raw_artifact_path)

        meta = item.meta or {}
        circular_number = meta.get("circular_number", "")
        hijri_date = meta.get("hijri_date", "")
        category = meta.get("category", "")

        title_ar = None
        if circular_number:
            title_ar = f"تعميم رقم {circular_number}"
            if category:
                title_ar += f" - {category}"
        elif category:
            title_ar = f"تعميم - {category}"

        html_text = html.decode("utf-8", errors="replace")
        published_at_guess = _parse_explicit_gregorian_date(html_text, item.source_url)

        if published_at_guess is None and hijri_date:
            logger.debug(
                "No Gregorian date found, Hijri date available: %s (not converted) url=%s",
                hijri_date, item.source_url,
            )

        record = ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=title_ar,
            title_en=None,
            instrument_type_guess="circular",
            published_at_guess=published_at_guess,
            raw_artifact_path=raw_artifact_path,
            raw_sha256=raw_sha256,
        )
        return record

    def _print_diagnostic_summary(self) -> None:
        logger.warning("KSA MOJ CONNECTOR - No items found. Diagnostic info: %s", self._diagnostic_info)

    def get_failure_summary(self) -> dict[str, int]:
        """Get summary of failure reasons during this run."""
        summary: dict[str, int] = {}
        for reason in self._failure_reasons:
            category = reason.split(":")[0] if ":" in reason else reason
            summary[category] = summary.get(category, 0) + 1
        return summary
