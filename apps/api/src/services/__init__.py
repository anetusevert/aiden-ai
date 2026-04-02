"""Services for Aiden.ai API."""

from src.services.audit_service import AuditService, log_audit_event
from src.services.bootstrap_service import BootstrapService
from src.services.clause_detection_service import ClauseDetectionService
from src.services.clause_redlines_service import ClauseRedlinesService
from src.services.contract_review_service import ContractReviewService
from src.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentUploadError,
    DocumentVersionNotFoundError,
    PolicyViolationError,
)
from src.services.embedding_service import EmbeddingService
from src.services.export_service import ExportService
from src.services.extraction_service import ExtractionService
from src.services.policy_service import PolicyService
from src.services.research_service import ResearchService
from src.services.retrieval_service import RetrievalService, SearchFilters, SearchResult
from src.services.tenant_service import TenantService
from src.services.user_service import UserService
from src.services.workspace_membership_service import (
    DuplicateMembershipError,
    LastAdminError,
    MembershipNotFoundError,
    MembershipServiceError,
    UserNotFoundError,
    WorkspaceMembershipService,
)
from src.services.workspace_service import WorkspaceService
from src.utils.hashing import hash_question

__all__ = [
    "AuditService",
    "BootstrapService",
    "ClauseDetectionService",
    "ClauseRedlinesService",
    "ContractReviewService",
    "DocumentNotFoundError",
    "DocumentService",
    "DocumentUploadError",
    "DocumentVersionNotFoundError",
    "DuplicateMembershipError",
    "EmbeddingService",
    "ExportService",
    "ExtractionService",
    "LastAdminError",
    "MembershipNotFoundError",
    "MembershipServiceError",
    "PolicyService",
    "PolicyViolationError",
    "ResearchService",
    "RetrievalService",
    "hash_question",
    "SearchFilters",
    "SearchResult",
    "TenantService",
    "UserNotFoundError",
    "WorkspaceService",
    "UserService",
    "WorkspaceMembershipService",
    "log_audit_event",
]
