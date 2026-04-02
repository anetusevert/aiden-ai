"""Global Legal Service for managing the global law corpus.

This service handles:
- Legal instrument and version CRUD operations
- S3 storage integration for legal documents
- Text extraction and chunking
- Embedding generation for indexed versions
"""

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.dependencies.platform_admin import PlatformAdminContext
from src.embeddings import EmbeddingProvider, get_embedding_provider
from src.extraction import ChunkResult, create_chunks, extract_text
from src.models.legal_chunk import LegalChunk
from src.models.legal_chunk_embedding import LegalChunkEmbedding
from src.models.legal_instrument import LegalInstrument
from src.models.legal_instrument_version import LegalInstrumentVersion
from src.models.legal_text import LegalText
from src.storage.s3 import S3StorageClient, S3StorageError, compute_sha256

logger = logging.getLogger(__name__)


class LegalInstrumentNotFoundError(Exception):
    """Raised when a legal instrument is not found."""

    pass


class LegalVersionNotFoundError(Exception):
    """Raised when a legal instrument version is not found."""

    pass


class LegalUploadError(Exception):
    """Raised when a legal document upload fails."""

    pass


def generate_legal_storage_key(
    instrument_id: str,
    version_id: str,
    filename: str,
) -> str:
    """Generate a unique storage key for a legal instrument version.

    The key structure is:
    global-legal/{instrument_id}/versions/{version_id}/{filename}

    Args:
        instrument_id: Instrument UUID
        version_id: Version UUID
        filename: Original filename

    Returns:
        Storage key string
    """
    # Sanitize filename to prevent path traversal
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"global-legal/{instrument_id}/versions/{version_id}/{safe_filename}"


