"""Case-centric tools for Amin — file to case, get context, set deadline."""

import logging
from datetime import date
from typing import Any

from src.services.agent.tool_registry import Tool, ToolResult

logger = logging.getLogger(__name__)


async def _get_active_case_id(context: dict[str, Any]) -> str | None:
    try:
        from src.services.agent.screen_context import get_redis_client
        redis_client = get_redis_client()
        return await redis_client.get(f"active_case:{context['user_id']}")
    except Exception:
        return None


async def _file_to_case_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.models.case import Case, CaseEvent, CaseNote

        db = context["db"]
        case_id = await _get_active_case_id(context)
        if not case_id:
            return ToolResult(content="No active case. Ask the lawyer to open a case first.")

        case = await db.get(Case, case_id)
        if not case:
            return ToolResult(content="Active case not found.")

        item_type = params.get("item_type", "note")
        content = params.get("content", "")
        title = params.get("title", "Amin action")

        if item_type == "note":
            note = CaseNote(
                case_id=case_id,
                content=content,
                is_amin_generated=True,
                created_by=None,
            )
            db.add(note)
            db.add(CaseEvent(
                case_id=case_id,
                event_type="note_added",
                title=f"Note added by Amin: {title}",
                description=content[:200],
                created_by=None,
            ))
        elif item_type == "event":
            db.add(CaseEvent(
                case_id=case_id,
                event_type="amin_action",
                title=title,
                description=content,
                created_by=None,
            ))
        elif item_type == "document":
            from src.models.case import CaseDocument
            from src.models.office import OfficeDocument

            doc = await db.get(OfficeDocument, content)
            if not doc:
                return ToolResult(content="Document not found.", error="Document ID invalid")
            from sqlalchemy import select
            existing = (await db.execute(
                select(CaseDocument).where(
                    CaseDocument.case_id == case_id,
                    CaseDocument.document_id == content,
                )
            )).scalar_one_or_none()
            if not existing:
                cd = CaseDocument(
                    case_id=case_id,
                    document_id=content,
                    attached_by=context["user_id"],
                    document_role="general",
                )
                db.add(cd)
                db.add(CaseEvent(
                    case_id=case_id,
                    event_type="document_added",
                    title=f"Document attached: {doc.title}",
                    created_by=None,
                ))

        await db.commit()
        return ToolResult(
            content=f"Filed to case: {case.title}.",
            data={"case_id": case_id, "item_type": item_type},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Failed to file to case: {e}")


async def _get_case_context_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.models.case import Case, CaseDocument, CaseEvent, CaseNote
        from src.models.client import Client
        from sqlalchemy import func, select

        db = context["db"]
        case_id = await _get_active_case_id(context)
        if not case_id:
            return ToolResult(content="No active case set.")

        case = await db.get(Case, case_id)
        if not case:
            return ToolResult(content="Active case not found.")

        client = await db.get(Client, case.client_id)
        doc_count = (await db.execute(
            select(func.count()).select_from(CaseDocument).where(CaseDocument.case_id == case_id)
        )).scalar() or 0
        note_count = (await db.execute(
            select(func.count()).select_from(CaseNote).where(CaseNote.case_id == case_id)
        )).scalar() or 0

        events_result = await db.execute(
            select(CaseEvent).where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.event_date.desc()).limit(5)
        )
        recent_events = [f"- {e.title} ({e.event_date.strftime('%d %b %Y')})" for e in events_result.scalars()]

        summary = (
            f"Case: {case.title}\n"
            f"Client: {client.display_name} ({client.client_type})\n"
            f"Practice Area: {case.practice_area} | Jurisdiction: {case.jurisdiction}\n"
            f"Status: {case.status} | Priority: {case.priority}\n"
            f"Deadline: {case.next_deadline or 'None'} — {case.next_deadline_description or ''}\n"
            f"Documents: {doc_count} | Notes: {note_count}\n"
            f"Brief: {case.amin_briefing or case.description or 'No brief'}\n\n"
            f"Recent Activity:\n" + "\n".join(recent_events or ["  No recent activity."])
        )
        return ToolResult(content=summary, data={"case_id": case_id})
    except Exception as e:
        return ToolResult(content="", error=f"Failed to get case context: {e}")


