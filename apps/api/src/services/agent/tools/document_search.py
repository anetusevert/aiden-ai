"""Search workspace documents tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.services.retrieval_service import RetrievalService, SearchFilters

        db = context["db"]
        service = RetrievalService()
        chunks = await service.hybrid_search(
            db=db,
            tenant_id=context["tenant_id"],
            workspace_id=context["workspace_id"],
            query=params["query"],
            limit=params.get("limit", 10),
            filters=SearchFilters(),
        )

        results = []
        for c in chunks:
            results.append({
                "chunk_id": c.chunk_id,
                "snippet": c.text[:400],
                "document_title": c.document_title,
                "page_start": c.page_start,
                "score": round(c.final_score, 3),
            })

        content = f"Found {len(results)} relevant chunks.\n"
        for i, r in enumerate(results[:5], 1):
            content += f"\n[{i}] **{r['document_title']}** (score: {r['score']})\n{r['snippet'][:200]}...\n"

        return ToolResult(content=content, data={"results": results})
    except Exception as e:
        return ToolResult(content="", error=f"Search failed: {e}")


document_search_tool = Tool(
    name="search_documents",
    description=(
        "Search the lawyer's workspace documents using semantic and keyword search. "
        "Use this to find relevant documents, clauses, or precedents in the lawyer's own files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["query"],
    },
    execute=_execute,
    read_only=True,
)
