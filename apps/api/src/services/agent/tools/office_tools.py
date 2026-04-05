"""Office document tools for Amin."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.dependencies.auth import RequestContext
from src.models import Tenant, User, Workspace, WorkspaceMembership
from src.services.agent.realtime import send_user_event
from src.services.agent.screen_context import get_screen_context
from src.services.agent.tool_registry import Tool, ToolResult
from src.services.office_service import (
    OfficeDocumentNotFoundError,
    OfficeService,
    answer_office_document_question,
    build_collabora_editor_url,
)
from src.services.amin_document_ops import execute_instruction


async def _build_request_context(context: dict[str, Any]) -> RequestContext:
    db = context["db"]
    user = await db.get(User, context["user_id"])
    tenant = await db.get(Tenant, context["tenant_id"])
    workspace = await db.get(Workspace, context["workspace_id"])
    membership = None
    if workspace is not None:
        membership = (
            await db.execute(
                select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace.id,
                    WorkspaceMembership.user_id == user.id,
                )
            )
        ).scalar_one_or_none()

    if user is None or tenant is None or workspace is None:
        raise ValueError("Missing tenant, user, or workspace context for office tool execution.")

    return RequestContext(
        tenant=tenant,
        user=user,
        workspace=workspace,
        membership=membership,
    )


async def _execute_create_document(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        db = context["db"]
        ctx = await _build_request_context(context)
        service = OfficeService(db)
        document = await service.create_document(
            ctx=ctx,
            title=params["title"],
            doc_type=params["doc_type"],
            template=params.get("template"),
        )

        summary = f"Created {document.doc_type.upper()} document '{document.title}'."
        if params.get("initial_content"):
            file_bytes, _content_type = await service.download_document(document)
            new_bytes, _ops, edit_summary = await execute_instruction(
                instruction=f"Populate this document with: {params['initial_content']}",
                file_bytes=file_bytes,
                doc_type=document.doc_type,
                context={"source": "create_document"},
            )
            await service.update_document_bytes(
                document,
                file_bytes=new_bytes,
                modified_by_user_id=ctx.user.id,
            )
            summary = edit_summary or summary

        token = await service.generate_wopi_token(
            document,
            user_id=ctx.user.id,
            can_write=ctx.has_role("EDITOR"),
        )
        collabora_url = build_collabora_editor_url(None, document.id, token.token)

        await send_user_event(
            ctx.user.id,
            {"type": "document_created", "docId": document.id},
        )

        return ToolResult(
            content=f"{summary} It is ready to open in the editor.",
            data={
                "doc_id": document.id,
                "title": document.title,
                "collabora_url": collabora_url,
                "summary": summary,
            },
        )
    except Exception as exc:
        return ToolResult(content="", error=f"Failed to create document: {exc}")


async def _execute_edit_document(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        db = context["db"]
        ctx = await _build_request_context(context)
        screen_context = await get_screen_context(ctx.user.id) or {}
        document_state = screen_context.get("document") or {}
        doc_id = params.get("doc_id") or document_state.get("doc_id")
        if not doc_id:
            return ToolResult(content="", error="No document is currently open, and no doc_id was provided.")

        service = OfficeService(db)
        _document, ops_applied, summary = await service.apply_amin_edit(
            ctx,
            doc_id,
            params["instruction"],
            context={"screen_context": screen_context},
        )

        if params.get("apply_immediately") and document_state.get("doc_id") == doc_id:
            await send_user_event(ctx.user.id, {"type": "collabora_reload", "docId": doc_id})

        return ToolResult(
            content=summary,
            data={"ops_applied": ops_applied, "summary": summary, "doc_id": doc_id},
        )
    except OfficeDocumentNotFoundError as exc:
        return ToolResult(content="", error=str(exc))
    except Exception as exc:
        return ToolResult(content="", error=f"Failed to edit document: {exc}")


async def _execute_read_document(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        db = context["db"]
        ctx = await _build_request_context(context)
        screen_context = await get_screen_context(ctx.user.id) or {}
        document_state = screen_context.get("document") or {}
        doc_id = params.get("doc_id") or document_state.get("doc_id")
        if not doc_id:
            return ToolResult(content="", error="No document is currently open, and no doc_id was provided.")

        service = OfficeService(db)
        document = await service.get_document(ctx, doc_id)
        answer = await answer_office_document_question(db, document, params.get("question"))
        return ToolResult(
            content=answer,
            data={
                "doc_id": document.id,
                "title": document.title,
                "metadata": document.metadata_ or {},
            },
        )
    except OfficeDocumentNotFoundError as exc:
        return ToolResult(content="", error=str(exc))
    except Exception as exc:
        return ToolResult(content="", error=f"Failed to read document: {exc}")


async def _execute_navigate_document(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        user_id = context["user_id"]
        payload = {
            "type": "collabora_navigate",
            "target_type": params["target_type"],
            "target_value": params["target_value"],
        }
        await send_user_event(user_id, payload)
        return ToolResult(
            content=f"Asked the editor to navigate to {params['target_type']} {params['target_value']}.",
            data=payload,
        )
    except Exception as exc:
        return ToolResult(content="", error=f"Failed to navigate document: {exc}")


async def _execute_get_document_state(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        payload = await get_screen_context(context["user_id"])
        if not payload:
            return ToolResult(
                content="No live screen context is available right now.",
                data={"screen_context": None},
            )
        return ToolResult(
            content="Current screen context loaded.",
            data={"screen_context": payload},
        )
    except Exception as exc:
        return ToolResult(content="", error=f"Failed to get document state: {exc}")


create_document_tool = Tool(
    name="create_document",
    description=(
        "Create a new Word document, Excel spreadsheet, or PowerPoint presentation. "
        "Amin can create from scratch or use a template."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "doc_type": {"type": "string", "enum": ["docx", "xlsx", "pptx"]},
            "template": {"type": "string"},
            "initial_content": {"type": "string"},
        },
        "required": ["title", "doc_type"],
    },
    execute=_execute_create_document,
    read_only=False,
)

edit_document_tool = Tool(
    name="edit_document",
    description=(
        "Edit the currently open document or a specific document by applying Amin's intelligence. "
        "Amin can rewrite sections, add content, format, and restructure."
    ),
    parameters={
        "type": "object",
        "properties": {
            "doc_id": {"type": "string"},
            "instruction": {"type": "string"},
            "apply_immediately": {"type": "boolean", "default": True},
        },
        "required": ["instruction"],
    },
    execute=_execute_edit_document,
    read_only=False,
)

read_document_tool = Tool(
    name="read_document",
    description=(
        "Read and understand the current document's content. Amin can summarize, "
        "extract key information, and answer questions about the document."
    ),
    parameters={
        "type": "object",
        "properties": {
            "doc_id": {"type": "string"},
            "question": {"type": "string"},
        },
    },
    execute=_execute_read_document,
    read_only=True,
)

navigate_document_tool = Tool(
    name="navigate_document",
    description=(
        "Navigate within the currently open document in Collabora. "
        "Go to a page, slide, sheet, or a search target."
    ),
    parameters={
        "type": "object",
        "properties": {
            "target_type": {"type": "string", "enum": ["page", "slide", "sheet", "search"]},
            "target_value": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "integer"},
                ]
            },
        },
        "required": ["target_type", "target_value"],
    },
    execute=_execute_navigate_document,
    read_only=False,
)

get_document_state_tool = Tool(
    name="get_document_state",
    description=(
        "Get the current state of the document the user is working on, including "
        "what they are looking at and any recent document context."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_execute_get_document_state,
    read_only=True,
)
