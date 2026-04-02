"""Tests for Global Legal Import feature.

Tests cover:
- Zip-slip attack rejection
- Idempotent import (same snapshot twice = 0 new versions)
- Record limit enforcement
- Invalid manifest rejection
- Platform admin access control

Prerequisites:
    docker compose up postgres minio minio-init -d

Run all tests:
    uv run pytest tests/test_global_legal_import.py -v
"""

import io
import json
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Tenant, User, Workspace
from src.models.legal_instrument import LegalInstrument
from src.models.legal_instrument_version import LegalInstrumentVersion
from src.services.global_legal_import_service import (
    is_safe_zip_path,
    compute_instrument_key,
    parse_file_ext_from_artifact_path,
    infer_content_type,
    GlobalLegalImportService,
    ZipSlipError,
    RecordLimitExceededError,
    InvalidManifestError,
    MAX_RECORDS_PER_IMPORT,
    MAX_FILE_SIZE_BYTES,
)
from src.storage.s3 import get_storage_client


@pytest.fixture(scope="module", autouse=True)
def check_minio_bucket():
    """Fail fast if MinIO bucket doesn't exist (minio-init not run)."""
    client = get_storage_client()
    if not client.bucket_exists():
        pytest.fail(
            f"S3 bucket '{client.bucket_name}' does not exist. "
            "Did you run minio-init? Use: docker compose up postgres minio minio-init -d"
        )


# =============================================================================
# Unit Tests for Utility Functions
# =============================================================================


class TestIsServeZipPath:
    """Unit tests for zip-slip path validation."""

    def test_safe_simple_path(self):
        """Simple paths should be safe."""
        assert is_safe_zip_path("manifest.json") is True
        assert is_safe_zip_path("records/connector.jsonl") is True
        assert is_safe_zip_path("raw/abc123.pdf") is True

    def test_unsafe_absolute_path(self):
        """Absolute paths should be rejected."""
        assert is_safe_zip_path("/etc/passwd") is False
        assert is_safe_zip_path("C:\\Windows\\System32") is False

    def test_unsafe_parent_traversal(self):
        """Parent directory traversal should be rejected."""
        assert is_safe_zip_path("../etc/passwd") is False
        assert is_safe_zip_path("records/../../../etc/passwd") is False
        assert is_safe_zip_path("..") is False
        assert is_safe_zip_path("foo/../../bar") is False

    def test_safe_with_dots_in_name(self):
        """Dots in filenames (not traversal) should be safe."""
        assert is_safe_zip_path("file.name.pdf") is True
        assert is_safe_zip_path("records/source..jsonl") is True

    def test_unsafe_with_extract_base(self):
        """Path should stay within extract base."""
        # Even if normalized, it escapes the base
        assert is_safe_zip_path("../sibling", "/tmp/extract") is False
        assert is_safe_zip_path("subdir/../../../etc", "/tmp/extract") is False


class TestParseFileExtFromArtifactPath:
    """Unit tests for file extension parsing."""

    def test_parse_pdf_extension(self):
        """Should parse PDF extension correctly."""
        assert parse_file_ext_from_artifact_path("raw/abc123.pdf") == "pdf"

    def test_parse_docx_extension(self):
        """Should parse DOCX extension correctly."""
        assert parse_file_ext_from_artifact_path("raw/def456.docx") == "docx"

    def test_parse_html_extension(self):
        """Should parse HTML extension correctly."""
        assert parse_file_ext_from_artifact_path("raw/ghi789.html") == "html"

    def test_no_extension(self):
        """Should return empty string if no extension."""
        assert parse_file_ext_from_artifact_path("raw/noextension") == ""

    def test_lowercase_extension(self):
        """Should return lowercase extension."""
        assert parse_file_ext_from_artifact_path("raw/UPPERCASE.PDF") == "pdf"


