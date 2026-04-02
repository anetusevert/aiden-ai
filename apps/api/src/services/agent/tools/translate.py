"""Legal translation tool."""

from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult


async def _execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.llm.providers import get_llm_provider

        llm = get_llm_provider()
        target = params["target_language"]
        target_name = "English" if target == "en" else "Arabic (Modern Standard Arabic / فصحى قانونية)"

        ctx_note = ""
        if params.get("context"):
            ctx_note = f"\nLegal context: {params['context']}"

        prompt = (
            f"Translate the following legal text to {target_name}.{ctx_note}\n\n"
            f"Preserve legal terminology precisely. If a concept has no direct equivalent, "
            f"provide the closest translation with a brief note in brackets.\n\n"
            f"Text:\n{params['text']}"
        )

        response = await llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=4096,
            system_prompt="You are a professional legal translator for GCC jurisdictions.",
        )

        return ToolResult(content=response.text, data={"target_language": target})
    except Exception as e:
        return ToolResult(content="", error=f"Translation failed: {e}")


translate_tool = Tool(
    name="translate",
    description=(
        "Translate legal text between Arabic and English with legal terminology preservation. "
        "Handles formal legal Arabic (فصحى قانونية)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "target_language": {"type": "string", "enum": ["ar", "en"]},
            "context": {"type": "string", "description": "Legal context for accurate terminology"},
        },
        "required": ["text", "target_language"],
    },
    execute=_execute,
    read_only=True,
)
