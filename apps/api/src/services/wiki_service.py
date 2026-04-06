"""Wiki service — core engine for the Amin Legal Wiki.

All wiki operations (ingest, query, lint, rebuild) flow through this service.
It orchestrates GPT analysis, page creation/updates, link management, and
index maintenance.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm import LLMProvider, get_llm_provider
from src.models.wiki import WikiIndex, WikiLink, WikiLog, WikiPage

logger = logging.getLogger(__name__)


# ── Result types ────────────────────────────────────────────────────────


@dataclass
class WikiPageResult:
    """Summary of a single page that was created or updated."""

    slug: str
    title: str
    action: str  # "created" | "updated"
    category: str
    jurisdiction: str | None
    version: int


@dataclass
class WikiIngestResult:
    """Result of a full ingest operation."""

    primary_page: WikiPageResult
    related_pages: list[WikiPageResult] = field(default_factory=list)
    links_created: int = 0
    contradictions: list[str] = field(default_factory=list)
    log_id: str | None = None


# ── Prompts ─────────────────────────────────────────────────────────────

_ANALYSIS_SYSTEM = """\
You are Amin, a GCC legal AI. You are maintaining a legal wiki — a persistent,
compounding knowledge base covering laws, regulations, concepts, entities,
cases, and synthesised research across all GCC jurisdictions.

You will be given a new source document. Analyse it and determine:
1. What is the single best wiki page title and slug for the primary page to
   create or update? (slug format: lowercase-kebab, e.g. "pdpl-data-privacy-law")
2. What category does this belong to?
   Valid categories: law, regulation, concept, entity, case, synthesis, research
3. What jurisdiction does this cover?
   Valid jurisdictions: UAE, KSA, QATAR, BAHRAIN, OMAN, KUWAIT, GCC (or null)
4. A 1-2 sentence summary of this source for the wiki index.
5. What existing wiki pages should be updated or linked to?
   Look at the wiki index provided and identify pages that relate to this source.
6. Are there any contradictions with information already in the wiki?

Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "primary_page": {
    "title": "string",
    "slug": "string",
    "category": "string",
    "jurisdiction": "string or null",
    "summary": "string"
  },
  "related_page_updates": [
    {
      "slug": "string",
      "reason": "string"
    }
  ],
  "contradictions": ["string"]
}"""

_WRITE_PAGE_SYSTEM = """\
You are Amin, a GCC legal AI. Write a comprehensive wiki page in markdown.

