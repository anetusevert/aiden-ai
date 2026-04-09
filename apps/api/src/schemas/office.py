"""Schemas for Office document APIs."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

OfficeDocType = Literal["docx", "xlsx", "pptx", "pdf"]


class OfficeDocumentCreate(BaseModel):
    title: str
    doc_type: OfficeDocType
    template: str | None = None


class OfficeDocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class OfficeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    owner_id: str
    title: str
    doc_type: OfficeDocType
    storage_key: str
    size_bytes: int
    last_modified_by: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata_: dict[str, Any] = Field(default_factory=dict)
    wopi_url: str
    collabora_url: str


class OfficeDocumentListResponse(BaseModel):
    items: list[OfficeDocumentResponse]
    total: int
    limit: int
    offset: int


class OfficeDocumentCountResponse(BaseModel):
    count: int


class WopiTokenResponse(BaseModel):
    token: str
    collabora_editor_url: str
    expires_at: datetime


class OfficeDocumentAminEditRequest(BaseModel):
    instruction: str


class OfficeDocumentAminEditResponse(BaseModel):
    success: bool
    ops_applied: list[dict[str, Any]]
    summary: str
