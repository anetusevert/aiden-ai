"""Shared service layer for Office documents and WOPI."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.database import async_session_maker
from src.dependencies.auth import RequestContext
from src.models.office import OfficeDocument, WopiToken
from src.models.organization import Organization, OrganizationMembership
from src.storage.s3 import S3StorageClient, S3StorageError, get_storage_client

from .amin_document_ops import (
    answer_document_question,
    execute_instruction,
    extract_document_metadata,
)
from .document_generator import create_document as generate_document

OFFICE_CONTENT_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class OfficeDocumentNotFoundError(Exception):
    pass


class WopiAccessError(Exception):
    pass


class OfficeService:
    """Manage office documents, tokens, and MinIO storage."""

    def __init__(self, db: AsyncSession, storage_client: S3StorageClient | None = None):
        self.db = db
        self.storage_client = storage_client or get_storage_client()

    async def resolve_current_organization(self, ctx: RequestContext) -> Organization:
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        membership_stmt = (
            select(Organization)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                Organization.workspace_id == ctx.workspace.id,
                OrganizationMembership.user_id == ctx.user.id,
            )
            .order_by(OrganizationMembership.role.desc(), Organization.created_at.asc())
        )
        org = (await self.db.execute(membership_stmt)).scalars().first()
        if org is not None:
            return org

        master_stmt = (
            select(Organization)
            .where(
                Organization.workspace_id == ctx.workspace.id,
                Organization.master_user_id == ctx.user.id,
            )
            .order_by(Organization.created_at.asc())
        )
        org = (await self.db.execute(master_stmt)).scalars().first()
        if org is not None:
            return org

        if ctx.has_role("ADMIN"):
            admin_stmt = (
                select(Organization)
                .where(Organization.workspace_id == ctx.workspace.id)
                .order_by(Organization.created_at.asc())
            )
            org = (await self.db.execute(admin_stmt)).scalars().first()
            if org is not None:
                return org

            org = Organization(
                tenant_id=ctx.tenant.id,
                workspace_id=ctx.workspace.id,
                name="Default",
                description="Auto-created default organisation",
                master_user_id=ctx.user.id,
            )
            self.db.add(org)
            await self.db.flush()
            return org

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization is available for the current user.",
        )

    async def accessible_org_ids(self, ctx: RequestContext) -> list[str]:
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        if ctx.has_role("ADMIN"):
            stmt = select(Organization.id).where(Organization.workspace_id == ctx.workspace.id)
            return list((await self.db.execute(stmt)).scalars().all())

        stmt = (
            select(Organization.id)
            .distinct()
            .outerjoin(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                Organization.workspace_id == ctx.workspace.id,
                or_(
                    Organization.master_user_id == ctx.user.id,
                    OrganizationMembership.user_id == ctx.user.id,
                ),
            )
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_document(
        self,
        ctx: RequestContext,
        title: str,
        doc_type: str,
        template: str | None,
    ) -> OfficeDocument:
        org = await self.resolve_current_organization(ctx)
        file_bytes = generate_document(doc_type=doc_type, template=template, title=title)
        doc_id = str(uuid4())
        storage_key = f"office/{org.id}/{doc_id}.{doc_type}"

        metadata = extract_document_metadata(file_bytes, doc_type)
        document = OfficeDocument(
            id=doc_id,
            org_id=org.id,
            owner_id=ctx.user.id,
            title=title,
            doc_type=doc_type,
            storage_key=storage_key,
            size_bytes=len(file_bytes),
            last_modified_by=ctx.user.id,
            metadata_=metadata,
        )

        self.storage_client.put_object(
            key=storage_key,
            data=file_bytes,
            content_type=OFFICE_CONTENT_TYPES[doc_type],
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def list_documents(
        self,
        ctx: RequestContext,
        *,
        limit: int = 50,
        offset: int = 0,
        doc_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[OfficeDocument], int]:
        org_ids = await self.accessible_org_ids(ctx)
        if not org_ids:
            return [], 0

        stmt = select(OfficeDocument).where(OfficeDocument.org_id.in_(org_ids))
        if doc_type:
            stmt = stmt.where(OfficeDocument.doc_type == doc_type)
        if search:
            stmt = stmt.where(OfficeDocument.title.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        result = await self.db.execute(
            stmt.order_by(OfficeDocument.updated_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), int(total)

    async def get_document(self, ctx: RequestContext, doc_id: str) -> OfficeDocument:
        org_ids = await self.accessible_org_ids(ctx)
        stmt = select(OfficeDocument).where(
            OfficeDocument.id == doc_id,
            OfficeDocument.org_id.in_(org_ids or [""]),
        )
        document = (await self.db.execute(stmt)).scalar_one_or_none()
        if document is None:
            raise OfficeDocumentNotFoundError(f"Office document '{doc_id}' not found")
        return document

    async def rename_document(self, ctx: RequestContext, doc_id: str, title: str) -> OfficeDocument:
        document = await self.get_document(ctx, doc_id)
        document.title = title.strip()
        document.updated_at = datetime.now(timezone.utc)
        document.last_modified_by = ctx.user.id
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def delete_document(self, ctx: RequestContext, doc_id: str) -> None:
        document = await self.get_document(ctx, doc_id)
        if not (ctx.has_role("ADMIN") or document.owner_id == ctx.user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only an admin or the document owner can delete this document.",
            )

        try:
            self.storage_client.delete_object(document.storage_key)
        except S3StorageError:
            pass

        await self.db.delete(document)
        await self.db.commit()

    async def download_document(self, document: OfficeDocument) -> tuple[bytes, str]:
        data, content_type = self.storage_client.get_object(document.storage_key)
        return data, content_type

    async def generate_wopi_token(
        self,
        document: OfficeDocument,
        *,
        user_id: str,
        can_write: bool,
    ) -> WopiToken:
        token = WopiToken(
            token=secrets.token_hex(32),
            document_id=document.id,
            user_id=user_id,
            can_write=can_write,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def validate_wopi_token(self, file_id: str, access_token: str) -> tuple[WopiToken, OfficeDocument]:
        stmt = (
            select(WopiToken)
            .options(selectinload(WopiToken.document))
            .where(WopiToken.token == access_token)
        )
        token = (await self.db.execute(stmt)).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if token is None or token.document is None:
            raise WopiAccessError("Invalid WOPI access token.")
        if token.document_id != file_id:
            raise WopiAccessError("WOPI token does not match the requested file.")
        if token.expires_at <= now:
            raise WopiAccessError("WOPI token has expired.")

        token.last_used_at = now
        await self.db.commit()
        return token, token.document

    async def update_document_bytes(
        self,
        document: OfficeDocument,
        *,
        file_bytes: bytes,
        modified_by_user_id: str | None,
    ) -> OfficeDocument:
        self.storage_client.put_object(
            key=document.storage_key,
            data=file_bytes,
            content_type=OFFICE_CONTENT_TYPES[document.doc_type],
        )
        document.size_bytes = len(file_bytes)
        document.updated_at = datetime.now(timezone.utc)
        document.last_modified_by = modified_by_user_id
        document.metadata_ = extract_document_metadata(file_bytes, document.doc_type)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def apply_amin_edit(
        self,
        ctx: RequestContext,
        doc_id: str,
        instruction: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> tuple[OfficeDocument, list[dict[str, Any]], str]:
        document = await self.get_document(ctx, doc_id)
        file_bytes, _content_type = await self.download_document(document)
        new_bytes, ops_applied, summary = await execute_instruction(
            instruction=instruction,
            file_bytes=file_bytes,
            doc_type=document.doc_type,
            context=context or {},
        )
        await self.update_document_bytes(
            document,
            file_bytes=new_bytes,
            modified_by_user_id=ctx.user.id,
        )
        return document, ops_applied, summary


def build_wopi_url(doc_id: str) -> str:
    """Return the WOPI URL used internally by the Collabora server (Docker-internal)."""
    return f"{settings.wopi_internal_url.rstrip('/')}/files/{doc_id}"


def build_wopi_public_url(doc_id: str) -> str:
    """Return the browser-accessible WOPI URL shown in API responses."""
    return f"{settings.wopi_public_url.rstrip('/')}/files/{doc_id}"


def build_collabora_base_url(request: Request | None = None) -> str:  # noqa: ARG001
    """Return the browser-accessible Collabora base URL.

    Always uses settings.collabora_url which must point to a host the browser can reach
    (e.g. http://localhost:9980). Never use Docker-internal hostnames here.
    """
    return settings.collabora_url.rstrip("/")


def build_collabora_editor_url(request: Request | None, doc_id: str, token: str) -> str:
    """Build the full Collabora editor URL sent to the frontend iframe.

    Topology:
      - Collabora base: browser-accessible (settings.collabora_url = localhost:9980)
      - WOPISrc: Docker-internal URL so Collabora server can call the API (api:8000)
    The browser receives and renders this URL; it does not need to reach WOPISrc directly.
    """
    collabora_base = build_collabora_base_url(request)
    wopi_src = quote(build_wopi_url(doc_id), safe="")
    return (
        f"{collabora_base}/browser/dist/cool.html"
        f"?WOPISrc={wopi_src}&access_token={token}"
    )


async def extract_document_metadata_task(doc_id: str) -> None:
    """Refresh metadata for a document in the background."""
    async with async_session_maker() as db:
        service = OfficeService(db)
        document = await db.get(OfficeDocument, doc_id)
        if document is None:
            return
        file_bytes, _content_type = await service.download_document(document)
        document.metadata_ = extract_document_metadata(file_bytes, document.doc_type)
        document.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def read_document_contents(
    db: AsyncSession,
    document: OfficeDocument,
) -> tuple[bytes, str]:
    service = OfficeService(db)
    return await service.download_document(document)


async def answer_office_document_question(
    db: AsyncSession,
    document: OfficeDocument,
    question: str | None,
) -> str:
    file_bytes, _content_type = await read_document_contents(db, document)
    return await answer_document_question(file_bytes, document.doc_type, question)
