"""Cases router — CRUD for legal cases, documents, notes, timeline, and active case management."""

import logging
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import (
    RequestContext,
    require_admin,
    require_editor,
    require_viewer,
)
from src.models.case import Case, CaseDocument, CaseEvent, CaseNote
from src.models.client import Client
from src.models.office import OfficeDocument
from src.services.organization_access_service import ensure_workspace_org_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


# ── Pydantic Schemas ──────────────────────────────────────────────

class CaseCreate(BaseModel):
    client_id: str
    title: str = Field(..., max_length=255)
    title_ar: str | None = None
    case_number: str | None = None
    internal_ref: str | None = None
    practice_area: str
    jurisdiction: str
    status: str = "active"
    priority: str = "medium"
    court_name: str | None = None
    court_circuit: str | None = None
    judge_name: str | None = None
    opposing_counsel: str | None = None
    opposing_party: str | None = None
    next_deadline: str | None = None
    next_deadline_description: str | None = None
    description: str | None = None
    lead_lawyer: str | None = None


class CaseUpdate(BaseModel):
    title: str | None = None
    title_ar: str | None = None
    case_number: str | None = None
    internal_ref: str | None = None
    practice_area: str | None = None
    jurisdiction: str | None = None
    status: str | None = None
    priority: str | None = None
    court_name: str | None = None
    court_circuit: str | None = None
    judge_name: str | None = None
    opposing_counsel: str | None = None
    opposing_party: str | None = None
    next_deadline: str | None = None
    next_deadline_description: str | None = None
    description: str | None = None
    lead_lawyer: str | None = None
    closed_at: str | None = None


class ClientBriefResponse(BaseModel):
    id: str
    display_name: str
    client_type: str
    model_config = {"from_attributes": True}


