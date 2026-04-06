"""Knowledge base tools for Amin."""

import logging
from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult

logger = logging.getLogger(__name__)


async def _search_wiki_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from sqlalchemy import or_, select
        from src.models.wiki import WikiArticle

        db = context["db"]
        workspace_id = context["workspace_id"]
        query = params.get("query", "").strip()

        if not query:
            return ToolResult(content="", error="Search query is required.")

        pattern = f"%{query}%"
        stmt = (
            select(WikiArticle)
            .where(
                WikiArticle.workspace_id == workspace_id,
                or_(
                    WikiArticle.title.ilike(pattern),
                    WikiArticle.body.ilike(pattern),
                ),
            )
            .order_by(WikiArticle.updated_at.desc())
            .limit(10)
        )

        result = await db.execute(stmt)
        articles = result.scalars().all()

        if not articles:
            return ToolResult(content=f"No knowledge base articles found for '{query}'.")

        lines = [f"Found {len(articles)} article(s):\n"]
        for a in articles:
            snippet = (a.body or "")[:150].replace("\n", " ")
            lines.append(f"- **{a.title}** — {snippet}… [ID: {a.id}]")

        return ToolResult(content="\n".join(lines), data={"count": len(articles)})
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