async def _set_case_deadline_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.models.case import Case, CaseEvent

        db = context["db"]
        case_id = await _get_active_case_id(context)
        if not case_id:
            return ToolResult(content="No active case set.")

        case = await db.get(Case, case_id)
        if not case:
            return ToolResult(content="Active case not found.")

        deadline_str = params.get("date", "")
        description = params.get("description", "")

        try:
            deadline_date = date.fromisoformat(deadline_str)
        except ValueError:
            return ToolResult(content="", error="Invalid date format. Use YYYY-MM-DD.")

        case.next_deadline = deadline_date
        case.next_deadline_description = description

        db.add(CaseEvent(
            case_id=case_id,
            event_type="deadline_set",
            title=f"Deadline set: {description}",
            description=f"{deadline_date.strftime('%d %B %Y')}",
            created_by=None,
        ))
        await db.commit()

        return ToolResult(
            content=f"Deadline set: {description} on {deadline_date.strftime('%d %B %Y')}. I'll keep this in mind.",
            data={"case_id": case_id, "deadline": deadline_str},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Failed to set deadline: {e}")


file_to_case_tool = Tool(
    name="file_to_case",
    description=(
        "File a document, research result, or note to the current active case. "
        "Use this whenever you complete research, create a document, or make an important "
        "finding that should be recorded against the case."
    ),
    parameters={
        "type": "object",
        "properties": {
            "item_type": {
                "type": "string",
                "enum": ["document", "note", "event"],
                "description": "Type of item to file",
            },
            "content": {
                "type": "string",
                "description": "The content to file (text for note/event, document_id for document)",
            },
            "title": {
                "type": "string",
                "description": "Brief title for the filed item",
            },
        },
        "required": ["item_type", "content", "title"],
    },
    execute=_file_to_case_execute,
    read_only=False,
)

get_case_context_tool = Tool(
    name="get_case_context",
    description=(
        "Get the full context of the current active case including client, "
        "documents, recent notes, and timeline."
    ),
    parameters={
        "type": "object",
        "properties": {},
    },
    execute=_get_case_context_execute,
    read_only=True,
)

set_case_deadline_tool = Tool(
    name="set_case_deadline",
    description="Set or update the next deadline for the current case.",
    parameters={
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Deadline date in YYYY-MM-DD format",
            },
            "description": {
                "type": "string",
                "description": "What the deadline is for (e.g. 'Statement of Claim due')",
            },
        },
        "required": ["date", "description"],
    },
    execute=_set_case_deadline_execute,
    read_only=False,
)


# ── Extended case tools ──────────────────────────────────────────────

async def _search_cases_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from sqlalchemy import or_, select
        from src.models.case import Case
        from src.models.client import Client

        db = context["db"]
        workspace_id = context["workspace_id"]
        query = params.get("query", "").strip()
        status_filter = params.get("status")

        stmt = select(Case).where(Case.workspace_id == workspace_id)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Case.title.ilike(pattern),
                    Case.case_number.ilike(pattern),
                    Case.practice_area.ilike(pattern),
                )
            )
        if status_filter:
            stmt = stmt.where(Case.status == status_filter)

        stmt = stmt.order_by(Case.updated_at.desc()).limit(20)
        result = await db.execute(stmt)
        cases = result.scalars().all()

        if not cases:
            return ToolResult(content="No cases found matching your search.")

        lines = [f"Found {len(cases)} case(s):\n"]
        for c in cases:
            lines.append(
                f"- **{c.title}** ({c.case_number or '—'}) — "
                f"Status: {c.status} | Priority: {c.priority} | "
                f"Area: {c.practice_area or '—'} [ID: {c.id}]"
            )
        return ToolResult(content="\n".join(lines), data={"count": len(cases)})
    except Exception as e:
        return ToolResult(content="", error=f"Case search failed: {e}")


