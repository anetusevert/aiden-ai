"""UAE Ministry of Justice connector for scraping UAE federal laws."""

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

UAE_MOJ_BASE_URL = "https://elaws.moj.gov.ae"
UAE_MOJ_LAWS_EN_URL = "https://elaws.moj.gov.ae/English.aspx?val=UAE-KaitEL1"
UAE_MOJ_LAWS_AR_URL = "https://elaws.moj.gov.ae/ArabicEnglish.aspx?val=UAE-KaitA1"
UAE_MOJ_INDEX_URL = "https://elaws.moj.gov.ae/indexEN.aspx"

UAE_MOJ_CATEGORY_PAGES = [
    ("https://elaws.moj.gov.ae/English.aspx?val=UAE-KaitEL1", "Federal Laws"),
]

LAW_DETAIL_PATTERNS = [
    re.compile(r"/Legislation\.aspx\?", re.IGNORECASE),
    re.compile(r"/ArabicEnglish\.aspx\?", re.IGNORECASE),
    re.compile(r"\.pdf$", re.IGNORECASE),
]

LAW_ID_PATTERN = re.compile(r"val=([A-Za-z0-9_-]+)", re.IGNORECASE)

GREGORIAN_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})/(\d{2})/(\d{2})"),
]

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

    match = GREGORIAN_DATE_PATTERNS[2].search(text)
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


