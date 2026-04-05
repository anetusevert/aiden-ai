"""Amin agent tools — wrappers around existing services."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.agent.tool_registry import ToolRegistry


def register_all_tools(registry: ToolRegistry) -> None:
    """Register all built-in Amin tools."""
    from src.services.agent.tools.clause_redlines import clause_redlines_tool
    from src.services.agent.tools.contract_review import contract_review_tool
    from src.services.agent.tools.document_draft import document_draft_tool
    from src.services.agent.tools.document_search import document_search_tool
    from src.services.agent.tools.legal_corpus_search import legal_corpus_search_tool
    from src.services.agent.tools.legal_research import legal_research_tool
    from src.services.agent.tools.office_tools import (
        create_document_tool,
        edit_document_tool,
        get_document_state_tool,
        navigate_document_tool,
        read_document_tool,
    )
    from src.services.agent.tools.summarize import summarize_tool
    from src.services.agent.tools.translate import translate_tool

    for tool in [
        document_search_tool,
        legal_corpus_search_tool,
        legal_research_tool,
        contract_review_tool,
        clause_redlines_tool,
        document_draft_tool,
        create_document_tool,
        edit_document_tool,
        read_document_tool,
        navigate_document_tool,
        get_document_state_tool,
        translate_tool,
        summarize_tool,
    ]:
        registry.register(tool)
