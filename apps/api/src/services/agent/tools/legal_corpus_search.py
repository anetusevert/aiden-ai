"""Search global legal corpus tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.services.global_legal_retrieval_service import GlobalLegalRetrievalService

        db = context["db"]
        service = GlobalLegalRetrievalService()
        chunks = await service.hybrid_search(
            db=db,
            query=params["query"],
            limit=params.get("limit", 10),
            jurisdiction=params.get("jurisdiction") if params.get("jurisdiction") != "ALL" else None,
        )

        results = []
        for c in chunks:
            results.append({
                "chunk_id": c.chunk_id,
                "snippet": c.text[:400],
                "instrument_title": c.instrument_title,
                "jurisdiction": c.jurisdiction,
                "instrument_type": c.instrument_type,
                "score": round(c.final_score, 3),
            })

        content = f"Found {len(results)} results in the legal corpus.\n"
        for i, r in enumerate(results[:5], 1):
            content += f"\n[{i}] **{r['instrument_title']}** ({r['jurisdiction']}, {r['instrument_type']})\n{r['snippet'][:200]}...\n"

        return ToolResult(content=content, data={"results": results})
    except Exception as e:
        return ToolResult(content="", error=f"Legal corpus search failed: {e}")


legal_corpus_search_tool = Tool(
    name="search_legal_corpus",
    description=(
        "Search the global legal corpus for laws, regulations, articles, and regulatory "
        "guidance across KSA and GCC jurisdictions. Always use this before making legal assertions."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "jurisdiction": {
                "type": "string",
                "enum": ["KSA", "UAE", "QAT", "BHR", "KWT", "OMN", "ALL"],
                "default": "ALL",
            },
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["query"],
    },
    execute=_execute,
    read_only=True,
)
