"""KSA Ministry of Investment (MISA) connector — HTML scraper for business law.

Scrapes the MISA news and regulations pages for investment-law-relevant items.
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

MISA_NEWS_URL = "https://www.misa.gov.sa/en/news"
MISA_REGS_URL = "https://www.misa.gov.sa/en/regulations"
MISA_BASE = "https://www.misa.gov.sa"

RELEVANCE_RE = re.compile(
    r"\b(regulation|license|foreign investment|FDI|Vision 2030|investor"
    r"|compliance|incentive|reform|framework|policy)\b",
    re.IGNORECASE,
)


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


def _scrape_listing(http: "HttpClient", url: str, base: str) -> list[dict]:
    """Scrape a MISA listing page and return raw card data."""
    results: list[dict] = []
    try:
        html = http.get(url)
        soup = BeautifulSoup(html, "html.parser")

        cards = (
            soup.select("article")
            or soup.select(".news-item")
            or soup.select(".card")
            or soup.select("[class*='news']")
            or soup.select("[class*='item']")
        )

        if not cards:
            for a in soup.find_all("a", href=True):
                href = str(a["href"])
                if ("/news/" in href or "/regulations/" in href) and len(a.get_text(strip=True)) > 10:
                    results.append({
                        "url": urljoin(base, href),
                        "title": a.get_text(strip=True),
                        "summary": "",
                        "date": "",
                        "image": None,
                    })
            return results

        for card in cards:
            link_el = card.find("a", href=True)
            if not link_el:
                continue
            full_url = urljoin(base, str(link_el["href"]))

            title = ""
            for tag in ["h2", "h3", "h4", "h5"]:
                el = card.find(tag)
                if el:
                    title = el.get_text(strip=True)
                    break
            if not title:
                title = link_el.get_text(strip=True)

            date_text = ""
            for cls in ["date", "time", "meta"]:
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
                    img = urljoin(base, img)

            results.append({
                "url": full_url,
                "title": title,
                "summary": summary,
                "date": date_text,
                "image": img,
            })
    except Exception as e:
        logger.warning("MISA listing fetch failed for %s: %s", url, e)

    return results


class KsaMisaConnector(Connector):
    """Connector for Ministry of Investment news and regulations."""

    name = "ksa_misa"
    jurisdiction = "KSA"
    source_name = "Ministry of Investment"

    _failure_reasons: list[str]

    def __init__(self, http: "HttpClient", out_dir: Path) -> None:
        super().__init__(http, out_dir)
        self._failure_reasons = []

    def list_items(self, limit: int) -> list[SourceItem]:
        if limit < 1:
            return []

        all_cards: list[dict] = []
        for url in [MISA_NEWS_URL, MISA_REGS_URL]:
            all_cards.extend(_scrape_listing(self.http, url, MISA_BASE))

        seen: set[str] = set()
        items: list[SourceItem] = []
        for card in all_cards:
            if len(items) >= limit:
                break
            url = card["url"]
            if url in seen:
                continue
            seen.add(url)

            text = f"{card['title']} {card['summary']}"
            if not RELEVANCE_RE.search(text):
                continue

            importance = "normal"
            if re.search(r"\b(regulation|license)\b", text, re.I):
                importance = "high"

            items.append(
                SourceItem(
                    source_url=url,
                    meta={
                        "connector": self.name,
                        "title": card["title"],
                        "summary": card["summary"],
                        "published_at": card["date"],
                        "image_url": card["image"],
                        "importance": importance,
                    },
                )
            )

        logger.info("MISA: discovered %d relevant items", len(items))
        return items

    def fetch_and_parse(self, item: SourceItem) -> ParsedRecord:
        logger.info("MISA: fetching %s", item.source_url)

        try:
            html = self.http.get(item.source_url)
        except Exception as e:
            logger.warning("MISA article fetch failed: %s", e)
            html = b""
            self._failure_reasons.append(f"article_fetch_failed: {type(e).__name__}")

        sha256 = hashlib.sha256(html or b"empty").hexdigest()
        artifact_path = str(self.out_dir / f"{sha256}.html")
        if html:
            artifact_path, sha256 = save_artifact(self.out_dir, html, "html")

        meta = item.meta or {}
        return ParsedRecord(
            jurisdiction=self.jurisdiction,
            source_name=self.source_name,
            source_url=item.source_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            title_ar=None,
            title_en=meta.get("title"),
            instrument_type_guess="business_law",
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
