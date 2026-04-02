"""Extraction service for processing document text.

Orchestrates:
- Text extraction from PDFs and DOCX files
- Chunking of extracted text
- Storage of results
- Embedding generation for chunks
- Audit logging
"""

import logging
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.extraction import ChunkResult, ExtractionResult, create_chunks, extract_text
from src.models.document_chunk import DocumentChunk
from src.models.document_text import DocumentText
from src.models.document_version import DocumentVersion

logger = logging.getLogger(__name__)


class ExtractionService:
    """Service for extracting and chunking document text."""

    def __init__(self, db: AsyncSession):
        """Initialize the extraction service.

        Args:
            db: Async database session
        """
        self.db = db

    async def extract_and_store(
        self,
        ctx: RequestContext,
        version: DocumentVersion,
        file_bytes: bytes,
        content_type: str,
        *,
        generate_embeddings: bool = True,
    ) -> tuple[DocumentText | None, list[DocumentChunk], str | None]:
        """Extract text from a document version and store results.

        This is the main entry point for extraction. It:
        1. Extracts text using appropriate extractor
        2. Creates chunks from extracted text
        3. Stores DocumentText and DocumentChunk records
        4. Generates embeddings for chunks (if enabled)

        Args:
            ctx: Request context with tenant/workspace info
            version: The document version to process
            file_bytes: File content as bytes
            content_type: MIME type of the file
            generate_embeddings: Whether to generate embeddings for chunks (default True)

        Returns:
            Tuple of (DocumentText or None, list of DocumentChunk, error message or None)
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        try:
            # Extract text
            extraction_result = extract_text(file_bytes, content_type)

            # Create text record
            doc_text = DocumentText(
                tenant_id=ctx.tenant.id,
                workspace_id=ctx.workspace.id,
                document_id=version.document_id,
                version_id=version.id,
                extracted_text=extraction_result.text,
                extraction_method=extraction_result.method,
                page_count=extraction_result.page_count,
            )
            self.db.add(doc_text)

            # Create chunks
            chunk_results = create_chunks(extraction_result.text)
            doc_chunks: list[DocumentChunk] = []

            for chunk_result in chunk_results:
                doc_chunk = DocumentChunk(
                    tenant_id=ctx.tenant.id,
                    workspace_id=ctx.workspace.id,
                    document_id=version.document_id,
                    version_id=version.id,
                    chunk_index=chunk_result.chunk_index,
                    text=chunk_result.text,
                    char_start=chunk_result.char_start,
                    char_end=chunk_result.char_end,
                    page_start=chunk_result.page_start,
                    page_end=chunk_result.page_end,
                )
                self.db.add(doc_chunk)
                doc_chunks.append(doc_chunk)

            await self.db.flush()

            # Generate embeddings for chunks
            if generate_embeddings and doc_chunks:
                try:
                    from src.services.embedding_service import EmbeddingService

                    embedding_service = EmbeddingService(self.db)
                    created, skipped = await embedding_service.generate_embeddings_for_chunks(
                        ctx, doc_chunks, skip_existing=True
                    )
                    logger.info(
                        f"Generated embeddings for version {version.id}: "
                        f"{created} created, {skipped} skipped"
                    )
                except Exception as embed_error:
                    # Log but don't fail extraction if embedding fails
                    logger.warning(
                        f"Embedding generation failed for version {version.id}: {embed_error}"
                    )

            return doc_text, doc_chunks, None

        except Exception as e:
            logger.error(f"Extraction failed for version {version.id}: {e}")
            # Return error but don't crash - caller should handle
            return None, [], str(e)

    async def get_document_text(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
    ) -> DocumentText | None:
        """Get extracted text for a document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            DocumentText or None if not found
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        result = await self.db.execute(
            select(DocumentText).where(
                and_(
                    DocumentText.version_id == version_id,
                    DocumentText.document_id == document_id,
                    DocumentText.tenant_id == ctx.tenant.id,
                    DocumentText.workspace_id == ctx.workspace.id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_document_chunks(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
    ) -> Sequence[DocumentChunk]:
        """Get chunks for a document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            List of DocumentChunk ordered by chunk_index
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        result = await self.db.execute(
            select(DocumentChunk)
            .where(
                and_(
                    DocumentChunk.version_id == version_id,
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.tenant_id == ctx.tenant.id,
                    DocumentChunk.workspace_id == ctx.workspace.id,
                )
            )
            .order_by(DocumentChunk.chunk_index)
        )
        return result.scalars().all()
