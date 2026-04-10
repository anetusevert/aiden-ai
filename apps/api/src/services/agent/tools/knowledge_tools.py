"""Knowledge base tools for Amin."""

import logging
from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult

logger = logging.getLogger(__name__)


async def _search_wiki_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from sqlalchemy import or_, select
        from src.models.wiki import WikiPage

        db = context["db"]
        query = params.get("query", "").strip()

        if not query:
            return ToolResult(content="", error="Search query is required.")

        pattern = f"%{query}%"
        stmt = (
            select(WikiPage)
            .where(
                or_(
                    WikiPage.title.ilike(pattern),
                    WikiPage.summary.ilike(pattern),
                    WikiPage.content_md.ilike(pattern),
                ),
            )
            .order_by(WikiPage.updated_at.desc())
            .limit(10)
        )

        result = await db.execute(stmt)
        pages = result.scalars().all()

        if not pages:
            return ToolResult(content=f"No knowledge base articles found for '{query}'.")

        lines = [f"Found {len(pages)} article(s):\n"]
        for p in pages:
            snippet = (p.content_md or "")[:150].replace("\n", " ")
            jurisdiction = f" [{p.jurisdiction}]" if p.jurisdiction else ""
            lines.append(f"- **{p.title}**{jurisdiction} — {snippet}… [slug: {p.slug}]")

        return ToolResult(content="\n".join(lines), data={"count": len(pages)})
    except ImportError:
        return ToolResult(content="Knowledge base module not available yet.")
    except Exception as e:
        return ToolResult(content="", error=f"Wiki search failed: {e}")


search_wiki_tool = Tool(
    name="search_knowledge_base",
    description=(
        "Search the internal knowledge base / wiki for articles, policies, "
        "precedents, and how-to guides. Use when the lawyer asks about internal procedures, "
        "firm policies, or standard workflows."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term or topic to find in the knowledge base",
            },
        },
        "required": ["query"],
    },
    execute=_search_wiki_execute,
    read_only=True,
)
