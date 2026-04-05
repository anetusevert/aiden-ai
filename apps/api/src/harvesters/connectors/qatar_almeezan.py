"""Qatar Al Meezan connector for scraping Qatari laws."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.harvesters.connectors.base import Connector
from src.harvesters.instrument_type import guess_instrument_type_ar
from src.harvesters.models import ParsedRecord, SourceItem
from src.harvesters.storage import save_artifact

if TYPE_CHECKING:
    from src.harvesters.http import HttpClient

logger = logging.getLogger(__name__)

ALMEEZAN_BASE_URL = "https://www.almeezan.qa"
ALMEEZAN_LAWS_AR_URL = "https://www.almeezan.qa/LawsByYear.aspx?language=ar"
ALMEEZAN_LAWS_EN_URL = "https://www.almeezan.qa/LawsByYear.aspx?language=en"
ALMEEZAN_LAW_PAGE_URL = "https://www.almeezan.qa/LawPage.aspx?id={law_id}&language=ar"
ALMEEZAN_LAW_PAGE_EN_URL = "https://www.almeezan.qa/LawPage.aspx?id={law_id}&language=en"

MIN_YEAR = 1954
MAX_YEAR = datetime.now(timezone.utc).year

LAW_ID_PATTERN = re.compile(r"id=(\d+)", re.IGNORECASE)

GREGORIAN_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]

CATEGORY_TO_TYPE: dict[str, str] = {
    "law": "law",
    "قانون": "law",
    "amiri decree": "decree",
    "مرسوم أميري": "decree",
    "cabinet decision": "order",
    "قرار مجلس الوزراء": "order",
    "ministerial decree": "regulation",
    "قرار وزاري": "regulation",
    "constitution": "law",
    "دستور": "law",
    "act": "law",
    "decree": "decree",
    "decision": "order",
    "resolution": "order",
}


def _is_valid_gregorian_year(year: int) -> bool:
    current_year = datetime.now(timezone.utc).year
    max_year = current_year + 1
    return MIN_YEAR <= year <= max_year


def _parse_gregorian_date(text: str) -> str | None:
    match = GREGORIAN_DATE_PATTERNS[0].search(text)
    if match:
        day, month, year_str = match.groups()
        year = int(year_str)
        if _is_valid_gregorian_year(year):
            try:
                dt = datetime(year, int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    match = GREGORIAN_DATE_PATTERNS[1].search(text)
    if match:
        year_str, month, day = match.groups()
        year = int(year_str)
        if _is_valid_gregorian_year(year):
            try:
                dt = datetime(year, int(month), int(day))
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


def _guess_instrument_type_from_text(text: str) -> str:
    text_lower = text.lower()
    for key, value in CATEGORY_TO_TYPE.items():
        if key in text_lower:
            return value

    ar_guess = guess_instrument_type_ar(title=text, default="other")
    if ar_guess and ar_guess != "other":
        return ar_guess

    return "law"


def _extract_law_list(html: bytes, base_url: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse listing HTML: %s", e)
        return []

    for a in soup.find_all("a", href=True):
        href = str(a.get("href", ""))
        if "LawPage.aspx" in href:
            id_match = LAW_ID_PATTERN.search(href)
            if id_match:
                law_id = id_match.group(1)
                if law_id in seen_ids:
                    continue
                seen_ids.add(law_id)
                link_text = a.get_text(strip=True)
                full_url = urljoin(base_url, href)
                entries.append({
                    "law_id": law_id,
                    "url": full_url,
                    "title": link_text,
                })

    return entries


def _extract_law_detail(html: bytes) -> dict[str, str | None]:
    details: dict[str, str | None] = {}

    try:
        soup = BeautifulSoup(html, "html.parser")
        html_text = html.decode("utf-8", errors="replace")
    except Exception as e:
        logger.warning("Failed to parse law detail HTML: %s", e)
        return details

    for tag in ["h1", "h2", "h3"]:
        elem = soup.find(tag)
        if elem:
            text = elem.get_text(strip=True)
            if text and any("\u0600" <= c <= "\u06FF" for c in text):
                details["title_ar"] = text
                break

    summary_text = ""
    for div in soup.find_all(["div", "p", "td"]):
        text = div.get_text(strip=True)
        if "Type:" in text or "Number:" in text or "Date:" in text:
            summary_text = text
            break

    if summary_text:
        type_match = re.search(r"Type:\s*(\w+)", summary_text, re.IGNORECASE)
        if type_match:
            details["law_type"] = type_match.group(1)
        num_match = re.search(r"Number:\s*(\d+)", summary_text, re.IGNORECASE)
        if num_match:
            details["law_number"] = num_match.group(1)
        details["published_at"] = _parse_gregorian_date(summary_text)

    if "published_at" not in details:
        details["published_at"] = _parse_gregorian_date(html_text)

    return details


def _extract_title_en_from_page(html: bytes) -> str | None:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse English law page HTML: %s", e)
        return None

    for tag in ["h1", "h2", "h3"]:
        elem = soup.find(tag)
        if elem:
            text = elem.get_text(strip=True)
            if text and len(text) > 3 and not any("\u0600" <= c <= "\u06FF" for c in text):
                return text

    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        for suffix in [" - Al Meezan", " :: Al Meezan", " | Al Meezan",
                       " - Qatar Legal Portal", "Al Meezan - Qatar Legal Portal"]:
            text = text.replace(suffix, "").strip()
        if text and len(text) > 3 and not any("\u0600" <= c <= "\u06FF" for c in text):
            return text

    for div in soup.find_all(["div", "span", "td"]):
        text = div.get_text(strip=True)
        if (text and len(text) > 10 and len(text) < 300
                and not any("\u0600" <= c <= "\u06FF" for c in text)
                and any(c.isalpha() for c in text)):
            lower = text.lower()
            if any(kw in lower for kw in ["law", "decree", "decision", "resolution",
                                           "act", "regulation", "amiri", "cabinet"]):
                return text

    return None


class QatarAlmeezanConnector(Connector):
    """Connector for Qatar Al Meezan legal portal."""

    name = "qatar_almeezan"
    jurisdiction = "QAT"
    source_name = "almeezan"

    _failure_reasons: list[str]
    _cached_pages: dict[str, bytes]

    def __init__(self, http: HttpClient, out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []
        self._cached_pages = {}

    def list_items(self, limit: int) -> list[SourceItem]:
        """Discover law URLs from Al Meezan legal portal."""
        if limit < 1:
            return []

        items: list[SourceItem] = []
        all_entries: list[dict[str, str]] = []
        seen_ids: set[str] = set()

        logger.info("Fetching Al Meezan laws listing from %s", ALMEEZAN_LAWS_AR_URL)
        try:
            html = self.http.get(ALMEEZAN_LAWS_AR_URL)
            self._cached_pages[ALMEEZAN_LAWS_AR_URL] = html
            logger.debug("Received %d bytes", len(html))
            entries = _extract_law_list(html, ALMEEZAN_BASE_URL)
            logger.info("Found %d laws from listing", len(entries))
            for entry in entries:
                law_id = entry.get("law_id", "")
                if law_id and law_id not in seen_ids:
                    seen_ids.add(law_id)
                    all_entries.append(entry)
        except Exception as e:
            logger.warning("Failed to fetch Arabic listing: %s", e)
            self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}")

        try:
            html = self.http.get(ALMEEZAN_LAWS_EN_URL)
            self._cached_pages[ALMEEZAN_LAWS_EN_URL] = html
            entries = _extract_law_list(html, ALMEEZAN_BASE_URL)
            logger.info("Found %d laws from English listing", len(entries))
            for entry in entries:
                law_id = entry.get("law_id", "")
                if law_id and law_id not in seen_ids:
                    seen_ids.add(law_id)
                    all_entries.append(entry)
        except Exception as e:
            logger.warning("Failed to fetch English listing: %s", e)

        if len(all_entries) < 50:
            logger.info("Generating law URLs from known ID range")
            for numeric_id in range(1, min(limit + len(all_entries), 200)):
                str_id = str(numeric_id)
                if str_id not in seen_ids:
                    seen_ids.add(str_id)
                    url = ALMEEZAN_LAW_PAGE_URL.format(law_id=numeric_id)
                    all_entries.append({
                        "law_id": str_id,
                        "url": url,
                        "title": f"Qatar Law ID {numeric_id}",
                    })

        all_entries.sort(key=lambda x: int(x.get("law_id", "0") or "0"))
        all_entries = all_entries[:limit]
        logger.info("Total entries to process: %d", len(all_entries))

        for entry in all_entries:
            url = entry.get("url", "")
            if not url.startswith("http"):
                continue
            items.append(SourceItem(
                source_url=url,
                meta={
                    "connector": self.name,
                    "law_id": entry.get("law_id", ""),
                    "title": entry.get("title", ""),
                }
            ))

        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        """Fetch a law page and extract metadata."""
        meta = item.meta or {}
        law_id = meta.get("law_id", "")
        logger.info("Processing Qatar law %s: %s", law_id, item.source_url)

        try:
            html = self.http.get(item.source_url)
            logger.debug("Fetched %d bytes (Arabic)", len(html))
        except Exception as e:
            logger.error("Failed to fetch %s: %s", item.source_url, e)
            self._failure_reasons.append(f"fetch_failed: {type(e).__name__}")
            raise

        raw_artifact_path, raw_sha256 = save_artifact(self.out_dir, html, "html")
        logger.debug("Saved artifact: %s", raw_artifact_path)

        title_ar = None
        title_en = None
        published_at_guess = None
        instrument_type_guess = "law"

        try:
            details = _extract_law_detail(html)
            title_ar = details.get("title_ar")
            published_at_guess = details.get("published_at")

            law_type = details.get("law_type", "")
            if law_type:
                instrument_type_guess = _guess_instrument_type_from_text(law_type)
            elif title_ar:
                instrument_type_guess = _guess_instrument_type_from_text(title_ar)

            if not title_ar:
                listing_title = meta.get("title", "")
                if listing_title and listing_title != f"Qatar Law ID {law_id}":
                    title_ar = listing_title
                else:
                    title_ar = f"القانون القطري رقم {law_id}"
        except Exception as e:
            logger.warning("Parsing failed for %s: %s", item.source_url, e)
            self._failure_reasons.append(f"parse_failed: {type(e).__name__}")

        english_url = ALMEEZAN_LAW_PAGE_EN_URL.format(law_id=law_id) if law_id else None
        if not english_url:
            english_url = item.source_url.replace("language=ar", "language=en")

        try:
            html_en = self.http.get(english_url)
            logger.debug("Fetched %d bytes (English)", len(html_en))
            title_en = _extract_title_en_from_page(html_en)
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
