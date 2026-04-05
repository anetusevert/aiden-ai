"""Search global legal corpus tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.services.global_legal_retrieval_service import (
            GlobalLegalRetrievalService,
            GlobalLegalSearchFilters,
            PolicyFilters,
        )

        db = context["db"]
        service = GlobalLegalRetrievalService(db)

        jurisdiction = params.get("jurisdiction")
        filters = GlobalLegalSearchFilters()
        if jurisdiction and jurisdiction != "ALL":
            filters.jurisdiction = jurisdiction

        # Build permissive policy filters so the agent can search all jurisdictions
        policy_filters = PolicyFilters(
            allowed_jurisdictions=["UAE", "DIFC", "ADGM", "KSA", "OMAN", "BAHRAIN", "QATAR", "KUWAIT"],
            allowed_input_languages=["ar", "en", "mixed"],
        )

        response = await service.search_chunks(
            query=params["query"],
            limit=params.get("limit", 10),
            filters=filters,
            policy_filters=policy_filters,
        )

        results: list[dict[str, Any]] = []
        for c in response.items:
            results.append({
                "chunk_id": c.chunk_id,
                "snippet": c.snippet[:400],
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
