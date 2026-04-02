"""Global Legal Import Service for ingesting gcc-harvester snapshots.

This service handles bulk import of legal instruments from gcc-harvester ZIP snapshots.
See docs/IMPORT_CONTRACT.md for the full specification.
"""

import hashlib
import json
import logging
import os
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any, BinaryIO
from uuid import uuid4

from sqlalchemy import and_, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.legal_chunk import LegalChunk
from src.models.legal_chunk_embedding import LegalChunkEmbedding
from src.models.legal_instrument import LEGAL_INSTRUMENT_TYPES, LegalInstrument
from src.models.legal_instrument_version import LegalInstrumentVersion
from src.models.legal_text import LegalText
from src.services.global_legal_service import generate_legal_storage_key
from src.storage.s3 import S3StorageClient, S3StorageError, compute_sha256

logger = logging.getLogger(__name__)

# Import limits
MAX_RECORDS_PER_IMPORT = 5000
MAX_ZIP_SIZE_BYTES = 500 * 1024 * 1024  # 500 MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class SnapshotImportError(Exception):
    """Base exception for snapshot import errors."""

    pass


class ZipSlipError(SnapshotImportError):
    """Raised when a zip-slip path traversal attack is detected."""

    pass


class RecordLimitExceededError(SnapshotImportError):
    """Raised when the number of records exceeds the limit."""

    pass


class InvalidManifestError(SnapshotImportError):
    """Raised when the manifest.json is invalid or missing."""

    pass


class ZipSizeLimitExceededError(SnapshotImportError):
    """Raised when the ZIP file size exceeds the limit."""

    pass


class FileSizeLimitExceededError(SnapshotImportError):
    """Raised when an individual file size exceeds the limit."""

    pass


@dataclass
class ImportFailure:
    """Represents a single import failure."""

    record_index: int
    source_url: str | None
    error: str


@dataclass
class ImportResult:
    """Result of a snapshot import operation."""

    import_batch_id: str
    instruments_created: int = 0
    instruments_existing: int = 0
    versions_created: int = 0
    versions_existing: int = 0
    failures: list[ImportFailure] = field(default_factory=list)
    failure_count: int = 0
    processing_time_ms: int = 0

    def add_failure(self, record_index: int, source_url: str | None, error: str) -> None:
        """Add a failure to the result (caps at 20 for response)."""
        self.failure_count += 1
        if len(self.failures) < 20:
            self.failures.append(ImportFailure(
                record_index=record_index,
                source_url=source_url,
                error=error,
            ))


@dataclass
class HarvesterRecord:
    """Parsed record from gcc-harvester JSONL."""

    jurisdiction: str
    source_name: str
    source_url: str
    retrieved_at: str
    title_ar: str
    instrument_type_guess: str
    published_at_guess: str | None
    raw_artifact_path: str
    raw_sha256: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HarvesterRecord":
        """Parse a record from a dictionary."""
        return cls(
            jurisdiction=data.get("jurisdiction", ""),
            source_name=data.get("source_name", ""),
            source_url=data.get("source_url", ""),
            retrieved_at=data.get("retrieved_at", ""),
            title_ar=data.get("title_ar", ""),
            instrument_type_guess=data.get("instrument_type_guess", "other"),
            published_at_guess=data.get("published_at_guess"),
            raw_artifact_path=data.get("raw_artifact_path", ""),
            raw_sha256=data.get("raw_sha256", ""),
        )

    def validate(self) -> str | None:
        """Validate the record. Returns error message or None if valid."""
        if not self.jurisdiction:
            return "Missing jurisdiction"
        if not self.source_url:
            return "Missing source_url"
        if not self.title_ar:
            return "Missing title_ar"
        if not self.raw_artifact_path:
            return "Missing raw_artifact_path"
        if not self.raw_sha256:
            return "Missing raw_sha256"
        return None