class CaseBrief(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    practice_area: str
    next_deadline: str | None = None
    next_deadline_description: str | None = None
    client_display_name: str = ""
    urgent: bool = False
    model_config = {"from_attributes": True}


class CaseResponse(BaseModel):
    id: str
    org_id: str
    client_id: str
    title: str
    title_ar: str | None = None
    case_number: str | None = None
    internal_ref: str | None = None
    practice_area: str
    jurisdiction: str
    status: str
    priority: str
    court_name: str | None = None
    court_circuit: str | None = None
    judge_name: str | None = None
    opposing_counsel: str | None = None
    opposing_party: str | None = None
    opened_at: str | None = None
    closed_at: str | None = None
    next_deadline: str | None = None
    next_deadline_description: str | None = None
    description: str | None = None
    amin_briefing: str | None = None
    lead_lawyer: str | None = None
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    client: ClientBriefResponse | None = None
    document_count: int = 0
    note_count: int = 0
    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    items: list[CaseBrief]
    total: int


class PracticeAreaCount(BaseModel):
    area: str
    count: int


class DashboardResponse(BaseModel):
    active_cases: int
    high_priority: int
    due_today: list[CaseBrief]
    due_this_week: list[CaseBrief]
    recently_accessed: list[CaseBrief]
    practice_area_distribution: list[PracticeAreaCount]


class CaseDocumentResponse(BaseModel):
    id: str
    case_id: str
    document_id: str
    document_role: str
    attached_at: datetime
    document_title: str = ""
    document_type: str = ""
    model_config = {"from_attributes": True}


class CaseDocumentCreate(BaseModel):
    document_id: str
    document_role: str = "general"


class CaseNoteResponse(BaseModel):
    id: str
    case_id: str
    content: str
    is_amin_generated: bool
    created_by: str | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class CaseNoteCreate(BaseModel):
    content: str
    is_amin_generated: bool = False


class CaseEventResponse(BaseModel):
    id: str
    case_id: str
    event_type: str
    title: str
    description: str | None = None
    event_date: datetime
    created_by: str | None = None
    metadata_: dict[str, Any] = {}
    model_config = {"from_attributes": True}


class ActiveCaseResponse(BaseModel):
    case_id: str
    case_title: str


# ── Helpers ───────────────────────────────────────────────────────

async def _get_org_id_from_user(ctx: RequestContext, db: AsyncSession) -> str:
    org_id = await ensure_workspace_org_access(
        db,
        tenant_id=ctx.tenant.id,
        workspace_id=ctx.workspace.id if ctx.workspace else "",
        workspace_name=ctx.workspace.name if ctx.workspace else None,
        user_id=ctx.user.id,
        workspace_role=ctx.role or "VIEWER",
    )
    if not org_id:
        raise HTTPException(status_code=400, detail="User is not a member of any organization")
    return org_id


def _case_to_brief(case: Case, client_name: str = "") -> CaseBrief:
    today = date.today()
    urgent = (
        case.next_deadline is not None
        and case.status == "active"
        and case.next_deadline <= today + timedelta(days=7)
    )
    return CaseBrief(
        id=case.id,
        title=case.title,
        status=case.status,
        priority=case.priority,
        practice_area=case.practice_area,
        next_deadline=case.next_deadline.isoformat() if case.next_deadline else None,
        next_deadline_description=case.next_deadline_description,
        client_display_name=client_name,
        urgent=urgent,
    )


async def _get_redis():
    from src.services.agent.screen_context import get_redis_client
    return get_redis_client()


async def _generate_amin_briefing(case_id: str, db_url: str) -> None:
    """Background task: generate Amin briefing for a case."""
    try:
        from src.database import async_session_maker
        from src.llm.providers import get_llm_provider

        async with async_session_maker() as db:
            case = await db.get(Case, case_id)
            if not case:
                return

            client = await db.get(Client, case.client_id)
            client_info = f"{client.display_name} ({client.client_type})" if client else "Unknown client"

            prompt = (
                f"You are Amin, a senior legal AI assistant. Generate a 2-3 sentence case briefing.\n\n"
                f"Client: {client_info}\n"
                f"Case: {case.title}\n"
                f"Practice Area: {case.practice_area}\n"
                f"Jurisdiction: {case.jurisdiction}\n"
                f"Description: {case.description or 'No description provided.'}\n\n"
                f"Write a concise briefing summarizing what this case involves and key considerations."
            )

            provider = get_llm_provider()
            messages = [
                {"role": "system", "content": "You are Amin, a GCC/KSA legal intelligence assistant. Be concise and professional."},
                {"role": "user", "content": prompt},
            ]
            response = await provider.chat_completion(messages=messages, max_tokens=200)
            briefing = response.get("content", "") if isinstance(response, dict) else str(response)

            if briefing:
                case.amin_briefing = briefing
                await db.commit()
    except Exception as e:
        logger.warning("Amin briefing generation failed for case %s: %s", case_id, e)


# ── Case CRUD ─────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id_from_user(ctx, db)
    today = date.today()
    week_end = today + timedelta(days=7)

    active_count = (await db.execute(
        select(func.count()).select_from(Case).where(Case.org_id == org_id, Case.status == "active")
    )).scalar() or 0

    high_priority_count = (await db.execute(
        select(func.count()).select_from(Case)
        .where(Case.org_id == org_id, Case.status == "active", Case.priority == "high")
    )).scalar() or 0

    due_today_result = await db.execute(
        select(Case).where(Case.org_id == org_id, Case.status == "active", Case.next_deadline == today)
    )
    due_today_cases = list(due_today_result.scalars().all())

    due_week_result = await db.execute(
        select(Case).where(
            Case.org_id == org_id,
            Case.status == "active",
            Case.next_deadline != None,  # noqa: E711
            Case.next_deadline <= week_end,
            Case.next_deadline > today,
        )
    )
    due_week_cases = list(due_week_result.scalars().all())

    # Recently accessed from Redis
    recently_accessed: list[CaseBrief] = []
    try:
        redis_client = await _get_redis()
        recent_ids_raw = await redis_client.lrange(f"recent_cases:{ctx.user.id}", 0, 4)
        if recent_ids_raw:
            for rid in recent_ids_raw:
                c = await db.get(Case, rid)
                if c:
                    client = await db.get(Client, c.client_id)
                    recently_accessed.append(_case_to_brief(c, client.display_name if client else ""))
    except Exception:
        pass

    # Practice area distribution
    pa_result = await db.execute(
        select(Case.practice_area, func.count().label("cnt"))
        .where(Case.org_id == org_id, Case.status == "active")
        .group_by(Case.practice_area)
    )
    pa_distribution = [PracticeAreaCount(area=row[0], count=row[1]) for row in pa_result.all()]

    return DashboardResponse(
        active_cases=active_count,
        high_priority=high_priority_count,
        due_today=[_case_to_brief(c, c.client.display_name if c.client else "") for c in due_today_cases],
        due_this_week=[_case_to_brief(c, c.client.display_name if c.client else "") for c in due_week_cases],
        recently_accessed=recently_accessed,
        practice_area_distribution=pa_distribution,
    )


@router.get("/active")
async def get_active_case(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any] | None:
    try:
        redis_client = await _get_redis()
        case_id = await redis_client.get(f"active_case:{ctx.user.id}")
        if not case_id:
            return None
        case = await db.get(Case, case_id)
        if not case:
            return None
        client = await db.get(Client, case.client_id)
        return {
            "case_id": case.id,
            "case_title": case.title,
            "client_name": client.display_name if client else "",
            "practice_area": case.practice_area,
            "jurisdiction": case.jurisdiction,
            "status": case.status,
            "priority": case.priority,
        }
    except Exception:
        return None


@router.get("", response_model=CaseListResponse)
async def list_cases(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    practice_area: str | None = Query(None),
    jurisdiction: str | None = Query(None),
    client_id: str | None = Query(None),
    lead_lawyer: str | None = Query(None),
    deadline_before: str | None = Query(None),
    deadline_after: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    org_id = await _get_org_id_from_user(ctx, db)

    base_q = select(Case).where(Case.org_id == org_id)
    count_q = select(func.count()).select_from(Case).where(Case.org_id == org_id)

    filters = []
    if search:
        search_filter = or_(
            Case.title.ilike(f"%{search}%"),
            Case.case_number.ilike(f"%{search}%"),
        )
        filters.append(search_filter)
    if status_filter:
        filters.append(Case.status == status_filter)
    if priority:
        filters.append(Case.priority == priority)
    if practice_area:
        filters.append(Case.practice_area == practice_area)
    if jurisdiction:
        filters.append(Case.jurisdiction == jurisdiction)
    if client_id:
        filters.append(Case.client_id == client_id)
    if lead_lawyer:
        filters.append(Case.lead_lawyer == lead_lawyer)
    if deadline_before:
        filters.append(Case.next_deadline <= date.fromisoformat(deadline_before))
    if deadline_after:
        filters.append(Case.next_deadline >= date.fromisoformat(deadline_after))

    for f in filters:
        base_q = base_q.where(f)
        count_q = count_q.where(f)

    total = (await db.execute(count_q)).scalar() or 0

    priority_order = func.case(
        (Case.priority == "high", 1),
        (Case.priority == "medium", 2),
        else_=3,
    )
    result = await db.execute(
        base_q.order_by(priority_order, Case.next_deadline.asc().nulls_last())
        .offset(offset)
        .limit(limit)
    )
    cases = list(result.scalars().all())

    items = []
    for c in cases:
        client_name = c.client.display_name if c.client else ""
        items.append(_case_to_brief(c, client_name))

    return {"items": items, "total": total}


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
) -> Any:
    org_id = await _get_org_id_from_user(ctx, db)

    client = await db.get(Client, body.client_id)
    if not client or client.org_id != org_id:
        raise HTTPException(status_code=404, detail="Client not found")

    next_dl = None
    if body.next_deadline:
        try:
            next_dl = date.fromisoformat(body.next_deadline)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid next_deadline format")

    case = Case(
        org_id=org_id,
        client_id=body.client_id,
        title=body.title,
        title_ar=body.title_ar,
        case_number=body.case_number,
        internal_ref=body.internal_ref,
        practice_area=body.practice_area,
        jurisdiction=body.jurisdiction,
        status=body.status,
        priority=body.priority,
        court_name=body.court_name,
        court_circuit=body.court_circuit,
        judge_name=body.judge_name,
        opposing_counsel=body.opposing_counsel,
        opposing_party=body.opposing_party,
        next_deadline=next_dl,
        next_deadline_description=body.next_deadline_description,
        description=body.description,
        lead_lawyer=body.lead_lawyer,
        created_by=ctx.user.id,
    )
    db.add(case)
    await db.flush()

    event = CaseEvent(
        case_id=case.id,
        event_type="created",
        title="Case opened",
        description=f"Case '{case.title}' created for client '{client.display_name}'",
        created_by=ctx.user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(case)

    background_tasks.add_task(_generate_amin_briefing, case.id, "")

    doc_count = (await db.execute(
        select(func.count()).select_from(CaseDocument).where(CaseDocument.case_id == case.id)
    )).scalar() or 0
    note_count = (await db.execute(
        select(func.count()).select_from(CaseNote).where(CaseNote.case_id == case.id)
    )).scalar() or 0

    resp = CaseResponse.model_validate(case)
    resp.opened_at = case.opened_at.isoformat() if case.opened_at else None
    resp.next_deadline = case.next_deadline.isoformat() if case.next_deadline else None
    resp.client = ClientBriefResponse(id=client.id, display_name=client.display_name, client_type=client.client_type)
    resp.document_count = doc_count
    resp.note_count = note_count
    return resp


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id_from_user(ctx, db)
    case = (await db.execute(
        select(Case).where(Case.id == case_id, Case.org_id == org_id)
    )).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    client = await db.get(Client, case.client_id)

    doc_count = (await db.execute(
        select(func.count()).select_from(CaseDocument).where(CaseDocument.case_id == case.id)
    )).scalar() or 0
    note_count = (await db.execute(
        select(func.count()).select_from(CaseNote).where(CaseNote.case_id == case.id)
    )).scalar() or 0

    resp = CaseResponse.model_validate(case)
    resp.opened_at = case.opened_at.isoformat() if case.opened_at else None
    resp.closed_at = case.closed_at.isoformat() if case.closed_at else None
    resp.next_deadline = case.next_deadline.isoformat() if case.next_deadline else None
    resp.client = ClientBriefResponse(
        id=client.id, display_name=client.display_name, client_type=client.client_type
    ) if client else None
    resp.document_count = doc_count
    resp.note_count = note_count
    return resp


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: str,
    body: CaseUpdate,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id_from_user(ctx, db)
    case = (await db.execute(
        select(Case).where(Case.id == case_id, Case.org_id == org_id)
    )).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    update_data = body.model_dump(exclude_unset=True)
    old_status = case.status
    old_deadline = case.next_deadline

    date_fields = {"next_deadline", "closed_at"}
    for df in date_fields:
        if df in update_data and update_data[df] is not None:
            try:
                update_data[df] = date.fromisoformat(update_data[df])
            except ValueError:
                raise HTTPException(status_code=422, detail=f"Invalid {df} format")

    for key, value in update_data.items():
        setattr(case, key, value)

    if "status" in update_data and update_data["status"] != old_status:
        db.add(CaseEvent(
            case_id=case.id,
            event_type="status_change",
            title=f"Status changed to {update_data['status']}",
            description=f"Changed from {old_status} to {update_data['status']}",
            created_by=ctx.user.id,
        ))

    new_deadline = update_data.get("next_deadline")
    if new_deadline and new_deadline != old_deadline:
        db.add(CaseEvent(
            case_id=case.id,
            event_type="deadline_set",
            title=f"Deadline set: {update_data.get('next_deadline_description', '')}",
            description=f"Deadline: {new_deadline}",
            created_by=ctx.user.id,
        ))

    await db.commit()
    await db.refresh(case)
    return await get_case(case_id, ctx, db)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    org_id = await _get_org_id_from_user(ctx, db)
    case = (await db.execute(
        select(Case).where(Case.id == case_id, Case.org_id == org_id)
    )).scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await db.delete(case)
    await db.commit()


# ── Case Documents ────────────────────────────────────────────────

@router.get("/{case_id}/documents", response_model=list[CaseDocumentResponse])
async def list_case_documents(
    case_id: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(CaseDocument).where(CaseDocument.case_id == case_id)
        .order_by(CaseDocument.attached_at.desc())
    )
    case_docs = list(result.scalars().all())

    items = []
    for cd in case_docs:
        doc = cd.document
        items.append({
            "id": cd.id,
            "case_id": cd.case_id,
            "document_id": cd.document_id,
            "document_role": cd.document_role,
            "attached_at": cd.attached_at,
            "document_title": doc.title if doc else "",
            "document_type": doc.doc_type if doc else "",
        })
    return items


@router.post("/{case_id}/documents", response_model=CaseDocumentResponse, status_code=status.HTTP_201_CREATED)
async def attach_document(
    case_id: str,
    body: CaseDocumentCreate,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    doc = await db.get(OfficeDocument, body.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    existing = (await db.execute(
        select(CaseDocument).where(
            CaseDocument.case_id == case_id,
            CaseDocument.document_id == body.document_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Document already attached to this case")

    cd = CaseDocument(
        case_id=case_id,
        document_id=body.document_id,
        attached_by=ctx.user.id,
        document_role=body.document_role,
    )
    db.add(cd)

    db.add(CaseEvent(
        case_id=case_id,
        event_type="document_added",
        title=f"Document attached: {doc.title}",
        description=f"Role: {body.document_role}",
        created_by=ctx.user.id,
    ))
    await db.commit()
    await db.refresh(cd)

    return {
        "id": cd.id,
        "case_id": cd.case_id,
        "document_id": cd.document_id,
        "document_role": cd.document_role,
        "attached_at": cd.attached_at,
        "document_title": doc.title,
        "document_type": doc.doc_type,
    }


@router.delete("/{case_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_document(
    case_id: str,
    document_id: str,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    cd = (await db.execute(
        select(CaseDocument).where(
            CaseDocument.case_id == case_id,
            CaseDocument.document_id == document_id,
        )
    )).scalar_one_or_none()
    if not cd:
        raise HTTPException(status_code=404, detail="Document not attached to this case")
    await db.delete(cd)
    await db.commit()


# ── Case Notes ────────────────────────────────────────────────────

@router.get("/{case_id}/notes", response_model=list[CaseNoteResponse])
async def list_case_notes(
    case_id: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(CaseNote).where(CaseNote.case_id == case_id)
        .order_by(CaseNote.created_at.desc())
    )
    notes = list(result.scalars().all())
    items = []
    for n in notes:
        user = n.created_by_user
        items.append({
            "id": n.id,
            "case_id": n.case_id,
            "content": n.content,
            "is_amin_generated": n.is_amin_generated,
            "created_by": n.created_by,
            "created_by_name": user.full_name if user else ("Amin" if n.is_amin_generated else None),
            "created_at": n.created_at,
            "updated_at": n.updated_at,
        })
    return items


@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    case_id: str,
    body: CaseNoteCreate,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    note = CaseNote(
        case_id=case_id,
        content=body.content,
        is_amin_generated=body.is_amin_generated,
        created_by=ctx.user.id,
    )
    db.add(note)

    db.add(CaseEvent(
        case_id=case_id,
        event_type="note_added",
        title="Note added" + (" by Amin" if body.is_amin_generated else ""),
        description=body.content[:200],
        created_by=ctx.user.id if not body.is_amin_generated else None,
    ))
    await db.commit()
    await db.refresh(note)

    user = note.created_by_user
    return {
        "id": note.id,
        "case_id": note.case_id,
        "content": note.content,
        "is_amin_generated": note.is_amin_generated,
        "created_by": note.created_by,
        "created_by_name": user.full_name if user else ("Amin" if note.is_amin_generated else None),
        "created_at": note.created_at,
        "updated_at": note.updated_at,
    }


@router.delete("/{case_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    case_id: str,
    note_id: str,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    note = (await db.execute(
        select(CaseNote).where(CaseNote.id == note_id, CaseNote.case_id == case_id)
    )).scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    await db.delete(note)
    await db.commit()


# ── Timeline ──────────────────────────────────────────────────────

@router.get("/{case_id}/timeline", response_model=list[CaseEventResponse])
async def get_timeline(
    case_id: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(CaseEvent).where(CaseEvent.case_id == case_id)
        .order_by(CaseEvent.event_date.desc())
    )
    events = list(result.scalars().all())
    return [
        {
            "id": e.id,
            "case_id": e.case_id,
            "event_type": e.event_type,
            "title": e.title,
            "description": e.description,
            "event_date": e.event_date,
            "created_by": e.created_by,
            "metadata_": e.metadata_,
        }
        for e in events
    ]


# ── Active Case ───────────────────────────────────────────────────

@router.post("/{case_id}/set-active", response_model=ActiveCaseResponse)
async def set_active_case(
    case_id: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    redis_client = await _get_redis()
    await redis_client.set(f"active_case:{ctx.user.id}", case_id)

    # Track recently accessed (prepend, deduplicate, keep 10)
    key = f"recent_cases:{ctx.user.id}"
    await redis_client.lrem(key, 0, case_id)
    await redis_client.lpush(key, case_id)
    await redis_client.ltrim(key, 0, 9)

    return {"case_id": case.id, "case_title": case.title}