def _extract_category_items(html: bytes, base_url: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse category HTML: %s", e)
        return []

    for table in soup.find_all("table"):
        for td in table.find_all("td"):
            text = td.get_text(strip=True)
            if text and len(text) > 2:
                if text.isupper() or any("\u0600" <= c <= "\u06FF" for c in text):
                    for a in td.find_all("a", href=True):
                        href = str(a.get("href", ""))
                        link_text = a.get_text(strip=True)
                        if href and "javascript" not in href.lower():
                            full_url = urljoin(base_url, href)
                            id_match = LAW_ID_PATTERN.search(href)
                            item_id = id_match.group(1) if id_match else href
                            if item_id not in seen_ids:
                                seen_ids.add(item_id)
                                items.append({
                                    "url": full_url,
                                    "category": text,
                                    "title": link_text or text,
                                    "item_id": item_id,
                                })

    for a in soup.find_all("a", href=True):
        href = str(a.get("href", ""))
        if any(pattern.search(href) for pattern in LAW_DETAIL_PATTERNS[:2]):
            full_url = urljoin(base_url, href)
            link_text = a.get_text(strip=True)
            id_match = LAW_ID_PATTERN.search(href)
            item_id = id_match.group(1) if id_match else href
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                items.append({
                    "url": full_url,
                    "category": "federal_law",
                    "title": link_text,
                    "item_id": item_id,
                })

    return items


def _extract_law_entries_from_tree(html: bytes) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen_categories: set[str] = set()

    html_text = html.decode("utf-8", errors="replace")

    postback_pattern = re.compile(
        r"__doPostBack\([^,]+,\s*['\"]t?C:\*\|\*S-UAE_MOJ\*\|\*elaws\*\|\*[^*]+\*\|\*00_([^'\"]+)['\"]",
        re.IGNORECASE
    )

    for match in postback_pattern.finditer(html_text):
        category = match.group(1)
        category = category.replace("%20", " ").strip()
        if category in seen_categories:
            continue
        seen_categories.add(category)
        entries.append({"category": category, "display_name": category})

    expand_pattern = re.compile(r'(?:title|alt)="Expand ([^"]+)"', re.IGNORECASE)
    for match in expand_pattern.finditer(html_text):
        category = match.group(1).strip()
        if category and category not in seen_categories:
            seen_categories.add(category)
            entries.append({"category": category, "display_name": category})

    return entries


def _extract_title_ar(soup: BeautifulSoup, html_text: str) -> str | None:
    for tag in ["h1", "h2", "h3", "title"]:
        for elem in soup.find_all(tag):
            text = elem.get_text(strip=True)
            if text and any("\u0600" <= c <= "\u06FF" for c in text):
                text = text.replace(" | وزارة العدل", "").strip()
                text = text.replace("Ministry of Justice", "").strip()
                if len(text) > 5:
                    return text

    arabic_pattern = re.compile(r"[\u0600-\u06FF\s]{10,200}")
    matches: list[str] = arabic_pattern.findall(html_text)
    if matches:
        return max(matches, key=len).strip()

    return None


def _extract_title_en(soup: BeautifulSoup, html_text: str) -> str | None:
    for tag in ["h1", "h2", "h3"]:
        for elem in soup.find_all(tag):
            text = elem.get_text(strip=True)
            if text and len(text) > 5 and not any("\u0600" <= c <= "\u06FF" for c in text):
                text = text.replace("Ministry of Justice", "").strip()
                text = text.replace(" | ", "").strip()
                if text and len(text) > 5:
                    return text

    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        parts = text.split("|")
        for part in parts:
            part = part.strip()
            if part and len(part) > 5 and not any("\u0600" <= c <= "\u06FF" for c in part):
                if part.lower() not in ("ministry of justice", "moj", "elaws"):
                    return part

    for elem in soup.find_all(["a", "span", "div"]):
        text = elem.get_text(strip=True)
        if (text and len(text) > 15 and len(text) < 300
                and not any("\u0600" <= c <= "\u06FF" for c in text)
                and any(c.isalpha() for c in text)):
            lower = text.lower()
            if any(kw in lower for kw in ["law", "decree", "regulation", "resolution", "act", "federal"]):
                return text

    return None


def _guess_instrument_type_from_category(category: str) -> str:
    category_lower = category.lower()
    category_map = {
        "constitution": "law",
        "federal law": "federal_law",
        "federal laws": "federal_law",
        "decree": "decree",
        "regulation": "regulation",
        "decision": "order",
        "resolution": "order",
        "circular": "circular",
        "guideline": "guideline",
        "order": "order",
        "cabinet": "order",
        "ministries": "regulation",
    }
    for key, value in category_map.items():
        if key in category_lower:
            return value
    return "federal_law"


class UaeMojConnector(Connector):
    """Connector for UAE Ministry of Justice federal laws."""

    name = "uae_moj"
    jurisdiction = "UAE"
    source_name = "moj_elaws"

    _failure_reasons: list[str]
    _cached_pages: dict[str, bytes]

    def __init__(self, http: HttpClient, out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []
        self._cached_pages = {}

    def list_items(self, limit: int) -> list[SourceItem]:
        """Discover law URLs from UAE MOJ legal portal."""
        if limit < 1:
            return []

        items: list[SourceItem] = []
        all_entries: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for page_url, description in UAE_MOJ_CATEGORY_PAGES:
            if len(all_entries) >= limit:
                break
            logger.info("Fetching UAE MOJ %s from %s", description, page_url)
            try:
                html = self.http.get(page_url)
                self._cached_pages[page_url] = html
                logger.debug("Received %d bytes", len(html))

                tree_entries = _extract_law_entries_from_tree(html)
                logger.info("Found %d categories from TreeView", len(tree_entries))

                for entry in tree_entries:
                    category = entry.get("display_name", "Unknown")
                    category_url = f"{page_url}#category_{category.replace(' ', '_')}"
                    if category_url not in seen_urls:
                        seen_urls.add(category_url)
                        all_entries.append({
                            "url": page_url,
                            "category_url": category_url,
                            "category": category,
                            "title": f"UAE Federal Laws - {category}",
                        })

                direct_items = _extract_category_items(html, page_url)
                logger.info("Found %d direct items from HTML", len(direct_items))
                for item in direct_items:
                    if item["url"] not in seen_urls:
                        seen_urls.add(item["url"])
                        all_entries.append(item)

            except Exception as e:
                logger.warning("Failed to fetch %s: %s", description, e)
                self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}")

        try:
            html = self.http.get(UAE_MOJ_INDEX_URL)
            self._cached_pages[UAE_MOJ_INDEX_URL] = html
            direct_items = _extract_category_items(html, UAE_MOJ_INDEX_URL)
            for item in direct_items:
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    all_entries.append(item)
        except Exception as e:
            logger.warning("Failed to fetch index page: %s", e)

        all_entries = sorted(all_entries, key=lambda x: x.get("category", ""))[:limit]
        logger.info("Total unique entries discovered: %d", len(all_entries))

        for entry in all_entries:
            source_url = entry.get("category_url") or entry.get("url", "")
            if not source_url.startswith("http"):
                continue
            items.append(SourceItem(
                source_url=source_url,
                meta={
                    "connector": self.name,
                    "category": entry.get("category", ""),
                    "title": entry.get("title", ""),
                    "actual_url": entry.get("url", source_url),
                }
            ))

        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        """Fetch a law page and extract metadata."""
        meta = item.meta or {}
        actual_url = meta.get("actual_url", item.source_url.split("#")[0])
        logger.info("Processing UAE law: %s", item.source_url)

        if actual_url in self._cached_pages:
            html = self._cached_pages[actual_url]
            logger.debug("Using cached HTML")
        else:
            try:
                html = self.http.get(actual_url)
                logger.debug("Fetched %d bytes", len(html))
            except Exception as e:
                logger.error("Failed to fetch %s: %s", actual_url, e)
                raise

        raw_artifact_path, raw_sha256 = save_artifact(self.out_dir, html, "html")
        logger.debug("Saved artifact: %s", raw_artifact_path)

        title_ar = None
        title_en = None
        published_at_guess = None
        instrument_type_guess = "federal_law"

        try:
            soup = BeautifulSoup(html, "html.parser")
            html_text = html.decode("utf-8", errors="replace")
            title_ar = _extract_title_ar(soup, html_text)
            title_en = _extract_title_en(soup, html_text)

            if not title_ar:
                category = meta.get("category", "")
                if category:
                    title_ar = f"القوانين الاتحادية - {category}"

            if not title_en:
                category = meta.get("category", "")
                title_from_meta = meta.get("title", "")
                if title_from_meta and title_from_meta != f"UAE Federal Laws - {category}":
                    title_en = title_from_meta
                elif category:
                    title_en = f"UAE Federal Laws - {category}"

            published_at_guess = _parse_gregorian_date(html_text, item.source_url)

            category = meta.get("category", "")
            if category:
                instrument_type_guess = _guess_instrument_type_from_category(category)

            if title_ar:
                ar_guess = guess_instrument_type_ar(
                    title=title_ar,
                    content_sample=html_text[:500] if html_text else None,
                    default="other",
                )
                if ar_guess and ar_guess != "other":
                    instrument_type_guess = ar_guess

        except Exception as e:
            logger.warning("Parsing failed for %s: %s", item.source_url, e)
            self._failure_reasons.append(f"parse_failed: {type(e).__name__}")

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
