"""KSA Scientific Judicial Portal (SJP) connector — public circulars scraper.

Scrapes publicly accessible sections of the Ministry of Justice SJP portal for
recent judicial circulars and guidance. Authenticated content is skipped with a
clear run_log warning.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.harvesters.connectors.base import Connector
from src.harvesters.models import ParsedRecord, SourceItem
from src.harvesters.storage import save_artifact

if TYPE_CHECKING:
    from src.harvesters.http import HttpClient

logger = logging.getLogger(__name__)

SJP_BASE = "https://sjp.moj.gov.sa"
SJP_URLS = [
    "https://sjp.moj.gov.sa",
    "https://sjp.moj.gov.sa/Circulars",
    "https://sjp.moj.gov.sa/PublishedContent",
]


def _parse_date(text: str) -> str | None:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return m.group(0)
        except ValueError:
            pass
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        day, month, year = m.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _looks_like_auth_wall(soup: BeautifulSoup, html_text: str) -> bool:
    """Detect if the page requires authentication."""
    login_indicators = ["login", "sign in", "تسجيل الدخول", "username", "password"]
    text_lower = html_text.lower()
    for indicator in login_indicators:
        if indicator in text_lower:
            form = soup.find("form")
            if form:
                inputs = form.find_all("input")
                input_names = [i.get("name", "").lower() for i in inputs]
                if any(n in ("username", "password", "email") for n in input_names):
                    return True
    return False


class KsaSjpConnector(Connector):
    """Connector for Ministry of Justice Scientific Judicial Portal (public section)."""

    name = "ksa_sjp"
    jurisdiction = "KSA"
    source_name = "Scientific Judicial Portal"

    _failure_reasons: list[str]
    _auth_warning_logged: bool

    def __init__(self, http: "HttpClient", out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []
        self._auth_warning_logged = False

    def list_items(self, limit: int) -> list[SourceItem]:
        if limit < 1:
            return []

        seen_urls: set[str] = set()
        items: list[SourceItem] = []
        public_count = 0

        for page_url in SJP_URLS:
            if len(items) >= limit:
                break
            try:
                html = self.http.get(page_url)
                html_text = html.decode("utf-8", errors="replace")
                soup = BeautifulSoup(html, "html.parser")

                if _looks_like_auth_wall(soup, html_text):
                    if not self._auth_warning_logged:
                        logger.warning(
                            "SJP: authenticated content unavailable. "
                            "Scraping public circulars only."
                        )
                        self._auth_warning_logged = True
                        self._failure_reasons.append("auth_required")
                    continue

                for a in soup.find_all("a", href=True):
                    if len(items) >= limit:
                        break
                    href = str(a["href"])
                    full_url = urljoin(SJP_BASE, href)

                    if full_url in seen_urls:
                        continue

                    is_circular = any(
                        kw in href.lower()
                        for kw in ["circular", "detail", "content", "publish", "تعميم"]
                    )
                    if not is_circular:
                        continue

                    title = a.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    seen_urls.add(full_url)
                    public_count += 1

                    # Try to find date near the link
                    parent = a.parent
                    date_text = ""
                    if parent:
                        for cls in ["date", "time", "meta"]:
                            el = parent.find(class_=re.compile(cls, re.I))
                            if el:
                                date_text = el.get_text(strip=True)
                                break

                    # Try to find reference number
                    ref_number = ""
                    if parent:
                        text = parent.get_text()
                        ref_match = re.search(r"(\d{3,}/\d+|\d+-\d+-\d+)", text)
                        if ref_match:
                            ref_number = ref_match.group(1)

                    items.append(
                        SourceItem(
                            source_url=full_url,
                            meta={
                                "connector": self.name,
                                "title": title,
                                "published_at": date_text,
                                "ref_number": ref_number,
                                "importance": "high",
                            },
                        )
                    )

            except Exception as e:
                logger.warning("SJP page fetch failed for %s: %s", page_url, e)
                self._failure_reasons.append(f"page_fetch_failed: {type(e).__name__}")

        if self._auth_warning_logged:
            logger.info(
                "SJP: authenticated content unavailable. Scraped %d public circulars only.",
                public_count,
            )

        logger.info("SJP: discovered %d public items", len(items))
        return items[:limit]

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        logger.info("SJP: fetching circular %s", item.source_url)

        try:
            html = self.http.get(item.source_url)
        except Exception as e:
            logger.warning("SJP circular fetch failed: %s", e)
            html = b""
            self._failure_reasons.append(f"detail_fetch_failed: {type(e).__name__}")

        sha256 = hashlib.sha256(html or b"empty").hexdigest()
        artifact_path = str(self.out_dir / f"{sha256}.html")
        if html:
            artifact_path, sha256 = save_artifact(self.out_dir, html, "html")

        title_ar = None
        if html:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for tag in ["h1", "h2", "h3"]:
                    el = soup.find(tag)
                    if el:
                        text = el.get_text(strip=True)
                        if text and any("\u0600" <= c <= "\u06FF" for c in text):
                            title_ar = text
                            break
            except Exception:
                pass

        meta = item.meta or {}
        title = meta.get("title", "")
        if not title_ar and title and any("\u0600" <= c <= "\u06FF" for c in title):
            title_ar = title

        return ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=title_ar,
            title_en=title if title and not any("\u0600" <= c <= "\u06FF" for c in title) else None,
            instrument_type_guess="circular",
            published_at_guess=_parse_date(meta.get("published_at", "")),
            raw_artifact_path=artifact_path,
            raw_sha256=sha256,
        )

    def get_failure_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for reason in self._failure_reasons:
            cat = reason.split(":")[0] if ":" in reason else reason
            summary[cat] = summary.get(cat, 0) + 1
        return summary