def compute_instrument_key(jurisdiction: str, source_name: str, source_url: str) -> str:
    """Compute the instrument dedupe key.

    Format: {jurisdiction}:{source_name}:{sha256(source_url)}
    Uses FULL 64-char lowercase hex SHA256 (no truncation).
    """
    url_hash = hashlib.sha256(source_url.encode()).hexdigest()
    return f"{jurisdiction}:{source_name}:{url_hash}"


def parse_file_ext_from_artifact_path(raw_artifact_path: str) -> str:
    """Parse the file extension from raw_artifact_path.

    Expected format: raw/<sha256>.<ext>

    Args:
        raw_artifact_path: Path like "raw/abc123def456.pdf"

    Returns:
        Extension without dot (e.g., "pdf"), or empty string if none.
    """
    # Get the filename part
    filename = PurePosixPath(raw_artifact_path).name
    # Split by dot and get last part
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


def infer_content_type(ext: str) -> str:
    """Infer MIME content type from file extension.

    Args:
        ext: File extension without dot (e.g., "pdf")

    Returns:
        MIME type string
    """
    content_type_map = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "txt": "text/plain",
        "html": "text/html",
        "htm": "text/html",
    }
    return content_type_map.get(ext, "application/octet-stream")


def is_safe_zip_path(path: str, extract_base: str = "") -> bool:
    """Check if a zip path is safe (no path traversal).

    Args:
        path: The path from the zip file
        extract_base: Base directory for extraction (default: current directory)

    Returns:
        True if the path is safe, False if it contains traversal
    """
    # Normalize the path
    normalized = os.path.normpath(path)

    # Check for absolute paths
    if os.path.isabs(normalized):
        return False

    # Check for parent directory references
    if normalized.startswith("..") or "/../" in normalized or normalized == "..":
        return False

    # Check that the resolved path stays within the base
    if extract_base:
        full_path = os.path.normpath(os.path.join(extract_base, normalized))
        if not full_path.startswith(os.path.normpath(extract_base)):
            return False

    return True


def normalize_instrument_type(type_guess: str) -> str:
    """Normalize instrument type to valid enum value."""
    type_guess = type_guess.lower().strip().replace(" ", "_").replace("-", "_")
    if type_guess in LEGAL_INSTRUMENT_TYPES:
        return type_guess
    return "other"


def parse_date_guess(date_str: str | None) -> date | None:
    """Parse a date string guess. Returns None if unparseable."""
    if not date_str:
        return None
    try:
        # Try ISO format first
        return date.fromisoformat(date_str[:10])
    except ValueError:
        pass
    try:
        # Try other common formats
        from dateutil.parser import parse as dateutil_parse
        parsed = dateutil_parse(date_str)
        return parsed.date()
    except Exception:
        return None


