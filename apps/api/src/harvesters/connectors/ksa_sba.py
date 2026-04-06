"""KSA Saudi Bar Association (SBA) connector — HTML scraper for professional news.

Scrapes the SBA news listing page for articles directly relevant to
practicing lawyers in Saudi Arabia.
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

SBA_EN_URL = "https://www.sba.gov.sa/en/news"
SBA_AR_URL = "https://www.sba.gov.sa/ar/news"
SBA_BASE = "https://www.sba.gov.sa"

_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"),
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{1,2})\s+(\w+)\s+(\d{4})"),
]


def _parse_date(text: str) -> str | None:
    m = _DATE_PATTERNS[0].search(text)
    if m:
        day, month, year = m.groups()
        try:
            dt = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = _DATE_PATTERNS[1].search(text)
    if m:
        year, month, day = m.groups()
        try:
            dt = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


class KsaSbaConnector(Connector):
    """Connector for Saudi Bar Association news (professional updates)."""

    name = "ksa_sba"
    jurisdiction = "KSA"
    source_name = "Saudi Bar Association"

    _failure_reasons: list[str]

    def __init__(self, http: "HttpClient", out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []

    def list_items(self, limit: int) -> list[SourceItem]:
        if limit < 1:
            return []

        items: list[SourceItem] = []

        try:
            html = self.http.get(SBA_EN_URL)
            soup = BeautifulSoup(html, "html.parser")

            cards = (
                soup.select("article")
                or soup.select(".news-item")
                or soup.select(".card")
                or soup.select("[class*='news']")
            )

            if not cards:
                all_links = soup.find_all("a", href=True)
                for a in all_links:
                    href = str(a["href"])
                    if "/news/" in href and href != "/en/news" and href != "/ar/news":
                        title = a.get_text(strip=True)
                        if title and len(title) > 10:
                            full_url = urljoin(SBA_BASE, href)
                            items.append(
                                SourceItem(
                                    source_url=full_url,
                                    meta={
                                        "connector": self.name,
                                        "title": title,
                                        "importance": "high",
                                    },
                                )
                            )
                            if len(items) >= limit:
                                break
            else:
                for card in cards[:limit]:
                    link_el = card.find("a", href=True)
                    if not link_el:
                        continue
                    href = str(link_el["href"])
                    full_url = urljoin(SBA_BASE, href)

                    title = ""
                    for tag in ["h2", "h3", "h4", "h5", ".title", ".card-title"]:
                        el = card.select_one(tag) if "." in tag else card.find(tag)
                        if el:
                            title = el.get_text(strip=True)
                            break
                    if not title:
                        title = link_el.get_text(strip=True)
                    if not title:
                        continue

                    date_text = ""
                    for cls in ["date", "time", "meta", "published"]:
                        el = card.find(class_=re.compile(cls, re.I))
                        if el:
                            date_text = el.get_text(strip=True)
                            break
                    time_el = card.find("time")
                    if time_el:
                        date_text = time_el.get("datetime", "") or time_el.get_text(strip=True)

                    summary = ""
                    p = card.find("p")
                    if p:
                        summary = p.get_text(strip=True)[:500]

                    img = None
                    img_el = card.find("img")
                    if img_el:
                        img = img_el.get("src") or img_el.get("data-src")
                        if img:
                            img = urljoin(SBA_BASE, img)

                    items.append(
                        SourceItem(
                            source_url=full_url,
                            meta={
                                "connector": self.name,
                                "title": title,
                                "summary": summary,
                                "published_at": date_text,
                                "image_url": img,
                                "importance": "high",
                            },
                        )
                    )

        except Exception as e:
            logger.warning("SBA listing fetch failed: %s", e)
            self._failure_reasons.append(f"listing_fetch_failed: {type(e).__name__}")

        logger.info("SBA: discovered %d items", len(items))
        return items[:limit]

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        logger.info("SBA: fetching article %s", item.source_url)

        try:
            html = self.http.get(item.source_url)
        except Exception as e:
            logger.warning("SBA article fetch failed: %s", e)
            html = b""
            self._failure_reasons.append(f"article_fetch_failed: {type(e).__name__}")

        sha256 = hashlib.sha256(html or b"empty").hexdigest()
        artifact_path = str(self.out_dir / f"{sha256}.html")
        if html:
            artifact_path, sha256 = save_artifact(self.out_dir, html, "html")

        title_ar = None
        try:
            ar_url = item.source_url.replace("/en/", "/ar/")
            if ar_url != item.source_url:
                ar_html = self.http.get(ar_url)
                ar_soup = BeautifulSoup(ar_html, "html.parser")
                for tag in ["h1", "h2", "h3"]:
                    el = ar_soup.find(tag)
                    if el:
                        text = el.get_text(strip=True)
                        if text and any("\u0600" <= c <= "\u06FF" for c in text):
                            title_ar = text
                            break
        except Exception:
            pass

        meta = item.meta or {}
        return ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=title_ar,
            title_en=meta.get("title"),
            instrument_type_guess="professional_notice",
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
