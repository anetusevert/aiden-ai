"""KSA Umm Al-Qura (Official Gazette) connector for gazette item discovery."""

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

UAQ_BASE_URL = "https://uqn.gov.sa"
UAQ_MAIN_URL = "https://uqn.gov.sa/"
UAQ_DECISIONS_URL = "https://uqn.gov.sa/DecisionsAndSystems"
UAQ_CATEGORY_URLS = [
    "https://uqn.gov.sa/section",
    "https://uqn.gov.sa/category?cat=5",
    "https://uqn.gov.sa/category?cat=13",
    "https://uqn.gov.sa/category?cat=18",
]

DETAILS_URL_PATTERN = re.compile(r"/details\?p=\d+")

GREGORIAN_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
]

ARABIC_GREGORIAN_PATTERN = re.compile(r"الموافق\s*(\d{4})-(\d{1,2})-(\d{1,2})")
ISSUE_NUMBER_PATTERN = re.compile(r"العدد\s*(\d+)")

MIN_GREGORIAN_YEAR = 1900


def _is_valid_gregorian_year(year: int) -> bool:
    current_year = datetime.now(timezone.utc).year
    max_year = current_year + 1
    return MIN_GREGORIAN_YEAR <= year <= max_year


def _parse_gregorian_date(text: str, source_url: str | None = None) -> str | None:
    match = ARABIC_GREGORIAN_PATTERN.search(text)
    if match:
        year_str, month_str, day_str = match.groups()
        year = int(year_str)
        try:
            dt = datetime(year, int(month_str), int(day_str))
            if _is_valid_gregorian_year(year):
                return dt.strftime("%Y-%m-%d")
            else:
                logger.info("published_at_guess skipped (year out of range): %s url=%s", match.group(0), source_url or "unknown")
        except ValueError:
            pass

    match = GREGORIAN_DATE_PATTERNS[0].search(text)
    if match:
        day, month, year_str = match.groups()
        year = int(year_str)
        try:
            dt = datetime(year, int(month), int(day))
            if _is_valid_gregorian_year(year):
                return dt.strftime("%Y-%m-%d")
            else:
                logger.info("published_at_guess skipped (year out of range, likely Hijri): %s url=%s", match.group(0), source_url or "unknown")
        except ValueError:
            pass

    match = GREGORIAN_DATE_PATTERNS[1].search(text)
    if match:
        year_str, month, day = match.groups()
        year = int(year_str)
        try:
            dt = datetime(year, int(month), int(day))
            if _is_valid_gregorian_year(year):
                return dt.strftime("%Y-%m-%d")
            else:
                logger.info("published_at_guess skipped (year out of range, likely Hijri): %s url=%s", match.group(0), source_url or "unknown")
        except ValueError:
            pass

    return None


def _extract_detail_urls(html: bytes, base_url: str) -> list[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.warning("Failed to parse listing HTML: %s", e)
        return []

    urls: set[str] = set()
    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag["href"])
        if DETAILS_URL_PATTERN.search(href):
            full_url = urljoin(base_url, href)
            urls.add(full_url)
    return list(urls)


def _clean_title(title: str) -> str:
    return title.rstrip(" |").strip()


def _extract_title_ar(soup: BeautifulSoup, html_text: str) -> str | None:
    for h5 in soup.find_all("h5"):
        text = h5.get_text(strip=True)
        if "العدد" in text:
            return _clean_title(text)

    issue_match = ISSUE_NUMBER_PATTERN.search(html_text)
    if issue_match:
        issue_num = issue_match.group(1)
        return f"العدد {issue_num}"

    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        if text and len(text) > 3:
            for suffix in [" - جريدة أم القرى", " :: أم القرى", "جريدة أم القرى"]:
                text = text.replace(suffix, "").strip()
            if text:
                return _clean_title(text)

    for tag in ["h1", "h2", "h3"]:
        for header in soup.find_all(tag):
            text = header.get_text(strip=True)
            if text and len(text) > 3 and any("\u0600" <= c <= "\u06FF" for c in text):
                return _clean_title(text)

    return None


def _extract_published_date(soup: BeautifulSoup, html_text: str, source_url: str | None = None) -> str | None:
    return _parse_gregorian_date(html_text, source_url)


class KsaUaqConnector(Connector):
    """Connector for KSA Umm Al-Qura (Official Gazette) items."""

    name = "ksa_uaq"
    jurisdiction = "KSA"
    source_name = "uaq_portal"

    _failure_reasons: list[str]

    def __init__(self, http: HttpClient, out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []

    def list_items(self, limit: int) -> list[SourceItem]:
        """Discover gazette detail URLs from Umm Al-Qura listing pages."""
        if limit < 1:
            return []

        all_urls: set[str] = set()
        listing_pages = [
            (UAQ_MAIN_URL, "Main page"),
            (UAQ_DECISIONS_URL, "Decisions and Systems"),
        ] + [(url, f"Category: {url.split('=')[-1] if '=' in url else 'section'}")
             for url in UAQ_CATEGORY_URLS]

        for page_url, description in listing_pages:
            if len(all_urls) >= limit:
                break
            logger.info("Fetching %s from %s", description, page_url)
            try:
                html = self.http.get(page_url)
                urls = _extract_detail_urls(html, UAQ_BASE_URL)
                logger.info("Found %d detail URLs from %s", len(urls), description)
                all_urls.update(urls)
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", description, e)
                self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}")

        url_list = sorted(all_urls)[:limit]
        logger.info("Total unique detail URLs discovered: %d", len(url_list))

        items: list[SourceItem] = []
        for url in url_list:
            items.append(SourceItem(source_url=url, meta={"connector": self.name}))
        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        """Fetch a gazette detail page and extract metadata."""
        logger.info("Fetching gazette item: %s", item.source_url)

        html = self.http.get(item.source_url)
        logger.debug("Received %d bytes", len(html))

        raw_artifact_path, raw_sha256 = save_artifact(self.out_dir, html, "html")
        logger.info("Saved artifact: %s url=%s", raw_artifact_path, item.source_url)

        title_ar = None
        published_at_guess = None

        try:
            soup = BeautifulSoup(html, "html.parser")
            html_text = html.decode("utf-8", errors="replace")
            title_ar = _extract_title_ar(soup, html_text)
            published_at_guess = _extract_published_date(soup, html_text, item.source_url)

            if title_ar:
                logger.debug("Extracted title: %s...", title_ar[:50])
            else:
                logger.debug("Could not extract Arabic title")
                self._failure_reasons.append("title_extraction_failed")
        except Exception as e:
            logger.warning("Parsing failed for %s: %s", item.source_url, e)
            self._failure_reasons.append(f"parse_failed: {type(e).__name__}")

        instrument_type = guess_instrument_type_ar(
            title=title_ar,
            content_sample=html.decode("utf-8", errors="replace")[:500] if html else None,
            default="other",
        )

        record = ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=title_ar,
            title_en=None,
            instrument_type_guess=instrument_type,
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
