"""KSA Bureau of Experts (BOE) connector for scraping Saudi legal instruments.

This connector fetches laws and regulations from the official BOE portal at
laws.boe.gov.sa. It uses publicly accessible listing pages to discover
instrument URLs and detail pages to extract metadata.
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

BOE_BASE_URL = "https://laws.boe.gov.sa"
BOE_FOLDERS_URL = "https://laws.boe.gov.sa/BoeLaws/Laws/Folders/2"
BOE_MOST_VIEWED_URL = "https://laws.boe.gov.sa/BoeLaws/Laws/LawMostViewed"
BOE_UPDATED_URL = "https://laws.boe.gov.sa/BoeLaws/Laws/LawUpdated/2"

LAW_DETAIL_PATTERN = re.compile(
    r"/BoeLaws/Laws/LawDetails/([a-f0-9-]+)/(\d+)",
    re.IGNORECASE
)

GREGORIAN_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]

ARABIC_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4,
    "مايو": 5, "يونيو": 6, "يوليو": 7, "أغسطس": 8,
    "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}


def _extract_law_urls(html: bytes, base_url: str) -> list[str]:
    """Extract law detail URLs from a listing page."""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse listing HTML: %s", e)
        return []

    urls: set[str] = set()
    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag["href"])
        match = LAW_DETAIL_PATTERN.search(href)
        if match:
            guid = match.group(1)
            full_url = f"{BOE_BASE_URL}/BoeLaws/Laws/LawDetails/{guid}/1"
            urls.add(full_url)
    return list(urls)


MIN_GREGORIAN_YEAR = 1900


def _is_valid_gregorian_year(year: int) -> bool:
    current_year = datetime.now(timezone.utc).year
    max_year = current_year + 1
    return MIN_GREGORIAN_YEAR <= year <= max_year


def _parse_gregorian_date(text: str, source_url: str | None = None) -> str | None:
    match = GREGORIAN_DATE_PATTERNS[0].search(text)
    if match:
        day, month, year_str = match.groups()
        year = int(year_str)
        try:
            dt = datetime(year, int(month), int(day))
            if not _is_valid_gregorian_year(year):
                raw_value = match.group(0)
                logger.info(
                    "published_at_guess skipped (year out of range, likely Hijri or invalid): "
                    "%s url=%s", raw_value, source_url or "unknown",
                )
                return None
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    match = GREGORIAN_DATE_PATTERNS[1].search(text)
    if match:
        year_str, month, day = match.groups()
        year = int(year_str)
        try:
            dt = datetime(year, int(month), int(day))
            if not _is_valid_gregorian_year(year):
                raw_value = match.group(0)
                logger.info(
                    "published_at_guess skipped (year out of range, likely Hijri or invalid): "
                    "%s url=%s", raw_value, source_url or "unknown",
                )
                return None
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def _extract_title_ar(soup: BeautifulSoup) -> str | None:
    system_info = soup.find(class_="system_info")
    if system_info:
        labels = system_info.find_all("label")
        for label in labels:
            label_text = label.get_text(strip=True)
            if label_text == "الاسم":
                span = label.find_next_sibling("span")
                if span:
                    title = span.get_text(strip=True)
                    if title and len(title) > 2:
                        return title
                parent = label.parent
                if parent:
                    span = parent.find("span")
                    if span:
                        title = span.get_text(strip=True)
                        if title and len(title) > 2:
                            return title

    system_title = soup.find(class_="system_title")
    if system_title:
        text = system_title.get_text(strip=True)
        if text and len(text) > 3:
            if "نـــص النظـــام" not in text and "نص النظام" not in text:
                return text

    page_title = soup.find(class_="page-title")
    if page_title:
        text = page_title.get_text(strip=True)
        if text and len(text) > 3:
            return text

    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        for suffix in [" - BOE", " :: BOE", " | BOE", "نظام هيئة الخبراء"]:
            text = text.replace(suffix, "").strip()
        if text and len(text) > 3:
            return text

    for header in soup.find_all("h1"):
        text = header.get_text(strip=True)
        if text and len(text) > 5 and any("\u0600" <= c <= "\u06FF" for c in text):
            skip_phrases = ["الرئيسية", "القائمة", "نـــص النظـــام", "نص النظام"]
            if not any(phrase in text for phrase in skip_phrases):
                return text

    return None


def _extract_title_en(soup: BeautifulSoup) -> str | None:
    system_info = soup.find(class_="system_info")
    if system_info:
        labels = system_info.find_all("label")
        for label in labels:
            label_text = label.get_text(strip=True)
            if label_text.lower() in ("name", "system name", "law name"):
                span = label.find_next_sibling("span")
                if span:
                    title = span.get_text(strip=True)
                    if title and len(title) > 2:
                        return title
                parent = label.parent
                if parent:
                    span = parent.find("span")
                    if span:
                        title = span.get_text(strip=True)
                        if title and len(title) > 2:
                            return title

    system_title = soup.find(class_="system_title")
    if system_title:
        text = system_title.get_text(strip=True)
        if text and len(text) > 3:
            skip = ["Text of System", "System Text", "Law Text"]
            if not any(s.lower() in text.lower() for s in skip):
                return text

    page_title = soup.find(class_="page-title")
    if page_title:
        text = page_title.get_text(strip=True)
        if text and len(text) > 3:
            return text

    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        for suffix in [" - BOE", " :: BOE", " | BOE", "Bureau of Experts"]:
            text = text.replace(suffix, "").strip()
        if text and len(text) > 3:
            if not any("\u0600" <= c <= "\u06FF" for c in text):
                return text

    for header in soup.find_all("h1"):
        text = header.get_text(strip=True)
        if text and len(text) > 5 and not any("\u0600" <= c <= "\u06FF" for c in text):
            skip_phrases = ["Home", "Menu", "Text of System", "System Text"]
            if not any(phrase.lower() in text.lower() for phrase in skip_phrases):
                return text

    return None


def _extract_published_date(soup: BeautifulSoup, html_text: str, source_url: str | None = None) -> str | None:
    text_markers = [
        "Issued Date", "Publishing Date", "issued", "publishing",
        "تاريخ الإصدار", "تاريخ النشر", "صدر بتاريخ"
    ]

    for marker in text_markers:
        if marker.lower() in html_text.lower():
            pattern = re.compile(
                re.escape(marker) + r"[:\s]*(\d{1,2}/\d{1,2}/\d{4})",
                re.IGNORECASE
            )
            match = pattern.search(html_text)
            if match:
                date_str = match.group(1)
                parsed = _parse_gregorian_date(date_str, source_url)
                if parsed:
                    return parsed

    dates_found: list[str] = []
    for pattern in GREGORIAN_DATE_PATTERNS:
        for match in pattern.finditer(html_text):
            date_str = match.group(0)
            parsed = _parse_gregorian_date(date_str, source_url)
            if parsed:
                dates_found.append(parsed)

    if dates_found:
        dates_found.sort()
        return dates_found[0]

    return None


def _guess_instrument_type(soup: BeautifulSoup, title: str | None) -> str | None:
    type_keywords = {
        "نظام": "system",
        "لائحة": "regulation",
        "قرار": "resolution",
        "أمر ملكي": "royal_order",
        "مرسوم ملكي": "royal_decree",
        "قانون": "law",
        "تنظيم": "organization",
    }

    if title:
        for keyword, inst_type in type_keywords.items():
            if keyword in title:
                return inst_type

    text = soup.get_text()
    for keyword, inst_type in type_keywords.items():
        if keyword in text[:500]:
            return inst_type

    return None


class KsaBoeConnector(Connector):
    """Connector for KSA Bureau of Experts (BOE) legal instruments."""

    name = "ksa_boe"
    jurisdiction = "KSA"
    source_name = "boe"

    _failure_reasons: list[str]

    def __init__(self, http: HttpClient, out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []

    def list_items(self, limit: int) -> list[SourceItem]:
        """Discover law URLs from BOE listing pages."""
        if limit < 1:
            return []

        all_urls: set[str] = set()
        listing_pages = [
            (BOE_FOLDERS_URL, "Main folders"),
            (BOE_UPDATED_URL, "Updated laws"),
        ]

        for url, description in listing_pages:
            if len(all_urls) >= limit:
                break
            logger.info("Fetching %s from %s", description, url)
            try:
                html = self.http.get(url)
                urls = _extract_law_urls(html, url)
                logger.info("Found %d law URLs from %s", len(urls), description)
                all_urls.update(urls)
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", description, e)
                self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}")

        url_list = sorted(all_urls)[:limit]
        logger.info("Total unique law URLs discovered: %d", len(url_list))

        items: list[SourceItem] = []
        for url in url_list:
            items.append(SourceItem(source_url=url, meta={"connector": self.name}))
        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        """Fetch a law detail page and extract metadata."""
        logger.info("Fetching law detail: %s", item.source_url)

        html = self.http.get(item.source_url)
        logger.debug("Received %d bytes (Arabic)", len(html))

        raw_artifact_path, raw_sha256 = save_artifact(self.out_dir, html, "html")
        logger.debug("Saved artifact: %s", raw_artifact_path)

        title_ar = None
        title_en = None
        published_at_guess = None
        instrument_type_guess = None

        try:
            soup = BeautifulSoup(html, "html.parser")
            html_text = html.decode("utf-8", errors="replace")

            title_ar = _extract_title_ar(soup)
            published_at_guess = _extract_published_date(soup, html_text, item.source_url)
            instrument_type_guess = _guess_instrument_type(soup, title_ar)

            if title_ar:
                logger.debug("Extracted Arabic title: %s...", title_ar[:50])
            else:
                logger.debug("Could not extract Arabic title")
                self._failure_reasons.append("title_ar_extraction_failed")

        except Exception as e:
            logger.warning("Parsing failed for %s: %s", item.source_url, e)
            self._failure_reasons.append(f"parse_failed: {type(e).__name__}")

        english_url = item.source_url.rstrip("/")
        if english_url.endswith("/1"):
            english_url = english_url[:-1] + "2"

        try:
            html_en = self.http.get(english_url)
            logger.debug("Received %d bytes (English)", len(html_en))
            soup_en = BeautifulSoup(html_en, "html.parser")
            title_en = _extract_title_en(soup_en)

            if title_en:
                logger.debug("Extracted English title: %s...", title_en[:50])
            else:
                logger.debug("Could not extract English title from English page")
        except Exception as e:
            logger.debug("Failed to fetch English page %s: %s", english_url, e)

        record = ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=title_ar,
            title_en=title_en,
            instrument_type_guess=instrument_type_guess,
            published_at_guess=published_at_guess,
            raw_artifact_path=raw_artifact_path,
            raw_sha256=raw_sha256,
        )
        return record

    def get_failure_summary(self) -> dict[str, int]:
        """Get summary of failure reasons during this run."""
        summary: dict[str, int] = {}
        for reason in self._failure_reasons:
            category = reason.split(":")[0] if ":" in reason else reason
            summary[category] = summary.get(category, 0) + 1
        return summary
