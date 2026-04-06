"""Wiki API endpoints for the Amin Legal Wiki."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, require_admin, require_viewer
from src.models.wiki import WikiIndex, WikiLink, WikiLog, WikiPage
from src.services.wiki_service import WikiService

router = APIRouter(prefix="/wiki", tags=["wiki"])


# ── Schemas ─────────────────────────────────────────────────────────────


class WikiPageOut(BaseModel):
    id: str
    slug: str
    title: str
    category: str
    content_md: str
    summary: str
    jurisdiction: str | None
    source_doc_ids: list[Any]
    inbound_link_count: int
    version: int
    is_stale: bool
    has_contradictions: bool
    created_by_tool: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class WikiPageSummary(BaseModel):
    id: str
    slug: str
    title: str
    category: str
    summary: str
    jurisdiction: str | None
    inbound_link_count: int
    version: int
    is_stale: bool
    has_contradictions: bool
    updated_at: str

    model_config = {"from_attributes": True}


class WikiLinkOut(BaseModel):
    id: str
    from_page_id: str
    to_page_id: str
    link_text: str
    context: str
    created_at: str

    model_config = {"from_attributes": True}


class WikiPageListResponse(BaseModel):
    items: list[WikiPageSummary]
    total: int


class WikiGraphNode(BaseModel):
    id: str
    slug: str
    title: str
    category: str
    jurisdiction: str | None
    inbound_link_count: int


class WikiGraphEdge(BaseModel):
    source: str = Field(alias="from")
    target: str = Field(alias="to")
    context: str

    model_config = {"populate_by_name": True}


class WikiGraphResponse(BaseModel):
    nodes: list[WikiGraphNode]
    edges: list[WikiGraphEdge]


class WikiLogOut(BaseModel):
    id: str
    operation: str
    page_slug: str | None
    source_description: str
    amin_summary: str
    pages_affected: list[Any]
    created_at: str

    model_config = {"from_attributes": True}


class WikiLogListResponse(BaseModel):
    items: list[WikiLogOut]
    total: int


class WikiHealthResponse(BaseModel):
    page_count: int
    orphan_count: int
    stale_count: int
    contradiction_count: int


class WikiPageUpdateRequest(BaseModel):
    instruction: str


class WikiIngestRequest(BaseModel):
    source_text: str
    source_title: str
    source_type: str = "research_result"
    metadata: dict[str, Any] = {}


class WikiBacklink(BaseModel):
    slug: str
    title: str
    context: str

    model_config = {"from_attributes": True}


class WikiPageDetailResponse(WikiPageOut):
    backlinks: list[WikiBacklink] = []
    outlinks: list[WikiBacklink] = []


# ── Endpoints ───────────────────────────────────────────────────────────


@router.get("/pages", response_model=WikiPageListResponse)
async def list_wiki_pages(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = None,
    category: str | None = None,
    jurisdiction: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """List wiki pages with optional search, category, and jurisdiction filters."""
    org_id = getattr(ctx, "organization_id", None)

    stmt = select(WikiPage).where(WikiPage.org_id == org_id)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (WikiPage.title.ilike(pattern))
            | (WikiPage.summary.ilike(pattern))
        )
    if category:
        stmt = stmt.where(WikiPage.category == category)
    if jurisdiction:
        stmt = stmt.where(WikiPage.jurisdiction == jurisdiction)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(WikiPage.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    pages = result.scalars().all()

    return WikiPageListResponse(
        items=[
            WikiPageSummary(
                id=p.id,
                slug=p.slug,
                title=p.title,
                category=p.category,
                summary=p.summary,
                jurisdiction=p.jurisdiction,
                inbound_link_count=p.inbound_link_count,
                version=p.version,
                is_stale=p.is_stale,
                has_contradictions=p.has_contradictions,
                updated_at=p.updated_at.isoformat() if p.updated_at else "",
            )
            for p in pages
        ],
        total=total,
    )


@router.get("/pages/{slug}", response_model=WikiPageDetailResponse)
async def get_wiki_page(
    slug: str,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single wiki page by slug with backlinks and outlinks."""
    org_id = getattr(ctx, "organization_id", None)

    stmt = select(WikiPage).where(
        WikiPage.slug == slug,
        WikiPage.org_id == org_id,
    )
    result = await db.execute(stmt)
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    # Backlinks: pages that link TO this page
    backlink_stmt = (
        select(WikiLink, WikiPage)
        .join(WikiPage, WikiLink.from_page_id == WikiPage.id)
        .where(WikiLink.to_page_id == page.id)
    )
    backlink_result = await db.execute(backlink_stmt)
    backlinks = [
        WikiBacklink(slug=p.slug, title=p.title, context=link.context)
        for link, p in backlink_result.all()
    ]

    # Outlinks: pages this page links TO
    outlink_stmt = (
        select(WikiLink, WikiPage)
        .join(WikiPage, WikiLink.to_page_id == WikiPage.id)
        .where(WikiLink.from_page_id == page.id)
    )
    outlink_result = await db.execute(outlink_stmt)
    outlinks = [
        WikiBacklink(slug=p.slug, title=p.title, context=link.context)
        for link, p in outlink_result.all()
    ]

    return WikiPageDetailResponse(
        id=page.id,
        slug=page.slug,
        title=page.title,
        category=page.category,
        content_md=page.content_md,
        summary=page.summary,
        jurisdiction=page.jurisdiction,
        source_doc_ids=page.source_doc_ids or [],
        inbound_link_count=page.inbound_link_count,
        version=page.version,
        is_stale=page.is_stale,
        has_contradictions=page.has_contradictions,
        created_by_tool=page.created_by_tool,
        created_at=page.created_at.isoformat() if page.created_at else "",
        updated_at=page.updated_at.isoformat() if page.updated_at else "",
        backlinks=backlinks,
        outlinks=outlinks,
    )


