"""Embedding service for generating and storing document chunk embeddings.

This service handles:
- Generating embeddings for document chunks
- Storing embeddings in the database
- Idempotent updates (skip or update if exists)
- Updating document version indexing status
"""

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.embeddings import EmbeddingProvider, get_embedding_provider
from src.models.document_chunk import DocumentChunk
from src.models.document_chunk_embedding import DocumentChunkEmbedding
from src.models.document_version import DocumentVersion

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and storing document chunk embeddings."""

    def __init__(
        self,
        db: AsyncSession,
        provider: EmbeddingProvider | None = None,
    ):
        """Initialize the embedding service.

        Args:
            db: Async database session
            provider: Embedding provider (defaults to global provider)
        """
        self.db = db
        self.provider = provider or get_embedding_provider()

    async def generate_embeddings_for_chunks(
        self,
        ctx: RequestContext,
        chunks: Sequence[DocumentChunk],
        *,
        skip_existing: bool = True,
    ) -> tuple[int, int]:
        """Generate embeddings for a list of document chunks.

        This method is idempotent - if embeddings already exist for a chunk,
        they are skipped (when skip_existing=True) or replaced.

        Args:
            ctx: Request context with tenant/workspace info
            chunks: List of DocumentChunk objects to embed
            skip_existing: If True, skip chunks that already have embeddings

        Returns:
            Tuple of (created_count, skipped_count)
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        if not chunks:
            return 0, 0

        created_count = 0
        skipped_count = 0

        # Get existing embeddings for these chunks
        chunk_ids = [chunk.id for chunk in chunks]
        existing_result = await self.db.execute(
            select(DocumentChunkEmbedding.chunk_id).where(
                and_(
                    DocumentChunkEmbedding.chunk_id.in_(chunk_ids),
                    DocumentChunkEmbedding.tenant_id == ctx.tenant.id,
                )
            )
        )
        existing_chunk_ids = set(existing_result.scalars().all())

        for chunk in chunks:
            if chunk.id in existing_chunk_ids:
                if skip_existing:
                    skipped_count += 1
                    continue
                else:
                    # Delete existing embedding before creating new one
                    await self.db.execute(
                        delete(DocumentChunkEmbedding).where(
                            DocumentChunkEmbedding.chunk_id == chunk.id
                        )
                    )

            # Generate embedding as list[float]
            embedding_vector = self.provider.embed_text(chunk.text)

            # Create embedding record with native pgvector storage
            embedding = DocumentChunkEmbedding(
                tenant_id=chunk.tenant_id,
                workspace_id=chunk.workspace_id,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                chunk_id=chunk.id,
                embedding=embedding_vector,  # Native list[float] for pgvector
                embedding_model=self.provider.model_name,
            )
            self.db.add(embedding)
            created_count += 1

        await self.db.flush()
        return created_count, skipped_count

    async def generate_embeddings_for_version(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
        *,
        replace_existing: bool = False,
    ) -> tuple[int, int]:
        """Generate embeddings for all chunks in a document version.

        On success, updates the document version's indexing status:
        - is_indexed = True
        - indexed_at = current timestamp
        - embedding_model = current provider model name

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID
            replace_existing: If True, replace existing embeddings

        Returns:
            Tuple of (created_count, skipped_count)
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        # Get all chunks for this version
        result = await self.db.execute(
            select(DocumentChunk).where(
                and_(
                    DocumentChunk.version_id == version_id,
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.tenant_id == ctx.tenant.id,
                    DocumentChunk.workspace_id == ctx.workspace.id,
                )
            )
        )
        chunks = result.scalars().all()

        if not chunks:
            # No chunks to embed, but mark as indexed (empty index is still indexed)
            await self._update_version_index_status(version_id, success=True)
            return 0, 0

        created, skipped = await self.generate_embeddings_for_chunks(
            ctx,
            list(chunks),
            skip_existing=not replace_existing,
        )

        # Update version indexing status on success
        await self._update_version_index_status(version_id, success=True)

        return created, skipped

    async def _update_version_index_status(
        self,
        version_id: str,
        *,
        success: bool,
    ) -> None:
        """Update the indexing status of a document version.

        Args:
            version_id: Version ID to update
            success: Whether indexing was successful
        """
        result = await self.db.execute(
            select(DocumentVersion).where(DocumentVersion.id == version_id)
        )
        version = result.scalar_one_or_none()

        if version:
            if success:
                version.is_indexed = True
                version.indexed_at = datetime.now(timezone.utc)
                version.embedding_model = self.provider.model_name
            else:
                version.is_indexed = False
                # Keep indexed_at and embedding_model for debugging
            await self.db.flush()

    async def delete_embeddings_for_version(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
    ) -> int:
        """Delete all embeddings for a document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            Number of embeddings deleted
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        result = await self.db.execute(
            delete(DocumentChunkEmbedding).where(
                and_(
                    DocumentChunkEmbedding.version_id == version_id,
                    DocumentChunkEmbedding.document_id == document_id,
                    DocumentChunkEmbedding.tenant_id == ctx.tenant.id,
                    DocumentChunkEmbedding.workspace_id == ctx.workspace.id,
                )
            )
        )
        await self.db.flush()
        return result.rowcount

    async def get_embeddings_for_version(
        self,
        ctx: RequestContext,
        document_id: str,
        version_id: str,
    ) -> Sequence[DocumentChunkEmbedding]:
        """Get all embeddings for a document version.

        Args:
            ctx: Request context
            document_id: Document ID
            version_id: Version ID

        Returns:
            List of DocumentChunkEmbedding objects
        """
        if ctx.workspace is None:
            raise ValueError("Workspace context required")

        result = await self.db.execute(
            select(DocumentChunkEmbedding).where(
                and_(
                    DocumentChunkEmbedding.version_id == version_id,
                    DocumentChunkEmbedding.document_id == document_id,
                    DocumentChunkEmbedding.tenant_id == ctx.tenant.id,
                    DocumentChunkEmbedding.workspace_id == ctx.workspace.id,
                )
            )
        )
        return result.scalars().all()