class GlobalLegalImportService:
    """Service for importing gcc-harvester snapshots into the global legal corpus."""

    def __init__(
        self,
        db: AsyncSession,
        storage_client: S3StorageClient,
    ):
        """Initialize the import service.

        Args:
            db: Async database session
            storage_client: S3 storage client
        """
        self.db = db
        self.storage_client = storage_client

    async def import_snapshot(
        self,
        zip_file: BinaryIO,
        filename: str,
        user_id: str | None = None,
    ) -> ImportResult:
        """Import a gcc-harvester snapshot ZIP file.

        Args:
            zip_file: The ZIP file as a binary stream
            filename: Original filename for logging
            user_id: ID of the user performing the import (for audit)

        Returns:
            ImportResult with counts and any failures

        Raises:
            ZipSlipError: If path traversal is detected
            RecordLimitExceededError: If too many records
            InvalidManifestError: If manifest is invalid
        """
        start_time = datetime.now(timezone.utc)
        import_batch_id = str(uuid4())
        result = ImportResult(import_batch_id=import_batch_id)

        # Read ZIP into memory with size limit enforcement
        zip_bytes = zip_file.read()
        if len(zip_bytes) > MAX_ZIP_SIZE_BYTES:
            raise ZipSizeLimitExceededError(
                f"ZIP file too large: {len(zip_bytes):,} bytes "
                f"(max {MAX_ZIP_SIZE_BYTES:,} bytes / {MAX_ZIP_SIZE_BYTES // (1024*1024)} MB)"
            )

        # Open ZIP
        with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
            # Validate all paths first (fail-fast on zip-slip)
            for name in zf.namelist():
                if not is_safe_zip_path(name):
                    raise ZipSlipError(f"Unsafe path detected in ZIP: {name}")

            # Read manifest
            try:
                manifest_data = zf.read("manifest.json")
                manifest = json.loads(manifest_data.decode("utf-8"))
            except KeyError:
                raise InvalidManifestError("manifest.json not found in ZIP")
            except json.JSONDecodeError as e:
                raise InvalidManifestError(f"Invalid manifest.json: {e}")

            # Find JSONL files
            record_files = [n for n in zf.namelist() if n.startswith("records/") and n.endswith(".jsonl")]

            # Parse all records first to check count
            all_records: list[tuple[int, HarvesterRecord, str]] = []  # (index, record, connector)
            global_index = 0

            for jsonl_path in record_files:
                connector = PurePosixPath(jsonl_path).stem
                try:
                    jsonl_data = zf.read(jsonl_path).decode("utf-8")
                    for line in jsonl_data.strip().split("\n"):
                        if not line.strip():
                            continue
                        try:
                            record_dict = json.loads(line)
                            record = HarvesterRecord.from_dict(record_dict)
                            all_records.append((global_index, record, connector))
                        except json.JSONDecodeError as e:
                            result.add_failure(global_index, None, f"Invalid JSON: {e}")
                        global_index += 1
                except Exception as e:
                    logger.warning(f"Failed to read {jsonl_path}: {e}")

            # Check record limit
            if len(all_records) > MAX_RECORDS_PER_IMPORT:
                raise RecordLimitExceededError(
                    f"Too many records: {len(all_records)} (max {MAX_RECORDS_PER_IMPORT})"
                )

            # Process each record
            for record_index, record, connector in all_records:
                try:
                    await self._process_record(
                        zf=zf,
                        record=record,
                        record_index=record_index,
                        import_batch_id=import_batch_id,
                        user_id=user_id,
                        result=result,
                    )
                except Exception as e:
                    logger.warning(f"Failed to process record {record_index}: {e}")
                    result.add_failure(record_index, record.source_url, str(e))

        # Calculate processing time
        end_time = datetime.now(timezone.utc)
        result.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return result

    async def _process_record(
        self,
        zf: zipfile.ZipFile,
        record: HarvesterRecord,
        record_index: int,
        import_batch_id: str,
        user_id: str | None,
        result: ImportResult,
    ) -> None:
        """Process a single harvester record.

        Args:
            zf: Open ZIP file
            record: Parsed harvester record
            record_index: Index for error reporting
            import_batch_id: UUID of this import batch
            user_id: User performing the import
            result: Result object to update counts
        """
        # Validate record
        validation_error = record.validate()
        if validation_error:
            result.add_failure(record_index, record.source_url, validation_error)
            return

        # Compute keys
        instrument_key = compute_instrument_key(
            record.jurisdiction, record.source_name, record.source_url
        )
        version_key = record.raw_sha256

        # Upsert instrument
        instrument = await self._upsert_instrument(
            record=record,
            instrument_key=instrument_key,
            import_batch_id=import_batch_id,
            user_id=user_id,
            result=result,
        )

        # Check if version already exists
        existing_version = await self._get_existing_version(
            instrument_id=instrument.id,
            version_key=version_key,
        )
        if existing_version:
            result.versions_existing += 1
            return

        # Read raw artifact from ZIP
        try:
            raw_data = zf.read(record.raw_artifact_path)
        except KeyError:
            result.add_failure(
                record_index, record.source_url,
                f"Raw artifact not found: {record.raw_artifact_path}"
            )
            return

        # Enforce individual file size limit (50 MB)
        if len(raw_data) > MAX_FILE_SIZE_BYTES:
            result.add_failure(
                record_index, record.source_url,
                f"File too large: {len(raw_data):,} bytes "
                f"(max {MAX_FILE_SIZE_BYTES:,} bytes / {MAX_FILE_SIZE_BYTES // (1024*1024)} MB)"
            )
            return

        # Verify SHA256
        computed_sha = compute_sha256(raw_data)
        if computed_sha != record.raw_sha256:
            result.add_failure(
                record_index, record.source_url,
                f"SHA256 mismatch: expected {record.raw_sha256}, got {computed_sha}"
            )
            return

        # Parse extension from artifact path and infer content type
        ext = parse_file_ext_from_artifact_path(record.raw_artifact_path)
        content_type = infer_content_type(ext)

        # Determine language: "ar" if title_ar exists and non-empty, else "mixed"
        language = "ar" if record.title_ar and record.title_ar.strip() else "mixed"

        # Create version
        await self._create_version(
            instrument=instrument,
            record=record,
            version_key=version_key,
            raw_data=raw_data,
            content_type=content_type,
            ext=ext,
            language=language,
            import_batch_id=import_batch_id,
            user_id=user_id,
        )
        result.versions_created += 1

    async def _upsert_instrument(
        self,
        record: HarvesterRecord,
        instrument_key: str,
        import_batch_id: str,
        user_id: str | None,
        result: ImportResult,
    ) -> LegalInstrument:
        """Upsert a legal instrument by (jurisdiction, instrument_key).

        Args:
            record: Harvester record
            instrument_key: Computed dedupe key
            import_batch_id: UUID of import batch
            user_id: User performing the import
            result: Result object for counting

        Returns:
            The existing or newly created LegalInstrument
        """
        # Check if instrument exists
        stmt = select(LegalInstrument).where(
            and_(
                LegalInstrument.jurisdiction == record.jurisdiction,
                LegalInstrument.instrument_key == instrument_key,
            )
        )
        existing = await self.db.execute(stmt)
        instrument = existing.scalar_one_or_none()

        if instrument:
            # Update timestamp to track last import touch
            instrument.updated_at = datetime.now(timezone.utc)
            instrument.import_batch_id = import_batch_id
            result.instruments_existing += 1
            return instrument

        # Create new instrument
        # Use Arabic title for both title and title_ar (English translation deferred)
        title = record.title_ar
        published_at = parse_date_guess(record.published_at_guess)
        instrument_type = normalize_instrument_type(record.instrument_type_guess)

        instrument = LegalInstrument(
            jurisdiction=record.jurisdiction,
            instrument_type=instrument_type,
            title=title,
            title_ar=record.title_ar,
            official_source_url=record.source_url,
            published_at=published_at,
            status="active",
            created_by_user_id=user_id,
            instrument_key=instrument_key,
            import_batch_id=import_batch_id,
        )
        self.db.add(instrument)
        await self.db.flush()
        result.instruments_created += 1
        return instrument

    async def _get_existing_version(
        self,
        instrument_id: str,
        version_key: str,
    ) -> LegalInstrumentVersion | None:
        """Check if a version already exists for an instrument.

        Args:
            instrument_id: The instrument ID
            version_key: The version dedupe key (sha256)

        Returns:
            The existing version or None
        """
        stmt = select(LegalInstrumentVersion).where(
            and_(
                LegalInstrumentVersion.legal_instrument_id == instrument_id,
                LegalInstrumentVersion.version_key == version_key,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_version(
        self,
        instrument: LegalInstrument,
        record: HarvesterRecord,
        version_key: str,
        raw_data: bytes,
        content_type: str,
        ext: str,
        language: str,
        import_batch_id: str,
        user_id: str | None,
    ) -> LegalInstrumentVersion:
        """Create a new version for an instrument.

        Args:
            instrument: The parent instrument
            record: Harvester record
            version_key: The version dedupe key (sha256)
            raw_data: Raw file bytes
            content_type: MIME type
            ext: File extension (without dot)
            language: Language code ("ar" or "mixed")
            import_batch_id: UUID of import batch
            user_id: User performing the import

        Returns:
            The created LegalInstrumentVersion
        """
        # Construct file_name as {raw_sha256}.{ext}
        # Do NOT use raw_artifact_path directly
        file_name = f"{record.raw_sha256}.{ext}" if ext else record.raw_sha256

        # Create version record
        version = LegalInstrumentVersion(
            legal_instrument_id=instrument.id,
            version_label="imported",
            file_name=file_name,
            content_type=content_type,
            size_bytes=len(raw_data),
            storage_provider="s3",
            storage_bucket=self.storage_client.bucket_name,
            storage_key="",  # Will be set after we have the ID
            sha256=record.raw_sha256,
            language=language,
            is_indexed=False,  # Indexing deferred
            uploaded_by_user_id=user_id,
            version_key=version_key,
            import_batch_id=import_batch_id,
            imported_at=datetime.now(timezone.utc),
        )
        self.db.add(version)
        await self.db.flush()

        # Generate storage key
        storage_key = generate_legal_storage_key(
            instrument_id=instrument.id,
            version_id=version.id,
            filename=file_name,
        )
        version.storage_key = storage_key

        # Upload to S3
        try:
            self.storage_client.put_object(
                key=storage_key,
                data=raw_data,
                content_type=content_type,
            )
        except S3StorageError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

        return version


# =============================================================================
# Batch Reindex Service
# =============================================================================


@dataclass
class ReindexFailure:
    """Represents a single reindex failure."""

    version_id: str
    instrument_id: str
    error: str


@dataclass
class BatchReindexResult:
    """Result of a batch reindex operation."""

    import_batch_id: str
    attempted: int = 0
    indexed: int = 0
    failed: int = 0
    failures: list[ReindexFailure] = field(default_factory=list)

    def add_failure(self, version_id: str, instrument_id: str, error: str) -> None:
        """Add a failure to the result (caps at 20 for response)."""
        self.failed += 1
        if len(self.failures) < 20:
            self.failures.append(ReindexFailure(
                version_id=version_id,
                instrument_id=instrument_id,
                error=error,
            ))


@dataclass
class BatchStatusResult:
    """Status of an import batch for indexing progress."""

    import_batch_id: str
    total_versions: int = 0
    indexed_versions: int = 0
    pending_versions: int = 0
    last_imported_at: datetime | None = None


async def get_batch_status(
    db: AsyncSession,
    import_batch_id: str,
) -> BatchStatusResult | None:
    """Get the indexing status of an import batch.

    Args:
        db: Async database session
        import_batch_id: UUID of the import batch

    Returns:
        BatchStatusResult or None if batch not found
    """
    # Query for aggregate counts
    stmt = select(
        func.count(LegalInstrumentVersion.id).label("total"),
        func.sum(
            case((LegalInstrumentVersion.is_indexed == True, 1), else_=0)
        ).label("indexed"),
        func.max(LegalInstrumentVersion.imported_at).label("last_imported_at"),
    ).where(
        LegalInstrumentVersion.import_batch_id == import_batch_id
    )

    result = await db.execute(stmt)
    row = result.one_or_none()

    if row is None or row.total == 0:
        return None

    total = row.total or 0
    indexed = int(row.indexed or 0)
    pending = total - indexed

    return BatchStatusResult(
        import_batch_id=import_batch_id,
        total_versions=total,
        indexed_versions=indexed,
        pending_versions=pending,
        last_imported_at=row.last_imported_at,
    )


async def batch_reindex_versions(
    db: AsyncSession,
    storage_client: S3StorageClient,
    import_batch_id: str,
    max_versions: int = 25,
    index_all: bool = False,
) -> BatchReindexResult:
    """Reindex up to max_versions unindexed versions from an import batch.

    Args:
        db: Async database session
        storage_client: S3 storage client
        import_batch_id: UUID of the import batch
        max_versions: Maximum number of versions to process (capped at 5000 unless index_all=True)
        index_all: If True, index ALL pending versions (no limit)

    Returns:
        BatchReindexResult with counts and failures
    """
    from src.services.global_legal_service import GlobalLegalService

    # Cap max_versions at 5000 unless index_all is set
    if index_all:
        # No limit - fetch all unindexed versions
        effective_limit = None
    else:
        effective_limit = min(max_versions, 5000)

    result = BatchReindexResult(import_batch_id=import_batch_id)

    # Find unindexed versions for this batch
    stmt = (
        select(LegalInstrumentVersion)
        .where(
            and_(
                LegalInstrumentVersion.import_batch_id == import_batch_id,
                LegalInstrumentVersion.is_indexed == False,
            )
        )
        .order_by(LegalInstrumentVersion.imported_at.asc())
    )
    
    # Apply limit only if not indexing all
    if effective_limit is not None:
        stmt = stmt.limit(effective_limit)

    versions_result = await db.execute(stmt)
    versions = versions_result.scalars().all()

    if not versions:
        return result

    # Create the global legal service for reindexing
    service = GlobalLegalService(db, storage_client)

    for version in versions:
        result.attempted += 1
        try:
            chunks_indexed, _ = await service.reindex_version(
                version_id=version.id,
                replace_existing=True,
            )
            if chunks_indexed > 0:
                result.indexed += 1
            else:
                # Zero chunks is treated as a failure
                result.add_failure(
                    version_id=version.id,
                    instrument_id=version.legal_instrument_id,
                    error="No chunks created during indexing",
                )
        except Exception as e:
            logger.warning(f"Failed to reindex version {version.id}: {e}")
            result.add_failure(
                version_id=version.id,
                instrument_id=version.legal_instrument_id,
                error=str(e)[:200],
            )

    return result


# =============================================================================
# Purge All Legal Corpus
# =============================================================================


@dataclass
class PurgeResult:
    """Result of purging all legal corpus data."""

    instruments_deleted: int = 0
    versions_deleted: int = 0
    chunks_deleted: int = 0
    embeddings_deleted: int = 0
    texts_deleted: int = 0


async def purge_all_legal_corpus(db: AsyncSession) -> PurgeResult:
    """Delete all legal corpus data from the database.

    Deletes in the correct order to respect foreign key constraints:
    1. legal_chunk_embeddings
    2. legal_chunks
    3. legal_texts
    4. legal_instrument_versions
    5. legal_instruments

    Note: S3 files are NOT deleted by this function. They must be cleaned
    separately if needed.

    Args:
        db: Async database session

    Returns:
        PurgeResult with counts of deleted items
    """
    result = PurgeResult()

    # Count items before deletion
    embeddings_count = await db.execute(select(func.count(LegalChunkEmbedding.id)))
    result.embeddings_deleted = embeddings_count.scalar() or 0

    chunks_count = await db.execute(select(func.count(LegalChunk.id)))
    result.chunks_deleted = chunks_count.scalar() or 0

    texts_count = await db.execute(select(func.count(LegalText.id)))
    result.texts_deleted = texts_count.scalar() or 0

    versions_count = await db.execute(select(func.count(LegalInstrumentVersion.id)))
    result.versions_deleted = versions_count.scalar() or 0

    instruments_count = await db.execute(select(func.count(LegalInstrument.id)))
    result.instruments_deleted = instruments_count.scalar() or 0

    # Delete in order (respecting foreign key constraints)
    # Even though CASCADE is set, we delete explicitly for accurate counts
    await db.execute(delete(LegalChunkEmbedding))
    await db.execute(delete(LegalChunk))
    await db.execute(delete(LegalText))
    await db.execute(delete(LegalInstrumentVersion))
    await db.execute(delete(LegalInstrument))

    logger.info(
        f"Purged legal corpus: {result.instruments_deleted} instruments, "
        f"{result.versions_deleted} versions, {result.chunks_deleted} chunks, "
        f"{result.embeddings_deleted} embeddings, {result.texts_deleted} texts"
    )

    return result