@router.post("/pages/{slug}/update")
async def update_wiki_page(
    slug: str,
    body: WikiPageUpdateRequest,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a wiki page using Amin's intelligence."""
    org_id = getattr(ctx, "organization_id", None)
    service = WikiService(db)

    page = await service.get_page(slug, org_id)
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    result = await service.ingest_source(
        source_text=body.instruction,
        source_title=f"Update to {page.title}",
        source_type="workflow_output",
        org_id=org_id,
        user_id=ctx.user.id,
    )

    return {"status": "ok", "page_slug": result.primary_page.slug, "version": result.primary_page.version}


@router.get("/graph", response_model=WikiGraphResponse)
async def get_wiki_graph(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the wiki knowledge graph (nodes + edges) for visualisation."""
    org_id = getattr(ctx, "organization_id", None)

    pages_stmt = select(WikiPage).where(WikiPage.org_id == org_id)
    pages_result = await db.execute(pages_stmt)
    pages = list(pages_result.scalars().all())

    page_ids = {p.id for p in pages}
    nodes = [
        WikiGraphNode(
            id=p.id,
            slug=p.slug,
            title=p.title,
            category=p.category,
            jurisdiction=p.jurisdiction,
            inbound_link_count=p.inbound_link_count,
        )
        for p in pages
    ]

    links_stmt = select(WikiLink).where(
        WikiLink.from_page_id.in_(page_ids),
        WikiLink.to_page_id.in_(page_ids),
    )
    links_result = await db.execute(links_stmt)
    links = list(links_result.scalars().all())

    edges = [
        WikiGraphEdge(**{"from": link.from_page_id, "to": link.to_page_id, "context": link.context})
        for link in links
    ]

    return WikiGraphResponse(nodes=nodes, edges=edges)


@router.get("/log", response_model=WikiLogListResponse)
async def list_wiki_logs(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
    operation: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List wiki operation logs."""
    org_id = getattr(ctx, "organization_id", None)

    stmt = select(WikiLog).where(WikiLog.org_id == org_id)
    if operation:
        stmt = stmt.where(WikiLog.operation == operation)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(WikiLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return WikiLogListResponse(
        items=[
            WikiLogOut(
                id=log.id,
                operation=log.operation,
                page_slug=log.page_slug,
                source_description=log.source_description,
                amin_summary=log.amin_summary,
                pages_affected=log.pages_affected or [],
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=total,
    )


@router.get("/health", response_model=WikiHealthResponse)
async def wiki_health(
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get wiki health stats: page count, orphans, stale, contradictions."""
    org_id = getattr(ctx, "organization_id", None)

    base = select(WikiPage).where(WikiPage.org_id == org_id)
    page_count = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    orphan_count = (await db.execute(
        select(func.count()).select_from(
            base.where(WikiPage.inbound_link_count == 0).subquery()
        )
    )).scalar() or 0
    stale_count = (await db.execute(
        select(func.count()).select_from(
            base.where(WikiPage.is_stale == True).subquery()  # noqa: E712
        )
    )).scalar() or 0
    contradiction_count = (await db.execute(
        select(func.count()).select_from(
            base.where(WikiPage.has_contradictions == True).subquery()  # noqa: E712
        )
    )).scalar() or 0

    return WikiHealthResponse(
        page_count=page_count,
        orphan_count=orphan_count,
        stale_count=stale_count,
        contradiction_count=contradiction_count,
    )


@router.post("/lint")
async def run_wiki_lint(
    ctx: Annotated[RequestContext, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Run a health check / lint pass on the wiki (admin only)."""
    org_id = getattr(ctx, "organization_id", None)

    service = WikiService(db)
    await service.rebuild_index(org_id)

    return {"status": "ok", "message": "Wiki health check started"}


@router.post("/ingest")
async def ingest_to_wiki(
    body: WikiIngestRequest,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Ingest content into the wiki."""
    org_id = getattr(ctx, "organization_id", None)

    service = WikiService(db)
    result = await service.ingest_source(
        source_text=body.source_text,
        source_title=body.source_title,
        source_type=body.source_type,
        org_id=org_id,
        user_id=ctx.user.id,
        metadata=body.metadata,
    )

    return {
        "status": "ok",
        "page_slug": result.primary_page.slug,
        "page_title": result.primary_page.title,
        "action": result.primary_page.action,
        "links_created": result.links_created,
        "contradictions": result.contradictions,
    }