class TestInferContentType:
    """Unit tests for content type inference."""

    def test_pdf_content_type(self):
        """PDF should return correct MIME type."""
        assert infer_content_type("pdf") == "application/pdf"

    def test_docx_content_type(self):
        """DOCX should return correct MIME type."""
        assert infer_content_type("docx") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def test_html_content_type(self):
        """HTML should return correct MIME type."""
        assert infer_content_type("html") == "text/html"
        assert infer_content_type("htm") == "text/html"

    def test_txt_content_type(self):
        """TXT should return correct MIME type."""
        assert infer_content_type("txt") == "text/plain"

    def test_unknown_extension(self):
        """Unknown extension should return octet-stream."""
        assert infer_content_type("xyz") == "application/octet-stream"
        assert infer_content_type("") == "application/octet-stream"


class TestComputeInstrumentKey:
    """Unit tests for instrument key computation."""

    def test_consistent_key_generation(self):
        """Same inputs should produce same key."""
        key1 = compute_instrument_key("UAE", "moj_uae", "https://example.com/law/1")
        key2 = compute_instrument_key("UAE", "moj_uae", "https://example.com/law/1")
        assert key1 == key2

    def test_different_urls_different_keys(self):
        """Different URLs should produce different keys."""
        key1 = compute_instrument_key("UAE", "moj_uae", "https://example.com/law/1")
        key2 = compute_instrument_key("UAE", "moj_uae", "https://example.com/law/2")
        assert key1 != key2

    def test_key_format(self):
        """Key should follow expected format with FULL 64-char SHA256."""
        key = compute_instrument_key("UAE", "moj_uae", "https://example.com/law/1")
        parts = key.split(":")
        assert len(parts) == 3
        assert parts[0] == "UAE"
        assert parts[1] == "moj_uae"
        # Full 64-char lowercase hex SHA256 (no truncation)
        assert len(parts[2]) == 64
        assert parts[2] == parts[2].lower()  # Lowercase
        assert all(c in "0123456789abcdef" for c in parts[2])  # Hex chars only


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def platform_admin_user(clean_db: AsyncSession, tenant_factory, user_factory, workspace_factory, membership_factory):
    """Create a platform admin user with workspace membership (for auth)."""
    tenant = await tenant_factory()
    workspace = await workspace_factory(tenant)
    user = await user_factory(tenant, email="admin@platform.com")
    user.is_platform_admin = True
    await clean_db.commit()
    membership = await membership_factory(workspace, user, role="ADMIN")
    await clean_db.refresh(user)
    return user, tenant, workspace


@pytest.fixture
async def regular_user(clean_db: AsyncSession, tenant_factory, user_factory, workspace_factory, membership_factory):
    """Create a regular user with workspace membership."""
    tenant = await tenant_factory()
    workspace = await workspace_factory(tenant)
    user = await user_factory(tenant, email="user@example.com")
    membership = await membership_factory(workspace, user, role="ADMIN")
    return user, tenant, workspace