async def _create_case_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.models.case import Case, CaseEvent

        db = context["db"]
        workspace_id = context["workspace_id"]

        case = Case(
            workspace_id=workspace_id,
            client_id=params["client_id"],
            title=params["title"],
            practice_area=params.get("practice_area", "General"),
            jurisdiction=params.get("jurisdiction", "KSA"),
            description=params.get("description", ""),
            priority=params.get("priority", "medium"),
        )
        db.add(case)
        await db.flush()

        db.add(CaseEvent(
            case_id=case.id,
            event_type="case_created",
            title=f"Case created: {case.title}",
            created_by=context["user_id"],
        ))
        await db.commit()
        await db.refresh(case)

        return ToolResult(
            content=f"Case '{case.title}' created successfully (ID: {case.id}).",
            data={"case_id": case.id},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Failed to create case: {e}")


async def _update_case_status_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from src.models.case import Case, CaseEvent

        db = context["db"]
        case_id = params.get("case_id", "")
        new_status = params.get("status", "")

        case = await db.get(Case, case_id)
        if not case:
            return ToolResult(content="Case not found.", error="Invalid case_id")

        old_status = case.status
        case.status = new_status
        db.add(CaseEvent(
            case_id=case_id,
            event_type="status_changed",
            title=f"Status changed from {old_status} to {new_status}",
            created_by=None,
        ))
        await db.commit()

        return ToolResult(
            content=f"Case '{case.title}' status updated from {old_status} to {new_status}.",
            data={"case_id": case_id, "old_status": old_status, "new_status": new_status},
        )
    except Exception as e:
        return ToolResult(content="", error=f"Failed to update case status: {e}")


async def _get_dashboard_summary_execute(params: dict[str, Any], context: dict[str, Any]) -> ToolResult:
    try:
        from sqlalchemy import func, select
        from src.models.case import Case
        from src.models.client import Client

        db = context["db"]
        workspace_id = context["workspace_id"]

        total_cases = (await db.execute(
            select(func.count()).select_from(Case).where(Case.workspace_id == workspace_id)
        )).scalar() or 0

        active_cases = (await db.execute(
            select(func.count()).select_from(Case).where(
                Case.workspace_id == workspace_id,
                Case.status.in_(["active", "in_progress", "open"]),
            )
        )).scalar() or 0

        total_clients = (await db.execute(
            select(func.count()).select_from(Client).where(Client.workspace_id == workspace_id)
        )).scalar() or 0

        urgent_cases = (await db.execute(
            select(Case).where(
                Case.workspace_id == workspace_id,
                Case.priority.in_(["high", "urgent", "critical"]),
                Case.status.in_(["active", "in_progress", "open"]),
            ).limit(5)
        )).scalars().all()

        upcoming_stmt = (
            select(Case)
            .where(
                Case.workspace_id == workspace_id,
                Case.next_deadline.isnot(None),
                Case.status.in_(["active", "in_progress", "open"]),
            )
            .order_by(Case.next_deadline)
            .limit(5)
        )
        upcoming = (await db.execute(upcoming_stmt)).scalars().all()

        summary = (
            f"**Dashboard Summary**\n"
            f"Total Cases: {total_cases} | Active: {active_cases} | Clients: {total_clients}\n\n"
        )

        if urgent_cases:
            summary += "**Urgent Cases:**\n"
            for c in urgent_cases:
                summary += f"- {c.title} ({c.priority}) — {c.status}\n"
            summary += "\n"

        if upcoming:
            summary += "**Upcoming Deadlines:**\n"
            for c in upcoming:
                dl = c.next_deadline.strftime("%d %b %Y") if c.next_deadline else "—"
                summary += f"- {c.title}: {dl} — {c.next_deadline_description or ''}\n"

        return ToolResult(content=summary)
    except Exception as e:
        return ToolResult(content="", error=f"Failed to get dashboard summary: {e}")


search_cases_tool = Tool(
    name="search_cases",
    description="Search for cases by title, case number, practice area, or status.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term"},
            "status": {
                "type": "string",
                "description": "Filter by status (e.g. 'active', 'closed')",
            },
        },
        "required": ["query"],
    },
    execute=_search_cases_execute,
    read_only=True,
)

create_case_tool = Tool(
    name="create_case",
    description="Create a new case for an existing client.",
    parameters={
        "type": "object",
        "properties": {
            "client_id": {"type": "string", "description": "UUID of the client"},
            "title": {"type": "string", "description": "Title of the case"},
            "practice_area": {"type": "string", "description": "e.g. Corporate, Litigation, Real Estate"},
            "jurisdiction": {"type": "string", "description": "e.g. KSA, UAE, Bahrain"},
            "description": {"type": "string", "description": "Brief description"},
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "urgent"],
                "description": "Priority level",
            },
        },
        "required": ["client_id", "title"],
    },
    execute=_create_case_execute,
    read_only=False,
    requires_confirmation=True,
    risk_level="low",
    min_role="EDITOR",
)

update_case_status_tool = Tool(
    name="update_case_status",
    description="Update the status of a case (e.g. 'active' → 'closed').",
    parameters={
        "type": "object",
        "properties": {
            "case_id": {"type": "string", "description": "UUID of the case"},
            "status": {
                "type": "string",
                "description": "New status value",
            },
        },
        "required": ["case_id", "status"],
    },
    execute=_update_case_status_execute,
    read_only=False,
    requires_confirmation=True,
    risk_level="medium",
    min_role="EDITOR",
)

get_dashboard_summary_tool = Tool(
    name="get_dashboard_summary",
    description=(
        "Get an overview of the workspace: total cases, active cases, "
        "client count, urgent items, and upcoming deadlines."
    ),
    parameters={"type": "object", "properties": {}},
    execute=_get_dashboard_summary_execute,
    read_only=True,
)
