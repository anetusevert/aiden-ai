"""Clients router — CRUD for legal practice clients."""

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies.auth import (
    RequestContext,
    require_admin,
    require_editor,
    require_viewer,
)
from src.models.case import Case
from src.models.client import Client
from src.services.organization_access_service import ensure_workspace_org_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


# ── Pydantic Schemas ──────────────────────────────────────────────

class ClientCreate(BaseModel):
    client_type: str = Field(..., pattern="^(individual|company|organisation)$")
    display_name: str = Field(..., max_length=255)
    display_name_ar: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    national_id: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None
    trade_name: str | None = None
    cr_number: str | None = None
    vat_number: str | None = None
    sector: str | None = None
    incorporation_country: str | None = None
    org_type: str | None = None


class ClientUpdate(BaseModel):
    display_name: str | None = None
    display_name_ar: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    national_id: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None
    trade_name: str | None = None
    cr_number: str | None = None
    vat_number: str | None = None
    sector: str | None = None
    incorporation_country: str | None = None
    org_type: str | None = None


class CaseBriefResponse(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    next_deadline: str | None = None

    model_config = {"from_attributes": True}


class ClientResponse(BaseModel):
    id: str
    org_id: str
    client_type: str
    display_name: str
    display_name_ar: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    notes: str | None = None
    is_active: bool
    national_id: str | None = None
    nationality: str | None = None
    date_of_birth: str | None = None
    trade_name: str | None = None
    cr_number: str | None = None
    vat_number: str | None = None
    sector: str | None = None
    incorporation_country: str | None = None
    org_type: str | None = None
    created_at: datetime
    updated_at: datetime
    case_count: int = 0

    model_config = {"from_attributes": True}


class ClientDetailResponse(ClientResponse):
    cases: list[CaseBriefResponse] = []


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int


# ── Helpers ───────────────────────────────────────────────────────

def _get_org_id(ctx: RequestContext) -> str:
    """Get the organization ID from membership metadata."""
    if ctx.membership and ctx.membership.organization_id:
        return ctx.membership.organization_id
    raise HTTPException(status_code=400, detail="No organization found for current user")


async def _get_org_id_from_user(ctx: RequestContext, db: AsyncSession) -> str:
    """Resolve organization ID via organization membership."""
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


def _client_to_response(client: Client, *, case_count: int = 0) -> ClientResponse:
    return ClientResponse(
        id=client.id,
        org_id=client.org_id,
        client_type=client.client_type,
        display_name=client.display_name,
        display_name_ar=client.display_name_ar,
        email=client.email,
        phone=client.phone,
        address=client.address,
        notes=client.notes,
        is_active=client.is_active,
        national_id=client.national_id,
        nationality=client.nationality,
        date_of_birth=client.date_of_birth.isoformat() if client.date_of_birth else None,
        trade_name=client.trade_name,
        cr_number=client.cr_number,
        vat_number=client.vat_number,
        sector=client.sector,
        incorporation_country=client.incorporation_country,
        org_type=client.org_type,
        created_at=client.created_at,
        updated_at=client.updated_at,
        case_count=case_count,
    )


# ── Smart Onboarding ──────────────────────────────────────────────

class ExtractedClientData(BaseModel):
    client_type: str = "individual"
    display_name: str = ""
    display_name_ar: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    national_id: str | None = None
    nationality: str | None = None
    cr_number: str | None = None
    vat_number: str | None = None
    trade_name: str | None = None
    sector: str | None = None
    org_type: str | None = None
    notes: str | None = None
    confidence: float = 0.0


@router.post("/extract-from-document", response_model=ExtractedClientData)
async def extract_client_from_document(
    file: UploadFile,
    ctx: Annotated[RequestContext, Depends(require_editor())],
) -> ExtractedClientData:
    """Upload a document (PDF, DOCX, image) and use AI to extract client information."""
    if not file.filename:
        raise HTTPException(status_code=422, detail="No file provided")

    allowed = {".pdf", ".docx", ".doc", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(status_code=422, detail=f"Unsupported file type: {ext}")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="File too large (max 20MB)")

    text = ""
    try:
        if ext == ".pdf":
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
        elif ext in (".docx", ".doc"):
            import io

            from docx import Document as DocxDoc
            doc = DocxDoc(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        else:
            text = f"[Image file: {file.filename} — text extraction not available for images in this version]"
    except Exception as e:
        logger.warning("Text extraction failed for %s: %s", file.filename, e)
        text = f"[Extraction failed for {file.filename}]"

    if not text.strip() or len(text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Could not extract text from document")

    try:
        from src.llm.providers import get_llm_provider
        provider = get_llm_provider()

        prompt = (
            "You are a legal AI assistant. Extract client information from this document.\n\n"
            "DOCUMENT TEXT:\n" + text[:8000] + "\n\n"
            "Extract and return a JSON object with these fields:\n"
            '- "client_type": one of "individual", "company", or "organisation"\n'
            '- "display_name": the full name of the person or entity\n'
            '- "display_name_ar": Arabic name if present\n'
            '- "email": email address if found\n'
            '- "phone": phone number if found\n'
            '- "address": address if found\n'
            '- "national_id": national ID / Iqama number for individuals\n'
            '- "nationality": nationality for individuals\n'
            '- "cr_number": Commercial Registration number for companies\n'
            '- "vat_number": VAT number if found\n'
            '- "trade_name": trade/brand name for companies\n'
            '- "sector": industry/sector for companies\n'
            '- "org_type": type for organisations (government, ngo, international, semi-govt)\n'
            '- "notes": any other relevant information\n'
            '- "confidence": your confidence level 0.0-1.0\n\n'
            "Return ONLY valid JSON, no markdown or explanation."
        )

        messages = [
            {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        response = await provider.chat_completion(messages=messages, max_tokens=800)
        raw = response.get("content", "") if isinstance(response, dict) else str(response)

        import json
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]

        data = json.loads(raw)
        return ExtractedClientData(**{k: v for k, v in data.items() if k in ExtractedClientData.model_fields})
    except Exception as e:
        logger.warning("AI extraction failed: %s", e)
        raise HTTPException(status_code=500, detail="AI extraction failed. Please fill in the form manually.")


# ── Endpoints ─────────────────────────────────────────────────────

@router.get("", response_model=ClientListResponse)
async def list_clients(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = Query(None, description="Search by name, email, or CR number"),
    client_type: str | None = Query(None, description="Filter by client type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    org_id = await _get_org_id_from_user(ctx, db)

    base_q = select(Client).where(Client.org_id == org_id)
    count_q = select(func.count()).select_from(Client).where(Client.org_id == org_id)

    if search:
        search_filter = (
            Client.display_name.ilike(f"%{search}%")
            | Client.email.ilike(f"%{search}%")
            | Client.cr_number.ilike(f"%{search}%")
        )
        base_q = base_q.where(search_filter)
        count_q = count_q.where(search_filter)

    if client_type:
        base_q = base_q.where(Client.client_type == client_type)
        count_q = count_q.where(Client.client_type == client_type)

    if is_active is not None:
        base_q = base_q.where(Client.is_active == is_active)
        count_q = count_q.where(Client.is_active == is_active)

    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(
        base_q.order_by(Client.display_name).offset(offset).limit(limit)
    )
    clients = list(result.scalars().all())

    items = []
    for c in clients:
        case_count_result = await db.execute(
            select(func.count()).select_from(Case).where(Case.client_id == c.id)
        )
        case_count = case_count_result.scalar() or 0
        item = _client_to_response(c, case_count=case_count)
        items.append(item)

    return {"items": items, "total": total}


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    from datetime import date as date_type

    org_id = await _get_org_id_from_user(ctx, db)

    dob = None
    if body.date_of_birth:
        try:
            dob = date_type.fromisoformat(body.date_of_birth)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_of_birth format, use YYYY-MM-DD")

    client = Client(
        org_id=org_id,
        client_type=body.client_type,
        display_name=body.display_name,
        display_name_ar=body.display_name_ar,
        email=body.email,
        phone=body.phone,
        address=body.address,
        notes=body.notes,
        national_id=body.national_id,
        nationality=body.nationality,
        date_of_birth=dob,
        trade_name=body.trade_name,
        cr_number=body.cr_number,
        vat_number=body.vat_number,
        sector=body.sector,
        incorporation_country=body.incorporation_country,
        org_type=body.org_type,
        created_by=ctx.user.id,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)

    return _client_to_response(client, case_count=0)


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
    client_id: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id_from_user(ctx, db)

    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.org_id == org_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    cases_result = await db.execute(
        select(Case)
        .where(Case.client_id == client_id)
        .order_by(Case.created_at.desc())
    )
    cases = list(cases_result.scalars().all())

    case_briefs = [
        CaseBriefResponse(
            id=c.id,
            title=c.title,
            status=c.status,
            priority=c.priority,
            next_deadline=c.next_deadline.isoformat() if c.next_deadline else None,
        )
        for c in cases
    ]

    base = _client_to_response(client, case_count=len(cases))
    return ClientDetailResponse(**base.model_dump(), cases=case_briefs)


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: str,
    body: ClientUpdate,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    org_id = await _get_org_id_from_user(ctx, db)

    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.org_id == org_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = body.model_dump(exclude_unset=True)
    if "date_of_birth" in update_data and update_data["date_of_birth"] is not None:
        from datetime import date as date_type
        try:
            update_data["date_of_birth"] = date_type.fromisoformat(update_data["date_of_birth"])
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date_of_birth format")

    for key, value in update_data.items():
        setattr(client, key, value)

    await db.commit()
    await db.refresh(client)

    case_count_result = await db.execute(
        select(func.count()).select_from(Case).where(Case.client_id == client.id)
    )
    return _client_to_response(client, case_count=case_count_result.scalar() or 0)


@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
async def delete_client(
    client_id: str,
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    org_id = await _get_org_id_from_user(ctx, db)

    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.org_id == org_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    active_case_count = await db.execute(
        select(func.count()).select_from(Case)
        .where(Case.client_id == client_id, Case.status == "active")
    )
    if (active_case_count.scalar() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate client with active cases. Close or reassign active cases first.",
        )

    client.is_active = False
    await db.commit()
    return {"status": "deactivated", "client_id": client_id}