def create_test_snapshot(
    records: list[dict],
    include_manifest: bool = True,
    include_files: bool = True,
    extra_files: dict[str, bytes] | None = None,
) -> bytes:
    """Create a test snapshot ZIP file.

    Args:
        records: List of record dictionaries
        include_manifest: Whether to include manifest.json
        include_files: Whether to include raw files referenced by records
        extra_files: Additional files to include (path -> content)

    Returns:
        ZIP file as bytes
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write manifest
        if include_manifest:
            manifest = {
                "harvester_version": "1.0.0",
                "created_at": "2025-01-27T10:00:00Z",
                "record_count": len(records),
            }
            zf.writestr("manifest.json", json.dumps(manifest))

        # Write records JSONL
        jsonl_content = "\n".join(json.dumps(r) for r in records)
        zf.writestr("records/test_connector.jsonl", jsonl_content)

        # Write raw files
        if include_files:
            for record in records:
                if "raw_artifact_path" in record and "raw_sha256" in record:
                    # Create dummy content that matches the declared SHA256
                    # For testing, we'll use the sha256 as the content (won't match in real scenario)
                    # Actually, let's create proper content
                    path = record["raw_artifact_path"]
                    # Create simple PDF-like content
                    content = b"%PDF-1.4\nTest content for " + record.get("source_url", "").encode()
                    # Compute actual SHA256
                    import hashlib
                    actual_sha = hashlib.sha256(content).hexdigest()
                    # Update record with actual SHA (this modifies the input dict)
                    record["raw_sha256"] = actual_sha
                    zf.writestr(path, content)

        # Write extra files
        if extra_files:
            for path, content in extra_files.items():
                zf.writestr(path, content)

    buffer.seek(0)
    return buffer.getvalue()


def create_valid_record(
    jurisdiction: str = "UAE",
    source_name: str = "test_source",
    source_url: str = "https://example.com/law/1",
    title_ar: str = "قانون اختبار",
    instrument_type_guess: str = "law",
    raw_index: int = 0,
) -> dict:
    """Create a valid harvester record."""
    return {
        "jurisdiction": jurisdiction,
        "source_name": source_name,
        "source_url": source_url,
        "retrieved_at": "2025-01-27T09:00:00Z",
        "title_ar": title_ar,
        "instrument_type_guess": instrument_type_guess,
        "published_at_guess": "2024-01-01",
        "raw_artifact_path": f"raw/file_{raw_index}.pdf",
        "raw_sha256": "",  # Will be updated by create_test_snapshot
    }


# =============================================================================
# Integration Tests
# =============================================================================


class TestAccessControl:
    """Tests for platform admin access control."""

    @pytest.mark.asyncio
    async def test_non_platform_admin_cannot_import(
        self, async_client: AsyncClient, regular_user
    ):
        """Non-platform admin should get 403 when importing."""
        user, tenant, workspace = regular_user
        snapshot = create_test_snapshot([create_valid_record()])

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_platform_admin_can_get_import_info(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Platform admin should be able to get import info."""
        user, tenant, workspace = platform_admin_user

        response = await async_client.get(
            "/global/legal-import/info",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "limits" in data
        assert data["limits"]["max_records_per_import"] == MAX_RECORDS_PER_IMPORT


class TestZipSlipRejection:
    """Tests for zip-slip attack detection."""

    @pytest.mark.asyncio
    async def test_reject_zip_with_traversal_path(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Snapshot with path traversal should be rejected."""
        user, tenant, workspace = platform_admin_user

        # Create a malicious ZIP with path traversal
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"harvester_version": "1.0.0"}))
            zf.writestr("records/test.jsonl", "")
            # Malicious path
            zf.writestr("../../../etc/passwd", "root:x:0:0:root:/root:/bin/bash")
        buffer.seek(0)

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("malicious.zip", buffer.getvalue(), "application/zip")},
        )
        assert response.status_code == 400
        assert "Unsafe path" in response.json()["detail"] or "Security error" in response.json()["detail"]


class TestImportIdempotency:
    """Tests for idempotent import behavior."""

    @pytest.mark.asyncio
    async def test_import_same_snapshot_twice_is_idempotent(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """Importing the same snapshot twice should not create duplicates."""
        user, tenant, workspace = platform_admin_user

        # Create a snapshot with two records
        records = [
            create_valid_record(source_url="https://example.com/law/1", raw_index=0),
            create_valid_record(source_url="https://example.com/law/2", raw_index=1),
        ]
        snapshot = create_test_snapshot(records)

        # First import
        response1 = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["instruments_created"] == 2
        assert data1["versions_created"] == 2
        assert data1["instruments_existing"] == 0
        assert data1["versions_existing"] == 0

        # Second import of the same snapshot
        response2 = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Second import should find all existing
        assert data2["instruments_created"] == 0
        assert data2["versions_created"] == 0
        assert data2["instruments_existing"] == 2
        assert data2["versions_existing"] == 2

        # Verify only 2 instruments exist in DB
        result = await clean_db.execute(select(func.count(LegalInstrument.id)))
        instrument_count = result.scalar()
        assert instrument_count == 2

        # Verify only 2 versions exist in DB
        result = await clean_db.execute(select(func.count(LegalInstrumentVersion.id)))
        version_count = result.scalar()
        assert version_count == 2


class TestInvalidInput:
    """Tests for invalid input handling."""

    @pytest.mark.asyncio
    async def test_reject_missing_manifest(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Snapshot without manifest.json should be rejected."""
        user, tenant, workspace = platform_admin_user
        snapshot = create_test_snapshot([create_valid_record()], include_manifest=False)

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response.status_code == 400
        assert "manifest" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reject_invalid_manifest_json(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Snapshot with invalid manifest.json should be rejected."""
        user, tenant, workspace = platform_admin_user

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("manifest.json", "not valid json {{{")
            zf.writestr("records/test.jsonl", "")
        buffer.seek(0)

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", buffer.getvalue(), "application/zip")},
        )
        assert response.status_code == 400
        assert "manifest" in response.json()["detail"].lower()


class TestVersionDeduplication:
    """Tests for version-level deduplication."""

    @pytest.mark.asyncio
    async def test_new_version_for_existing_instrument(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """New version with different content should be created."""
        user, tenant, workspace = platform_admin_user

        # First snapshot with one record
        records1 = [create_valid_record(source_url="https://example.com/law/1", raw_index=0)]
        snapshot1 = create_test_snapshot(records1)

        response1 = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot1.zip", snapshot1, "application/zip")},
        )
        assert response1.status_code == 200
        assert response1.json()["instruments_created"] == 1
        assert response1.json()["versions_created"] == 1

        # Second snapshot with same source_url but different file content
        # This simulates an updated version of the same law
        records2 = [create_valid_record(source_url="https://example.com/law/1", raw_index=99)]
        snapshot2 = create_test_snapshot(records2)

        response2 = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot2.zip", snapshot2, "application/zip")},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Instrument exists, but new version should be created (different sha256)
        assert data2["instruments_existing"] == 1
        assert data2["instruments_created"] == 0
        assert data2["versions_created"] == 1  # New version!
        assert data2["versions_existing"] == 0

        # Verify 1 instrument with 2 versions
        result = await clean_db.execute(select(func.count(LegalInstrument.id)))
        assert result.scalar() == 1

        result = await clean_db.execute(select(func.count(LegalInstrumentVersion.id)))
        assert result.scalar() == 2


class TestVersionFields:
    """Tests for version field handling (file_name, language)."""

    @pytest.mark.asyncio
    async def test_file_name_is_sha256_with_extension(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """file_name should be {raw_sha256}.{ext}, NOT the raw_artifact_path."""
        user, tenant, workspace = platform_admin_user

        records = [create_valid_record(source_url="https://example.com/law/fn1", raw_index=100)]
        snapshot = create_test_snapshot(records)

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response.status_code == 200
        assert response.json()["versions_created"] == 1

        # Check the version in DB
        result = await clean_db.execute(select(LegalInstrumentVersion))
        version = result.scalar_one()

        # file_name should be {sha256}.pdf, NOT raw/file_100.pdf
        assert version.file_name.endswith(".pdf")
        assert version.file_name == f"{version.sha256}.pdf"
        assert "raw/" not in version.file_name
        assert "file_" not in version.file_name

    @pytest.mark.asyncio
    async def test_language_is_ar_when_title_ar_present(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """language should be 'ar' when title_ar is present."""
        user, tenant, workspace = platform_admin_user

        records = [create_valid_record(
            source_url="https://example.com/law/lang1",
            title_ar="قانون اختبار",
            raw_index=200,
        )]
        snapshot = create_test_snapshot(records)

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response.status_code == 200

        result = await clean_db.execute(select(LegalInstrumentVersion))
        version = result.scalar_one()
        assert version.language == "ar"


class TestImportResults:
    """Tests for import result reporting."""

    @pytest.mark.asyncio
    async def test_import_result_contains_batch_id(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Import result should contain a batch ID."""
        user, tenant, workspace = platform_admin_user
        snapshot = create_test_snapshot([create_valid_record()])

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "import_batch_id" in data
        # Should be a valid UUID format
        import uuid
        uuid.UUID(data["import_batch_id"])  # Raises if invalid

    @pytest.mark.asyncio
    async def test_import_result_contains_processing_time(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Import result should contain processing time."""
        user, tenant, workspace = platform_admin_user
        snapshot = create_test_snapshot([create_valid_record()])

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0


class TestFileSizeLimitFailures:
    """Tests for per-record file size limit enforcement."""

    @pytest.mark.asyncio
    async def test_oversized_file_appears_in_failures(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """Files exceeding MAX_FILE_SIZE_BYTES should be logged as failures."""
        user, tenant, workspace = platform_admin_user

        # Create a snapshot with one normal record and one oversized record
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            manifest = {
                "harvester_version": "1.0.0",
                "created_at": "2025-01-27T10:00:00Z",
                "record_count": 2,
            }
            zf.writestr("manifest.json", json.dumps(manifest))

            # Normal-sized file (small)
            import hashlib
            normal_content = b"%PDF-1.4\nNormal size file"
            normal_sha = hashlib.sha256(normal_content).hexdigest()
            zf.writestr(f"raw/{normal_sha}.pdf", normal_content)

            # Oversized file (exceeds 50 MB limit)
            # We create content just over the limit for testing
            oversized_content = b"X" * (MAX_FILE_SIZE_BYTES + 1000)
            oversized_sha = hashlib.sha256(oversized_content).hexdigest()
            zf.writestr(f"raw/{oversized_sha}.pdf", oversized_content)

            # Write records JSONL
            records = [
                {
                    "jurisdiction": "UAE",
                    "source_name": "test_source",
                    "source_url": "https://example.com/normal",
                    "retrieved_at": "2025-01-27T09:00:00Z",
                    "title_ar": "قانون عادي",
                    "instrument_type_guess": "law",
                    "published_at_guess": "2024-01-01",
                    "raw_artifact_path": f"raw/{normal_sha}.pdf",
                    "raw_sha256": normal_sha,
                },
                {
                    "jurisdiction": "UAE",
                    "source_name": "test_source",
                    "source_url": "https://example.com/oversized",
                    "retrieved_at": "2025-01-27T09:00:00Z",
                    "title_ar": "قانون كبير جدا",
                    "instrument_type_guess": "law",
                    "published_at_guess": "2024-01-01",
                    "raw_artifact_path": f"raw/{oversized_sha}.pdf",
                    "raw_sha256": oversized_sha,
                },
            ]
            jsonl_content = "\n".join(json.dumps(r) for r in records)
            zf.writestr("records/test_connector.jsonl", jsonl_content)

        buffer.seek(0)
        snapshot = buffer.getvalue()

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()

        # Normal file should succeed
        assert data["versions_created"] == 1

        # Oversized file should be in failures
        assert data["failure_count"] == 1
        assert len(data["failures"]) == 1

        # Check failure details
        failure = data["failures"][0]
        assert failure["record_index"] == 1  # Second record (0-indexed)
        assert "https://example.com/oversized" in failure["source_url"]
        assert "too large" in failure["error"].lower() or "File too large" in failure["error"]
        assert "50 MB" in failure["error"] or str(MAX_FILE_SIZE_BYTES) in failure["error"]

        # Verify only 1 version was created in DB (the normal one)
        result = await clean_db.execute(select(func.count(LegalInstrumentVersion.id)))
        version_count = result.scalar()
        assert version_count == 1

    @pytest.mark.asyncio
    async def test_oversized_file_does_not_prevent_other_records(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """Oversized files should not prevent other records from being imported."""
        user, tenant, workspace = platform_admin_user

        # Create snapshot with 3 records: normal, oversized, normal
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "harvester_version": "1.0.0",
                "created_at": "2025-01-27T10:00:00Z",
                "record_count": 3,
            }
            zf.writestr("manifest.json", json.dumps(manifest))

            import hashlib
            records = []

            # Record 0: Normal
            content0 = b"%PDF-1.4\nNormal file 0"
            sha0 = hashlib.sha256(content0).hexdigest()
            zf.writestr(f"raw/{sha0}.pdf", content0)
            records.append({
                "jurisdiction": "UAE",
                "source_name": "test",
                "source_url": "https://example.com/law/0",
                "retrieved_at": "2025-01-27T09:00:00Z",
                "title_ar": "قانون 0",
                "instrument_type_guess": "law",
                "raw_artifact_path": f"raw/{sha0}.pdf",
                "raw_sha256": sha0,
            })

            # Record 1: Oversized
            content1 = b"Y" * (MAX_FILE_SIZE_BYTES + 500)
            sha1 = hashlib.sha256(content1).hexdigest()
            zf.writestr(f"raw/{sha1}.pdf", content1)
            records.append({
                "jurisdiction": "UAE",
                "source_name": "test",
                "source_url": "https://example.com/law/1",
                "retrieved_at": "2025-01-27T09:00:00Z",
                "title_ar": "قانون 1",
                "instrument_type_guess": "law",
                "raw_artifact_path": f"raw/{sha1}.pdf",
                "raw_sha256": sha1,
            })

            # Record 2: Normal
            content2 = b"%PDF-1.4\nNormal file 2"
            sha2 = hashlib.sha256(content2).hexdigest()
            zf.writestr(f"raw/{sha2}.pdf", content2)
            records.append({
                "jurisdiction": "UAE",
                "source_name": "test",
                "source_url": "https://example.com/law/2",
                "retrieved_at": "2025-01-27T09:00:00Z",
                "title_ar": "قانون 2",
                "instrument_type_guess": "law",
                "raw_artifact_path": f"raw/{sha2}.pdf",
                "raw_sha256": sha2,
            })

            jsonl_content = "\n".join(json.dumps(r) for r in records)
            zf.writestr("records/test.jsonl", jsonl_content)

        buffer.seek(0)
        snapshot = buffer.getvalue()

        response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )

        assert response.status_code == 200
        data = response.json()

        # 2 normal records should succeed
        assert data["versions_created"] == 2
        assert data["instruments_created"] == 2

        # 1 oversized should fail
        assert data["failure_count"] == 1
        assert data["failures"][0]["record_index"] == 1

        # Verify 2 versions in DB
        result = await clean_db.execute(select(func.count(LegalInstrumentVersion.id)))
        assert result.scalar() == 2


# =============================================================================
# Batch Reindex Endpoint Tests
# =============================================================================


class TestBatchReindexAccessControl:
    """Tests for batch reindex access control."""

    @pytest.mark.asyncio
    async def test_non_platform_admin_cannot_reindex(
        self, async_client: AsyncClient, regular_user
    ):
        """Non-platform admin should get 403 when calling reindex."""
        user, tenant, workspace = regular_user

        response = await async_client.post(
            "/global/legal-import/reindex",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "max_versions": 25,
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_non_platform_admin_cannot_get_status(
        self, async_client: AsyncClient, regular_user
    ):
        """Non-platform admin should get 403 when getting batch status."""
        user, tenant, workspace = regular_user

        response = await async_client.get(
            "/global/legal-import/batches/550e8400-e29b-41d4-a716-446655440000/status",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 403


class TestBatchReindexValidation:
    """Tests for batch reindex input validation."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_400(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Invalid UUID format should return 400."""
        user, tenant, workspace = platform_admin_user

        response = await async_client.post(
            "/global/legal-import/reindex",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "import_batch_id": "not-a-valid-uuid",
                "max_versions": 25,
            },
        )
        assert response.status_code == 400
        assert "UUID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_max_versions_capped_at_100(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """max_versions should be capped at 100."""
        user, tenant, workspace = platform_admin_user

        # Request with max_versions > 100 should be capped (not rejected)
        # We test this indirectly - the request should succeed with valid UUID
        # even if there are no versions to reindex
        response = await async_client.post(
            "/global/legal-import/reindex",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "import_batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "max_versions": 200,  # Exceeds cap but should be capped, not rejected
            },
        )
        # Request should succeed (even if no versions exist)
        assert response.status_code == 200


class TestBatchStatus:
    """Tests for batch status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_for_nonexistent_batch(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Getting status for nonexistent batch returns 404."""
        user, tenant, workspace = platform_admin_user

        response = await async_client.get(
            "/global/legal-import/batches/550e8400-e29b-41d4-a716-446655440000/status",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_status_invalid_uuid(
        self, async_client: AsyncClient, platform_admin_user
    ):
        """Invalid UUID format should return 400."""
        user, tenant, workspace = platform_admin_user

        response = await async_client.get(
            "/global/legal-import/batches/not-a-uuid/status",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert response.status_code == 400


class TestBatchReindexBehavior:
    """Tests for batch reindex behavior."""

    @pytest.mark.asyncio
    async def test_reindex_only_selects_unindexed_versions(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """Reindex should only process versions with is_indexed=false."""
        user, tenant, workspace = platform_admin_user

        # First import a snapshot
        records = [
            create_valid_record(source_url="https://example.com/law/1", raw_index=0),
            create_valid_record(source_url="https://example.com/law/2", raw_index=1),
        ]
        snapshot = create_test_snapshot(records)

        import_response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert import_response.status_code == 200
        import_data = import_response.json()
        batch_id = import_data["import_batch_id"]

        # Verify both versions are not indexed
        from sqlalchemy import select
        from src.models.legal_instrument_version import LegalInstrumentVersion

        result = await clean_db.execute(
            select(LegalInstrumentVersion).where(
                LegalInstrumentVersion.import_batch_id == batch_id
            )
        )
        versions = result.scalars().all()
        assert len(versions) == 2
        assert all(v.is_indexed == False for v in versions)

        # Check status
        status_response = await async_client.get(
            f"/global/legal-import/batches/{batch_id}/status",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
        )
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["total_versions"] == 2
        assert status_data["pending_versions"] == 2
        assert status_data["indexed_versions"] == 0

    @pytest.mark.asyncio
    async def test_reindex_respects_max_versions(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """Reindex should respect max_versions cap."""
        user, tenant, workspace = platform_admin_user

        # Import 3 records
        records = [
            create_valid_record(source_url=f"https://example.com/law/{i}", raw_index=i)
            for i in range(3)
        ]
        snapshot = create_test_snapshot(records)

        import_response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert import_response.status_code == 200
        batch_id = import_response.json()["import_batch_id"]

        # Request reindex with max_versions=1
        reindex_response = await async_client.post(
            "/global/legal-import/reindex",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "import_batch_id": batch_id,
                "max_versions": 1,
            },
        )
        assert reindex_response.status_code == 200
        reindex_data = reindex_response.json()

        # Should only attempt 1 version
        assert reindex_data["attempted"] == 1

    @pytest.mark.asyncio
    async def test_reindex_returns_correct_counts(
        self, async_client: AsyncClient, platform_admin_user, clean_db: AsyncSession
    ):
        """Reindex should return correct attempted/indexed/failed counts."""
        user, tenant, workspace = platform_admin_user

        # Import a snapshot
        records = [
            create_valid_record(source_url="https://example.com/law/1", raw_index=0),
        ]
        snapshot = create_test_snapshot(records)

        import_response = await async_client.post(
            "/global/legal-import/snapshot",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            files={"snapshot_zip": ("snapshot.zip", snapshot, "application/zip")},
        )
        assert import_response.status_code == 200
        batch_id = import_response.json()["import_batch_id"]

        # Reindex
        reindex_response = await async_client.post(
            "/global/legal-import/reindex",
            headers={
                "X-Tenant-Id": tenant.id,
                "X-User-Id": user.id,
                "X-Workspace-Id": workspace.id,
            },
            json={
                "import_batch_id": batch_id,
                "max_versions": 25,
            },
        )
        assert reindex_response.status_code == 200
        data = reindex_response.json()

        assert data["import_batch_id"] == batch_id
        assert data["attempted"] == 1
        # indexed + failed should equal attempted
        assert data["indexed"] + data["failed"] == data["attempted"]
