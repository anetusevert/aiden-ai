"""Document service for document vault operations.

This service handles:
- Document and version CRUD operations
- S3 storage integration
- Policy enforcement at upload time
- Text extraction and chunking (via ExtractionService)
"""

import logging
from typing import TYPE_CHECKING, Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dependencies.auth import RequestContext
from src.models.document import Document
from src.models.document_version import DocumentVersion
from src.schemas.policy import PolicyConfig
from src.services.policy_service import BUILTIN_DEFAULT_POLICY, PolicyService
from src.storage.s3 import (
    S3StorageClient,
    S3StorageError,
    compute_sha256,
    generate_storage_key,
)

if TYPE_CHECKING:
    from src.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""

    pass


class DocumentVersionNotFoundError(Exception):
    """Raised when a document version is not found."""

    pass


class PolicyViolationError(Exception):
    """Raised when a policy violation is detected."""

    def __init__(self, message: str, reason: str):
        super().__init__(message)
        self.reason = reason


class DocumentUploadError(Exception):
    """Raised when a document upload fails."""

    pass


class DocumentService:
    """Service for document vault operations."""

    def __init__(
        self,
        db: AsyncSession,
        storage_client: S3StorageClient,
    ):
        """Initialize the document service.

        Args:
            db: Async database session
            storage_client: S3 storage client
        """
        self.db = db
        self.storage_client = storage_client

    async def _get_effective_policy_config(
        self,
        ctx: RequestContext,
    ) -> PolicyConfig:
        """Get the effective policy configuration for the workspace.

        Args:
            ctx: Request context with tenant/workspace info

        Returns:
            PolicyConfig for the workspace
        """
        policy_service = PolicyService(self.db)
        resolved = await policy_service.resolve(ctx)
        return resolved.config

    async def validate_policy_constraints(
        self,
        ctx: RequestContext,
        language: str,
        jurisdiction: str,
    ) -> None:
        """Validate that the document meets policy constraints.

        Args:
            ctx: Request context with tenant/workspace info
            language: Document language
            jurisdiction: Document jurisdiction

        Raises:
            PolicyViolationError: If policy constraints are violated
        """
        policy_config = await self._get_effective_policy_config(ctx)

        # Check allowed input languages
        if language not in policy_config.allowed_input_languages:
            raise PolicyViolationError(
                f"Language '{language}' is not allowed by workspace policy. "
                f"Allowed languages: {policy_config.allowed_input_languages}",
                reason="language_not_allowed",
            )

        # Check allowed jurisdictions
        if jurisdiction not in policy_config.allowed_jurisdictions:
            raise PolicyViolationError(
                f"Jurisdiction '{jurisdiction}' is not allowed by workspace policy. "
                f"Allowed jurisdictions: {policy_config.allowed_jurisdictions}",
                reason="jurisdiction_not_allowed",
            )

    async def create_document(
        self,
        ctx: RequestContext,
        title: str,
        document_type: str,
        jurisdiction: str,
        language: str,
        confidentiality: str,
        file_name: str,
        content_type: str,
        file_data: bytes,
    ) -> tuple[Document, DocumentVersion]:
        """Create a new document with initial version.

        Args:
            ctx: Request context with tenant/workspace info
            title: Document title
            document_type: Document type (contract, policy, memo, regulatory, other)
            jurisdiction: Document jurisdiction (UAE, DIFC, ADGM, KSA)
            language: Document language (en, ar, mixed)
            confidentiality: Confidentiality level
            file_name: Original filename
            content_type: MIME type of the file
            file_data: File content as bytes

        Returns:
            Tuple of (Document, DocumentVersion)

        Raises:
            PolicyViolationError: If policy constraints are violated
            DocumentUploadError: If file upload fails
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        # Validate policy constraints
        await self.validate_policy_constraints(ctx, language, jurisdiction)

        # Create document
        document = Document(
            tenant_id=ctx.tenant.id,
            workspace_id=ctx.workspace.id,
            title=title,
            document_type=document_type,
            jurisdiction=jurisdiction,
            language=language,
            confidentiality=confidentiality,
            created_by_user_id=ctx.user.id,
        )
        self.db.add(document)
        await self.db.flush()  # Get document.id

        # Create version
        version = await self._create_version(
            ctx=ctx,
            document=document,
            version_number=1,
            file_name=file_name,
            content_type=content_type,
            file_data=file_data,
        )

        await self.db.commit()
        await self.db.refresh(document)
        await self.db.refresh(version)

        return document, version

    async def create_version(
        self,
        ctx: RequestContext,
        document_id: str,
        file_name: str,
        content_type: str,
        file_data: bytes,
    ) -> DocumentVersion:
        """Create a new version for an existing document.

        Args:
            ctx: Request context with tenant/workspace info
            document_id: Document ID
            file_name: Original filename
            content_type: MIME type of the file
            file_data: File content as bytes

        Returns:
            DocumentVersion

        Raises:
            DocumentNotFoundError: If document is not found
            DocumentUploadError: If file upload fails
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        # Get document
        document = await self.get_document(ctx, document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document '{document_id}' not found")

        # Get next version number
        next_version = await self._get_next_version_number(document_id)

        # Create version
        version = await self._create_version(
            ctx=ctx,
            document=document,
            version_number=next_version,
            file_name=file_name,
            content_type=content_type,
            file_data=file_data,
        )

        await self.db.commit()
        await self.db.refresh(version)

        return version

    async def _create_version(
        self,
        ctx: RequestContext,
        document: Document,
        version_number: int,
        file_name: str,
        content_type: str,
        file_data: bytes,
    ) -> DocumentVersion:
        """Internal method to create a document version.

        Args:
            ctx: Request context
            document: Parent document
            version_number: Version number
            file_name: Original filename
            content_type: MIME type
            file_data: File content as bytes

        Returns:
            DocumentVersion

        Raises:
            DocumentUploadError: If file upload fails
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        # Create version record first to get ID
        version = DocumentVersion(
            tenant_id=ctx.tenant.id,
            workspace_id=ctx.workspace.id,
            document_id=document.id,
            version_number=version_number,
            file_name=file_name,
            content_type=content_type,
            size_bytes=len(file_data),
            storage_provider="s3",
            storage_bucket=self.storage_client.bucket_name,
            storage_key="",  # Will be set after we have the ID
            sha256=compute_sha256(file_data),
            uploaded_by_user_id=ctx.user.id,
        )
        self.db.add(version)
        await self.db.flush()  # Get version.id

        # Generate storage key
        storage_key = generate_storage_key(
            tenant_id=ctx.tenant.id,
            workspace_id=ctx.workspace.id,
            document_id=document.id,
            version_id=version.id,
            filename=file_name,
        )
        version.storage_key = storage_key

        # Upload to S3
        try:
            self.storage_client.put_object(
                key=storage_key,
                data=file_data,
                content_type=content_type,
            )
        except S3StorageError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise DocumentUploadError(f"Failed to upload file: {e}") from e

        return version

    async def _get_next_version_number(self, document_id: str) -> int:
        """Get the next version number for a document.

        Args:
            document_id: Document ID

        Returns:
            Next version number (max + 1)
        """
        result = await self.db.execute(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        max_version = result.scalar() or 0
        return max_version + 1

    async def get_document(
        self,
        ctx: RequestContext,
        document_id: str,
    ) -> Document | None:
        """Get a document by ID.

        Args:
            ctx: Request context with tenant/workspace info
            document_id: Document ID

        Returns:
            Document or None if not found
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        result = await self.db.execute(
            select(Document)
            .where(
                and_(
                    Document.id == document_id,
                    Document.tenant_id == ctx.tenant.id,
                    Document.workspace_id == ctx.workspace.id,
                )
            )
            .options(selectinload(Document.versions))
        )
        return result.scalar_one_or_none()

    async def get_document_with_versions(
        self,
        ctx: RequestContext,
        document_id: str,
    ) -> Document | None:
        """Get a document with all versions loaded.

        Args:
            ctx: Request context
            document_id: Document ID

        Returns:
            Document with versions loaded, or None
        """
        return await self.get_document(ctx, document_id)

    async def list_documents(
        self,
        ctx: RequestContext,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[Document], int]:
        """List documents in a workspace.

        Args:
            ctx: Request context
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            Tuple of (list of documents, total count)
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        # Base query
        base_query = select(Document).where(
            and_(
                Document.tenant_id == ctx.tenant.id,
                Document.workspace_id == ctx.workspace.id,
            )
        )

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        # Get paginated documents
        result = await self.db.execute(
            base_query.order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Document.versions))
        )
        documents = result.scalars().all()

        return documents, total

    async def get_version(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
    ) -> DocumentVersion | None:
        """Get a specific document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            DocumentVersion or None
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        result = await self.db.execute(
            select(DocumentVersion).where(
                and_(
                    DocumentVersion.id == version_id,
                    DocumentVersion.document_id == document_id,
                    DocumentVersion.tenant_id == ctx.tenant.id,
                    DocumentVersion.workspace_id == ctx.workspace.id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def download_version(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
    ) -> tuple[bytes, str, str]:
        """Download a document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            Tuple of (file bytes, content type, filename)

        Raises:
            DocumentVersionNotFoundError: If version is not found
        """
        version = await self.get_version(ctx, document_id, version_id)
        if version is None:
            raise DocumentVersionNotFoundError(
                f"Version '{version_id}' not found for document '{document_id}'"
            )

        # Download from S3
        try:
            data, content_type = self.storage_client.get_object(
                key=version.storage_key,
                bucket=version.storage_bucket,
            )
            return data, content_type, version.file_name
        except S3StorageError as e:
            logger.error(f"Failed to download from S3: {e}")
            raise DocumentVersionNotFoundError(
                f"Failed to download file: {e}"
            ) from e

    async def extract_version_text(
        self,
        ctx: RequestContext,
        version: DocumentVersion,
        file_bytes: bytes,
        content_type: str,
    ) -> tuple[bool, dict]:
        """Extract text from a document version and store it.

        This should be called after a version is successfully created.
        It will not raise exceptions - failures are returned as metadata.

        Args:
            ctx: Request context
            version: The document version to extract
            file_bytes: File content as bytes
            content_type: MIME type of the file

        Returns:
            Tuple of (success: bool, metadata: dict for audit logging)
        """
        from src.services.extraction_service import ExtractionService

        extraction_service = ExtractionService(self.db)

        try:
            doc_text, doc_chunks, error = await extraction_service.extract_and_store(
                ctx=ctx,
                version=version,
                file_bytes=file_bytes,
                content_type=content_type,
            )

            if error:
                return False, {
                    "method": doc_text.extraction_method if doc_text else "unknown",
                    "error": error,
                }

            if doc_text is None:
                return False, {
                    "method": "unknown",
                    "error": "Extraction returned no result",
                }

            return True, {
                "method": doc_text.extraction_method,
                "page_count": doc_text.page_count,
                "chunk_count": len(doc_chunks),
                "text_length": len(doc_text.extracted_text),
            }

        except Exception as e:
            logger.error(f"Extraction failed for version {version.id}: {e}")
            return False, {
                "method": "unknown",
                "error": str(e),
            }