class GlobalLegalService:
    """Service for managing the global legal corpus."""

    def __init__(
        self,
        db: AsyncSession,
        storage_client: S3StorageClient,
    ):
        """Initialize the global legal service.

        Args:
            db: Async database session
            storage_client: S3 storage client
        """
        self.db = db
        self.storage_client = storage_client

    # =========================================================================
    # Legal Instrument CRUD
    # =========================================================================

    async def create_instrument(
        self,
        ctx: PlatformAdminContext,
        jurisdiction: str,
        instrument_type: str,
        title: str,
        title_ar: str | None = None,
        official_source_url: str | None = None,
        published_at=None,
        effective_at=None,
        status: str = "active",
    ) -> LegalInstrument:
        """Create a new legal instrument.

        Args:
            ctx: Platform admin context
            jurisdiction: GCC jurisdiction code
            instrument_type: Type of legal instrument
            title: Official title in English
            title_ar: Official title in Arabic (optional)
            official_source_url: URL to official source
            published_at: Date of publication
            effective_at: Effective date
            status: Status of the instrument

        Returns:
            Created LegalInstrument
        """
        instrument = LegalInstrument(
            jurisdiction=jurisdiction,
            instrument_type=instrument_type,
            title=title,
            title_ar=title_ar,
            official_source_url=official_source_url,
            published_at=published_at,
            effective_at=effective_at,
            status=status,
            created_by_user_id=ctx.user.id,
        )
        self.db.add(instrument)
        await self.db.flush()
        return instrument

    async def get_instrument(
        self,
        instrument_id: str,
    ) -> LegalInstrument | None:
        """Get a legal instrument by ID.

        Args:
            instrument_id: Instrument ID

        Returns:
            LegalInstrument or None if not found
        """
        result = await self.db.execute(
            select(LegalInstrument)
            .where(LegalInstrument.id == instrument_id)
            .options(selectinload(LegalInstrument.versions))
        )
        return result.scalar_one_or_none()

    async def list_instruments(
        self,
        limit: int = 100,
        offset: int = 0,
        jurisdiction: str | None = None,
        instrument_type: str | None = None,
        status: str | None = None,
    ) -> tuple[Sequence[LegalInstrument], int]:
        """List legal instruments with optional filters.

        Args:
            limit: Maximum number of instruments to return
            offset: Number of instruments to skip
            jurisdiction: Filter by jurisdiction
            instrument_type: Filter by instrument type
            status: Filter by status

        Returns:
            Tuple of (list of instruments, total count)
        """
        # Base query
        base_query = select(LegalInstrument)

        # Apply filters
        if jurisdiction:
            base_query = base_query.where(LegalInstrument.jurisdiction == jurisdiction)
        if instrument_type:
            base_query = base_query.where(LegalInstrument.instrument_type == instrument_type)
        if status:
            base_query = base_query.where(LegalInstrument.status == status)

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar() or 0

        # Get paginated instruments
        result = await self.db.execute(
            base_query.order_by(LegalInstrument.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(LegalInstrument.versions))
        )
        instruments = result.scalars().all()

        return instruments, total

    async def update_instrument(
        self,
        instrument_id: str,
        **updates,
    ) -> LegalInstrument:
        """Update a legal instrument.

        Args:
            instrument_id: Instrument ID
            **updates: Fields to update

        Returns:
            Updated LegalInstrument

        Raises:
            LegalInstrumentNotFoundError: If instrument not found
        """
        instrument = await self.get_instrument(instrument_id)
        if not instrument:
            raise LegalInstrumentNotFoundError(f"Instrument '{instrument_id}' not found")

        for key, value in updates.items():
            if value is not None and hasattr(instrument, key):
                setattr(instrument, key, value)

        instrument.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return instrument

    # =========================================================================
    # Legal Instrument Version CRUD
    # =========================================================================

    async def create_version(
        self,
        ctx: PlatformAdminContext,
        instrument_id: str,
        version_label: str,
        language: str,
        file_name: str,
        content_type: str,
        file_data: bytes,
    ) -> LegalInstrumentVersion:
        """Create a new version for a legal instrument.

        Args:
            ctx: Platform admin context
            instrument_id: Instrument ID
            version_label: Version label (e.g., 'v1.0')
            language: Language of the document
            file_name: Original filename
            content_type: MIME type of the file
            file_data: File content as bytes

        Returns:
            Created LegalInstrumentVersion

        Raises:
            LegalInstrumentNotFoundError: If instrument not found
            LegalUploadError: If file upload fails
        """
        # Verify instrument exists
        instrument = await self.get_instrument(instrument_id)
        if not instrument:
            raise LegalInstrumentNotFoundError(f"Instrument '{instrument_id}' not found")

        # Create version record
        version = LegalInstrumentVersion(
            legal_instrument_id=instrument_id,
            version_label=version_label,
            file_name=file_name,
            content_type=content_type,
            size_bytes=len(file_data),
            storage_provider="s3",
            storage_bucket=self.storage_client.bucket_name,
            storage_key="",  # Will be set after we have the ID
            sha256=compute_sha256(file_data),
            language=language,
            uploaded_by_user_id=ctx.user.id,
        )
        self.db.add(version)
        await self.db.flush()

        # Generate storage key
        storage_key = generate_legal_storage_key(
            instrument_id=instrument_id,
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
            logger.error(f"Failed to upload legal document to S3: {e}")
            raise LegalUploadError(f"Failed to upload file: {e}") from e

        # Extract text and create chunks
        await self._extract_and_index_version(version, file_data, content_type)

        return version

    async def get_version(
        self,
        version_id: str,
    ) -> LegalInstrumentVersion | None:
        """Get a legal instrument version by ID.

        Args:
            version_id: Version ID

        Returns:
            LegalInstrumentVersion or None if not found
        """
        result = await self.db.execute(
            select(LegalInstrumentVersion).where(LegalInstrumentVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def download_version(
        self,
        version_id: str,
    ) -> tuple[bytes, str, str]:
        """Download a legal instrument version.

        Args:
            version_id: Version ID

        Returns:
            Tuple of (file bytes, content type, filename)

        Raises:
            LegalVersionNotFoundError: If version is not found
        """
        version = await self.get_version(version_id)
        if version is None:
            raise LegalVersionNotFoundError(f"Version '{version_id}' not found")

        try:
            data, content_type = self.storage_client.get_object(
                key=version.storage_key,
                bucket=version.storage_bucket,
            )
            return data, content_type, version.file_name
        except S3StorageError as e:
            logger.error(f"Failed to download from S3: {e}")
            raise LegalVersionNotFoundError(f"Failed to download file: {e}") from e

    # =========================================================================
    # Extraction and Indexing
    # =========================================================================

    async def _extract_and_index_version(
        self,
        version: LegalInstrumentVersion,
        file_bytes: bytes,
        content_type: str,
    ) -> tuple[LegalText | None, list[LegalChunk], str | None]:
        """Extract text from a version and create chunks with embeddings.

        Args:
            version: The legal instrument version to process
            file_bytes: File content as bytes
            content_type: MIME type of the file

        Returns:
            Tuple of (LegalText or None, list of LegalChunk, error message or None)
        """
        try:
            # Extract text
            extraction_result = extract_text(file_bytes, content_type)

            # Create text record
            legal_text = LegalText(
                version_id=version.id,
                extracted_text=extraction_result.text,
                extraction_method=extraction_result.method,
                page_count=extraction_result.page_count,
            )
            self.db.add(legal_text)
            version.extracted_text_id = legal_text.id

            # Create chunks
            chunk_results = create_chunks(extraction_result.text)
            legal_chunks: list[LegalChunk] = []

            for chunk_result in chunk_results:
                legal_chunk = LegalChunk(
                    instrument_id=version.legal_instrument_id,
                    version_id=version.id,
                    chunk_index=chunk_result.chunk_index,
                    text=chunk_result.text,
                    char_start=chunk_result.char_start,
                    char_end=chunk_result.char_end,
                    page_start=chunk_result.page_start,
                    page_end=chunk_result.page_end,
                )
                self.db.add(legal_chunk)
                legal_chunks.append(legal_chunk)

            await self.db.flush()

            # Generate embeddings
            if legal_chunks:
                try:
                    provider = get_embedding_provider()
                    for chunk in legal_chunks:
                        embedding_vector = provider.embed_text(chunk.text)
                        embedding = LegalChunkEmbedding(
                            instrument_id=version.legal_instrument_id,
                            version_id=version.id,
                            chunk_id=chunk.id,
                            embedding=embedding_vector,
                            embedding_model=provider.model_name,
                        )
                        self.db.add(embedding)

                    # Update version indexing status
                    version.is_indexed = True
                    version.indexed_at = datetime.now(timezone.utc)
                    version.embedding_model = provider.model_name

                    await self.db.flush()
                    logger.info(
                        f"Generated embeddings for legal version {version.id}: "
                        f"{len(legal_chunks)} chunks"
                    )
                except Exception as embed_error:
                    logger.warning(
                        f"Embedding generation failed for legal version {version.id}: {embed_error}"
                    )

            return legal_text, legal_chunks, None

        except Exception as e:
            logger.error(f"Extraction failed for legal version {version.id}: {e}")
            return None, [], str(e)

    async def reindex_version(
        self,
        version_id: str,
        replace_existing: bool = True,
    ) -> tuple[int, int]:
        """Re-run extraction/chunking/embedding for a version.

        Args:
            version_id: Version ID to reindex
            replace_existing: If True, delete existing chunks and regenerate

        Returns:
            Tuple of (chunks_indexed, chunks_skipped)

        Raises:
            LegalVersionNotFoundError: If version not found
        """
        version = await self.get_version(version_id)
        if not version:
            raise LegalVersionNotFoundError(f"Version '{version_id}' not found")

        if replace_existing:
            # Delete existing chunks and embeddings (cascade handles embeddings)
            await self.db.execute(
                delete(LegalChunk).where(LegalChunk.version_id == version_id)
            )
            # Delete existing text
            await self.db.execute(
                delete(LegalText).where(LegalText.version_id == version_id)
            )
            await self.db.flush()

        # Download file from S3
        file_bytes, content_type, _ = await self.download_version(version_id)

        # Re-extract and index
        _, chunks, error = await self._extract_and_index_version(
            version, file_bytes, content_type
        )

        if error:
            version.is_indexed = False
            await self.db.flush()
            return 0, 0

        return len(chunks), 0

    async def get_version_chunks(
        self,
        version_id: str,
    ) -> Sequence[LegalChunk]:
        """Get all chunks for a legal instrument version.

        Args:
            version_id: Version ID

        Returns:
            List of LegalChunk ordered by chunk_index
        """
        result = await self.db.execute(
            select(LegalChunk)
            .where(LegalChunk.version_id == version_id)
            .order_by(LegalChunk.chunk_index)
        )
        return result.scalars().all()
