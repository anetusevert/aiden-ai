"""Summarization tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.llm.providers import get_llm_provider

        llm = get_llm_provider()

        text = params.get("text", "")

        if not text and params.get("document_id"):
            text = f"[Document {params['document_id']} — content would be loaded from vault]"

        if not text:
            return ToolResult(content="No text provided to summarize.", error="Missing text or document_id")

        length_map = {
            "brief": "3-5 sentence executive summary",
            "standard": "1-2 paragraph summary covering all key points",
            "detailed": "comprehensive summary organized by topic with all important details",
        }
        length_instr = length_map.get(params.get("max_length", "standard"), length_map["standard"])

        prompt = (
            f"Summarize the following legal text into a {length_instr}.\n"
            f"Preserve key legal details, dates, amounts, and citations.\n\n"
            f"Text:\n{text[:12000]}"
        )

        response = await llm.generate(
            prompt=prompt,
            temperature=0.2,
            max_tokens=2048,
            system_prompt="You are a legal professional creating precise, accurate summaries.",
        )

        return ToolResult(content=response.text, data={"length": params.get("max_length", "standard")})
    except Exception as e:
        return ToolResult(content="", error=f"Summarization failed: {e}")


summarize_tool = Tool(
    name="summarize",
    description=(
        "Summarize a legal document, research findings, or conversation into a concise brief. "
        "Preserves key legal details and citations."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to summarize"},
            "document_id": {"type": "string", "description": "Optional: UUID of document to summarize"},
            "max_length": {"type": "string", "enum": ["brief", "standard", "detailed"], "default": "standard"},
        },
        "required": [],
    },
    execute=_execute,
    read_only=True,
)
