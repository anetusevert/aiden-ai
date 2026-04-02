"""Pydantic schemas for Aiden.ai API."""

from src.schemas.audit import AuditLogListResponse, AuditLogResponse
from src.schemas.auth import CurrentUserResponse, DevLoginRequest, TokenResponse
from src.schemas.contract_review import (
    ContractReviewMeta,
    ContractReviewRequest,
    ContractReviewResponse,
    EvidenceChunkRef,
    Finding,
)
from src.schemas.document import (
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentVersionCreateResponse,
    DocumentVersionResponse,
    DocumentVersionSummary,
    DocumentWithLatestVersionResponse,
    DocumentWithVersionsResponse,
)
from src.schemas.policy import (
    AttachPolicyRequest,
    PolicyConfig,
    PolicyProfileCreate,
    PolicyProfileResponse,
    PolicyProfileUpdate,
    PolicyResolveResponse,
    ResolvedPolicy,
)
from src.schemas.tenant import (
    BootstrapPayload,
    BootstrapResponse,
    TenantCreate,
    TenantCreateWithBootstrap,
    TenantResponse,
)
from src.schemas.user import UserCreate, UserResponse
from src.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from src.schemas.workspace_membership import (
    MemberInviteRequest,
    MemberRoleUpdateRequest,
    MemberWithUserResponse,
    WorkspaceMembershipCreate,
    WorkspaceMembershipResponse,
)

__all__ = [
    "AuditLogListResponse",
    "AuditLogResponse",
    "ContractReviewMeta",
    "ContractReviewRequest",
    "ContractReviewResponse",
    "DocumentCreateResponse",
    "DocumentListResponse",
    "DocumentResponse",
    "DocumentVersionCreateResponse",
    "DocumentVersionResponse",
    "DocumentVersionSummary",
    "DocumentWithLatestVersionResponse",
    "DocumentWithVersionsResponse",
    "EvidenceChunkRef",
    "Finding",
    "TenantCreate",
    "TenantCreateWithBootstrap",
    "TenantResponse",
    "BootstrapPayload",
    "BootstrapResponse",
    "WorkspaceCreate",
    "WorkspaceResponse",
    "UserCreate",
    "UserResponse",
    "MemberInviteRequest",
    "MemberRoleUpdateRequest",
    "MemberWithUserResponse",
    "WorkspaceMembershipCreate",
    "WorkspaceMembershipResponse",
    "DevLoginRequest",
    "TokenResponse",
    "CurrentUserResponse",
    "PolicyConfig",
    "PolicyProfileCreate",
    "PolicyProfileUpdate",
    "PolicyProfileResponse",
    "AttachPolicyRequest",
    "ResolvedPolicy",
    "PolicyResolveResponse",
]
