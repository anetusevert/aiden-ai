"""WOPI endpoints for Collabora Online."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.user import User
from src.services.office_service import (
    OFFICE_CONTENT_TYPES,
    OfficeService,
    WopiAccessError,
    extract_document_metadata_task,
)

router = APIRouter(prefix="/api/v1/wopi", tags=["wopi"])


def _wopi_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stream_chunks(stream) -> Iterator[bytes]:
    try:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


@router.get("/files/{file_id}")
async def check_file_info(
    file_id: str,
    access_token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        token, document = await service.validate_wopi_token(file_id, access_token)
    except WopiAccessError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = await db.get(User, token.user_id)
    return {
        "BaseFileName": f"{document.title}.{document.doc_type}",
        "Size": document.size_bytes,
        "UserId": str(token.user_id),
        "UserFriendlyName": user.full_name if user and user.full_name else "HeyAmin User",
        "UserCanWrite": token.can_write,
        "SupportsUpdate": token.can_write,
        "SupportsLocks": False,
        "LastModifiedTime": _wopi_timestamp(document.updated_at),
    }


@router.get("/files/{file_id}/contents")
async def get_file(
    file_id: str,
    access_token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        _token, document = await service.validate_wopi_token(file_id, access_token)
    except WopiAccessError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    stream, content_type, _content_length = service.storage_client.get_object_stream(
        document.storage_key
    )
    headers = {
        "Content-Disposition": f'attachment; filename="{document.title}.{document.doc_type}"',
    }
    return StreamingResponse(
        _stream_chunks(stream),
        media_type=content_type or OFFICE_CONTENT_TYPES[document.doc_type],
        headers=headers,
    )


@router.post("/files/{file_id}/contents")
async def put_file(
    file_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    access_token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    service = OfficeService(db)
    try:
        token, document = await service.validate_wopi_token(file_id, access_token)
    except WopiAccessError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if not token.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This WOPI token does not permit writes.",
        )

    file_bytes = await request.body()
    await service.update_document_bytes(
        document,
        file_bytes=file_bytes,
        modified_by_user_id=token.user_id,
    )
    background_tasks.add_task(extract_document_metadata_task, document.id)
    return {"LastModifiedTime": _wopi_timestamp(document.updated_at)}
