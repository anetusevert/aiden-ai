"""Document drafting tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.llm.providers import get_llm_provider

        llm = get_llm_provider()

        lang_instr = (
            "Write in Arabic (Modern Standard Arabic / الفصحى), using proper Arabic legal terminology."
            if params.get("language") == "ar"
            else "Write in English." if params.get("language") != "bilingual"
            else "Write in bilingual format (Arabic and English)."
        )

        parties_str = ""
        if params.get("parties"):
            parties_str = f"\nParties: {', '.join(params['parties'])}"

        prompt = (
            f"Draft a {params['document_type']} for {params.get('jurisdiction', 'KSA')} jurisdiction.\n"
            f"{parties_str}\n"
            f"Key terms and requirements:\n{params['key_terms']}\n\n"
            f"{lang_instr}\n\n"
            f"Include proper legal formatting with numbered articles/sections. "
            f"Use [PLACEHOLDER] brackets for details that need to be filled in. "
            f"Note assumptions at the end."
        )

        response = await llm.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
            system_prompt="You are a senior legal drafter specializing in GCC commercial law.",
        )

        return ToolResult(
            content=response.text,
            data={"document_type": params["document_type"], "jurisdiction": params.get("jurisdiction", "KSA")},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Document drafting failed: {e}")


document_draft_tool = Tool(
    name="draft_document",
    description=(
        "Draft a legal document from scratch. Supports NDAs, employment agreements, SPAs, "
        "MOUs, board resolutions, legal memos, and other document types."
    ),
    parameters={
        "type": "object",
        "properties": {
            "document_type": {"type": "string", "description": "Type of document (NDA, Employment Agreement, SPA, MOU, Board Resolution, Legal Memo)"},
            "jurisdiction": {"type": "string", "default": "KSA"},
            "parties": {"type": "array", "items": {"type": "string"}},
            "key_terms": {"type": "string", "description": "Key commercial terms and requirements"},
            "language": {"type": "string", "enum": ["en", "ar", "bilingual"], "default": "en"},
        },
        "required": ["document_type", "key_terms"],
    },
    execute=_execute,
    read_only=False,
    requires_confirmation=True,
    risk_level="medium",
)