FORMAT REQUIREMENTS:
- Start with a level-1 heading: # {title}
- Include a "## Overview" section with a concise summary
- Use structured sections (## Key Provisions, ## Applicability, ## Enforcement, etc.)
- Use bullet points for lists of provisions, requirements, penalties
- Where relevant, note the jurisdiction and effective dates
- Link to related wiki pages using [[slug]] syntax (e.g. [[pdpl-data-privacy-law]])
- End with a "## Sources" section listing the source documents used
- Be authoritative, precise, and citation-aware
- Write in English unless the source is Arabic-only

Keep the page focused and well-structured. Aim for 500-2000 words depending
on the complexity of the topic."""

_UPDATE_PAGE_SYSTEM = """\
You are Amin, a GCC legal AI. You are updating an existing wiki page with
new information from a recently ingested source.

You will receive:
1. The current wiki page content (markdown)
2. The new source material

RULES:
- Preserve the existing structure and information
- Integrate the new information into the appropriate sections
- If information contradicts existing content, note the contradiction clearly
  with a > **Contradiction:** callout block
- Add new sections if needed for wholly new topics
- Update the ## Sources section to include the new source
- Maintain [[slug]] links to related pages
- Do NOT remove existing content unless it is factually superseded

Return the complete updated markdown page."""


class WikiService:
    """Core wiki engine. All wiki operations go through this service."""

    def __init__(self, db: AsyncSession, llm: LLMProvider | None = None):
        self.db = db
        self.llm = llm or get_llm_provider()

    # ── PUBLIC API ──────────────────────────────────────────────────────

    async def ingest_source(
        self,
        source_text: str,
        source_title: str,
        source_type: str,
        org_id: str | None,
        user_id: str,
        metadata: dict | None = None,
    ) -> WikiIngestResult:
        """Ingest a source document into the wiki.

        Steps:
        1. Load existing wiki index for context
        2. Ask GPT to analyse the source and produce a plan
        3. Execute the plan (create/update pages, links)
        4. Rebuild the wiki index
        5. Log the operation

        Args:
            source_text: Full text content of the source document
            source_title: Human-readable title of the source
            source_type: One of scraped_law, uploaded_document, research_result, workflow_output
            org_id: Organisation ID (None for global wiki)
            user_id: ID of the user triggering the ingest
            metadata: Optional extra metadata dict

        Returns:
            WikiIngestResult with details of what was created/updated
        """
        metadata = metadata or {}

        # Step 1 — Load existing wiki index
        wiki_index_text = await self._load_index_text(org_id)

        # Step 2 — Analyse the source with GPT
        plan = await self._analyse_source(
            source_text=source_text,
            source_title=source_title,
            source_type=source_type,
            wiki_index_text=wiki_index_text,
        )

        # Step 3 — Execute the plan
        primary = plan.get("primary_page", {})
        related_updates = plan.get("related_page_updates", [])
        contradictions = plan.get("contradictions", [])

        # Create or update the primary page
        primary_result = await self._upsert_page(
            slug=primary.get("slug", self._slugify(source_title)),
            title=primary.get("title", source_title),
            category=primary.get("category", "research"),
            jurisdiction=primary.get("jurisdiction"),
            summary=primary.get("summary", ""),
            source_text=source_text,
            source_title=source_title,
            org_id=org_id,
            created_by_tool=f"wiki_ingest:{source_type}",
            source_doc_id=metadata.get("document_id") or metadata.get("source_id"),
        )

        # Process related page updates (create links)
        related_results: list[WikiPageResult] = []
        links_created = 0
        for rel in related_updates[:10]:  # cap at 10 related pages
            rel_slug = rel.get("slug", "")
            rel_reason = rel.get("reason", "")
            if not rel_slug:
                continue

            existing = await self._get_page_by_slug(rel_slug, org_id)
            if existing:
                link_created = await self._ensure_link(
                    from_slug=primary_result.slug,
                    to_slug=rel_slug,
                    link_text=rel_slug,
                    context=rel_reason,
                    org_id=org_id,
                )
                if link_created:
                    links_created += 1

        # Mark contradictions on the page if any
        if contradictions:
            primary_page = await self._get_page_by_slug(primary_result.slug, org_id)
            if primary_page:
                primary_page.has_contradictions = True
                self.db.add(primary_page)

        # Step 4 — Rebuild the wiki index
        await self._rebuild_index(org_id)

        # Step 5 — Log the operation
        all_slugs = [primary_result.slug] + [r.slug for r in related_results]
        log_entry = WikiLog(
            id=str(uuid4()),
            org_id=org_id,
            operation="ingest",
            page_slug=primary_result.slug,
            source_description=f"{source_type}: {source_title}",
            amin_summary=(
                f"Ingested '{source_title}' → "
                f"{'created' if primary_result.action == 'created' else 'updated'} "
                f"wiki page '{primary_result.title}'. "
                f"{links_created} links created. "
                f"{len(contradictions)} contradictions noted."
            ),
            pages_affected=all_slugs,
        )
        self.db.add(log_entry)
        await self.db.flush()

        await self.db.commit()

        return WikiIngestResult(
            primary_page=primary_result,
            related_pages=related_results,
            links_created=links_created,
            contradictions=contradictions,
            log_id=log_entry.id,
        )

    async def get_page(self, slug: str, org_id: str | None) -> WikiPage | None:
        """Get a wiki page by slug within an org scope."""
        return await self._get_page_by_slug(slug, org_id)

    async def search_pages(
        self,
        query: str,
        org_id: str | None,
        limit: int = 10,
    ) -> list[WikiPage]:
        """Search wiki pages by title/content (simple ILIKE for now)."""
        pattern = f"%{query}%"
        stmt = (
            select(WikiPage)
            .where(WikiPage.org_id == org_id)
            .where(
                (WikiPage.title.ilike(pattern))
                | (WikiPage.content_md.ilike(pattern))
                | (WikiPage.summary.ilike(pattern))
            )
            .order_by(WikiPage.updated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_index(self, org_id: str | None) -> WikiIndex | None:
        """Get the wiki index for an org (or global)."""
        stmt = select(WikiIndex).where(WikiIndex.org_id == org_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def rebuild_index(self, org_id: str | None) -> WikiIndex:
        """Public wrapper for index rebuild."""
        return await self._rebuild_index(org_id)

    # ── PRIVATE HELPERS ─────────────────────────────────────────────────

    async def _load_index_text(self, org_id: str | None) -> str:
        """Load the wiki index markdown for GPT context."""
        idx = await self.get_index(org_id)
        if idx and idx.content_md:
            return idx.content_md
        return "(The wiki is currently empty. No pages exist yet.)"

    async def _analyse_source(
        self,
        source_text: str,
        source_title: str,
        source_type: str,
        wiki_index_text: str,
    ) -> dict:
        """Ask GPT to analyse the source and produce an ingest plan."""
        user_prompt = (
            f"## Source Document\n"
            f"**Title:** {source_title}\n"
            f"**Type:** {source_type}\n\n"
            f"### Content\n{source_text[:12000]}\n\n"
            f"---\n\n"
            f"## Current Wiki Index\n{wiki_index_text[:6000]}\n\n"
            f"---\n\n"
            f"Analyse this source and return your JSON plan."
        )

        response = await self.llm.generate(
            user_prompt,
            system_prompt=_ANALYSIS_SYSTEM,
            temperature=0.0,
            max_tokens=2048,
        )

        return self._parse_json_response(response.text)

    async def _upsert_page(
        self,
        slug: str,
        title: str,
        category: str,
        jurisdiction: str | None,
        summary: str,
        source_text: str,
        source_title: str,
        org_id: str | None,
        created_by_tool: str,
        source_doc_id: str | None = None,
    ) -> WikiPageResult:
        """Create a new wiki page or update an existing one."""
        existing = await self._get_page_by_slug(slug, org_id)

        if existing:
            # Update existing page
            new_content = await self._generate_page_update(
                existing_content=existing.content_md,
                source_text=source_text,
                source_title=source_title,
            )
            existing.content_md = new_content
            existing.summary = summary or existing.summary
            existing.version += 1
            existing.is_stale = False
            if source_doc_id:
                doc_ids = list(existing.source_doc_ids or [])
                if source_doc_id not in doc_ids:
                    doc_ids.append(source_doc_id)
                existing.source_doc_ids = doc_ids
            self.db.add(existing)
            await self.db.flush()

            return WikiPageResult(
                slug=existing.slug,
                title=existing.title,
                action="updated",
                category=existing.category,
                jurisdiction=existing.jurisdiction,
                version=existing.version,
            )
        else:
            # Create new page
            new_content = await self._generate_new_page(
                title=title,
                category=category,
                jurisdiction=jurisdiction,
                source_text=source_text,
                source_title=source_title,
            )
            doc_ids = [source_doc_id] if source_doc_id else []
            page = WikiPage(
                id=str(uuid4()),
                org_id=org_id,
                slug=slug,
                title=title,
                category=category,
                content_md=new_content,
                summary=summary,
                jurisdiction=jurisdiction,
                source_doc_ids=doc_ids,
                created_by_tool=created_by_tool,
            )
            self.db.add(page)
            await self.db.flush()

            return WikiPageResult(
                slug=page.slug,
                title=page.title,
                action="created",
                category=page.category,
                jurisdiction=page.jurisdiction,
                version=1,
            )

    async def _generate_new_page(
        self,
        title: str,
        category: str,
        jurisdiction: str | None,
        source_text: str,
        source_title: str,
    ) -> str:
        """Ask GPT to write a full new wiki page from the source."""
        user_prompt = (
            f"Write a wiki page with this information:\n\n"
            f"**Title:** {title}\n"
            f"**Category:** {category}\n"
            f"**Jurisdiction:** {jurisdiction or 'GCC (general)'}\n\n"
            f"### Source: {source_title}\n"
            f"{source_text[:12000]}\n"
        )

        response = await self.llm.generate(
            user_prompt,
            system_prompt=_WRITE_PAGE_SYSTEM,
            temperature=0.1,
            max_tokens=4096,
        )
        return response.text

    async def _generate_page_update(
        self,
        existing_content: str,
        source_text: str,
        source_title: str,
    ) -> str:
        """Ask GPT to merge new source material into an existing page."""
        user_prompt = (
            f"## Current Wiki Page\n{existing_content[:8000]}\n\n"
            f"---\n\n"
            f"## New Source: {source_title}\n{source_text[:8000]}\n\n"
            f"---\n\n"
            f"Update the wiki page by integrating the new source material."
        )

        response = await self.llm.generate(
            user_prompt,
            system_prompt=_UPDATE_PAGE_SYSTEM,
            temperature=0.1,
            max_tokens=4096,
        )
        return response.text

    async def _get_page_by_slug(
        self, slug: str, org_id: str | None
    ) -> WikiPage | None:
        """Fetch a wiki page by slug + org scope."""
        stmt = select(WikiPage).where(
            WikiPage.slug == slug,
            WikiPage.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _ensure_link(
        self,
        from_slug: str,
        to_slug: str,
        link_text: str,
        context: str,
        org_id: str | None,
    ) -> bool:
        """Create a link between two pages if it doesn't already exist.

        Returns True if a new link was created, False if it already existed
        or one of the pages doesn't exist.
        """
        from_page = await self._get_page_by_slug(from_slug, org_id)
        to_page = await self._get_page_by_slug(to_slug, org_id)
        if not from_page or not to_page:
            return False

        # Check for existing link
        stmt = select(WikiLink).where(
            WikiLink.from_page_id == from_page.id,
            WikiLink.to_page_id == to_page.id,
        )
        existing = await self.db.execute(stmt)
        if existing.scalar_one_or_none():
            return False

        link = WikiLink(
            id=str(uuid4()),
            from_page_id=from_page.id,
            to_page_id=to_page.id,
            link_text=link_text,
            context=context,
        )
        self.db.add(link)

        # Update denormalised inbound_link_count
        to_page.inbound_link_count = (to_page.inbound_link_count or 0) + 1
        self.db.add(to_page)

        await self.db.flush()
        return True

    async def _rebuild_index(self, org_id: str | None) -> WikiIndex:
        """Rebuild the wiki index for a given org (or global)."""
        stmt = (
            select(WikiPage)
            .where(WikiPage.org_id == org_id)
            .order_by(WikiPage.category, WikiPage.title)
        )
        result = await self.db.execute(stmt)
        pages = list(result.scalars().all())

        lines = ["# Wiki Index", ""]
        current_category = None
        for page in pages:
            if page.category != current_category:
                current_category = page.category
                lines.append(f"## {current_category.title()}")
                lines.append("")
            stale_marker = " [STALE]" if page.is_stale else ""
            contradiction_marker = " [CONTRADICTIONS]" if page.has_contradictions else ""
            lines.append(
                f"- **[[{page.slug}]]** — {page.title}{stale_marker}{contradiction_marker}"
            )
            lines.append(f"  {page.summary}")
            lines.append("")

        content_md = "\n".join(lines)

        # Upsert the index row
        idx = await self.get_index(org_id)
        if idx:
            idx.content_md = content_md
            idx.page_count = len(pages)
            idx.last_rebuilt_at = datetime.now(timezone.utc)
            self.db.add(idx)
        else:
            idx = WikiIndex(
                id=str(uuid4()),
                org_id=org_id,
                content_md=content_md,
                page_count=len(pages),
                last_rebuilt_at=datetime.now(timezone.utc),
            )
            self.db.add(idx)

        await self.db.flush()
        return idx

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert a title to a URL-safe slug."""
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug.strip("-")[:300]

    @staticmethod
    def _parse_json_response(text: str) -> dict:
        """Extract and parse JSON from an LLM response.

        Handles responses that may be wrapped in markdown code fences.
        """
        cleaned = text.strip()

        # Strip markdown fences
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Drop first and last lines (the fences)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM JSON response, using fallback plan")
            return {
                "primary_page": {
                    "title": "Untitled",
                    "slug": "untitled",
                    "category": "research",
                    "jurisdiction": None,
                    "summary": "Could not parse LLM analysis.",
                },
                "related_page_updates": [],
                "contradictions": [],
            }
