"""Tests for Document Vault API.

Test Categories:
- Integration tests: Require PostgreSQL and MinIO (with minio-init) running

Prerequisites:
    docker compose up postgres minio minio-init -d

Run all tests:
    uv run pytest tests/test_documents.py -v

Run only document tests:
    uv run pytest -m integration tests/test_documents.py -v
"""

import io
import pytest
from httpx import AsyncClient
from sqlalchemy import text

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


@pytest.fixture
async def clean_documents_db(clean_db):
    """Clean document tables before tests."""
    await clean_db.execute(text("DELETE FROM document_versions"))
    await clean_db.execute(text("DELETE FROM documents"))
    await clean_db.commit()
    yield clean_db


async def bootstrap_and_login(async_client: AsyncClient, admin_email: str = "admin@doctest.com"):
    """Helper to bootstrap tenant/workspace and get admin token."""
    bootstrap_response = await async_client.post(
        "/tenants",
        json={
            "name": "Document Test Tenant",
            "primary_jurisdiction": "UAE",
            "data_residency_policy": "UAE",
            "bootstrap": {
                "admin_user": {"password": "Testpass123", "email": admin_email, "full_name": "Doc Admin"},
                "workspace": {"name": "Doc Workspace"},
            },
        },
    )
    assert bootstrap_response.status_code == 201
    data = bootstrap_response.json()

    # Login to get token
    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": admin_email,
        },
    )
    assert login_response.status_code == 200
    token = login_response.cookies.get("access_token")
    assert token, "Expected access_token cookie from dev-login"

    return data, token


@pytest.mark.integration
class TestDocumentUpload:
    """Tests for document upload."""

    @pytest.mark.asyncio
    async def test_upload_document_success(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Successfully upload a document with initial version."""
        data, token = await bootstrap_and_login(async_client, "admin@upload1.com")

        # Upload document
        files = {
            "file": ("test.pdf", b"PDF content here", "application/pdf"),
        }
        form_data = {
            "title": "Test Contract",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "internal",
        }

        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )

        assert response.status_code == 201
        result = response.json()

        # Verify document
        assert "document" in result
        assert result["document"]["title"] == "Test Contract"
        assert result["document"]["document_type"] == "contract"
        assert result["document"]["jurisdiction"] == "UAE"
        assert result["document"]["language"] == "en"
        assert result["document"]["confidentiality"] == "internal"
        assert result["document"]["tenant_id"] == data["tenant_id"]
        assert result["document"]["workspace_id"] == data["workspace_id"]

        # Verify version
        assert "version" in result
        assert result["version"]["version_number"] == 1
        assert result["version"]["file_name"] == "test.pdf"
        assert result["version"]["content_type"] == "application/pdf"
        assert result["version"]["size_bytes"] == len(b"PDF content here")

    @pytest.mark.asyncio
    async def test_upload_document_creates_audit_log(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Document upload creates audit log entry."""
        data, token = await bootstrap_and_login(async_client, "admin@auditdoc.com")

        # Upload document
        files = {"file": ("audit_test.pdf", b"Audit test", "application/pdf")}
        form_data = {
            "title": "Audit Test Doc",
            "document_type": "memo",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "public",
        }

        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )
        assert response.status_code == 201

        # Check audit log
        audit_response = await async_client.get(
            "/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
            params={"action": "document.upload"},
        )
        assert audit_response.status_code == 200
        audit_data = audit_response.json()
        assert len(audit_data["items"]) >= 1

        # Find our upload event
        upload_event = next(
            (e for e in audit_data["items"] if e["action"] == "document.upload"),
            None,
        )
        assert upload_event is not None
        assert upload_event["status"] == "success"


@pytest.mark.integration
class TestDocumentVersioning:
    """Tests for document versioning."""

    @pytest.mark.asyncio
    async def test_upload_second_version_increments_version_number(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Uploading a new version increments the version number."""
        data, token = await bootstrap_and_login(async_client, "admin@version1.com")

        # Upload initial document
        files = {"file": ("v1.pdf", b"Version 1 content", "application/pdf")}
        form_data = {
            "title": "Versioned Doc",
            "document_type": "policy",
            "jurisdiction": "DIFC",
            "language": "en",
            "confidentiality": "confidential",
        }

        response1 = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )
        assert response1.status_code == 201
        doc_id = response1.json()["document"]["id"]
        version1_id = response1.json()["version"]["id"]

        # Upload second version
        files2 = {"file": ("v2.pdf", b"Version 2 content - updated", "application/pdf")}

        response2 = await async_client.post(
            f"/documents/{doc_id}/versions",
            headers={"Authorization": f"Bearer {token}"},
            files=files2,
        )
        assert response2.status_code == 201
        version2 = response2.json()["version"]

        assert version2["version_number"] == 2
        assert version2["file_name"] == "v2.pdf"
        assert version2["document_id"] == doc_id
        assert version2["id"] != version1_id

    @pytest.mark.asyncio
    async def test_upload_third_version(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Multiple versions increment correctly."""
        data, token = await bootstrap_and_login(async_client, "admin@version2.com")

        # Upload initial document
        files = {"file": ("v1.txt", b"v1", "text/plain")}
        form_data = {
            "title": "Multi Version Doc",
            "document_type": "other",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "public",
        }

        response1 = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )
        doc_id = response1.json()["document"]["id"]

        # Upload versions 2 and 3
        for i in range(2, 4):
            files = {"file": (f"v{i}.txt", f"v{i}".encode(), "text/plain")}
            response = await async_client.post(
                f"/documents/{doc_id}/versions",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
            )
            assert response.status_code == 201
            assert response.json()["version"]["version_number"] == i


@pytest.mark.integration
class TestDocumentListing:
    """Tests for document listing."""

    @pytest.mark.asyncio
    async def test_list_documents_returns_documents(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """List documents returns uploaded documents."""
        data, token = await bootstrap_and_login(async_client, "admin@list1.com")

        # Upload two documents
        for i in range(2):
            files = {"file": (f"doc{i}.pdf", f"Content {i}".encode(), "application/pdf")}
            form_data = {
                "title": f"Document {i}",
                "document_type": "contract",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "internal",
            }
            response = await async_client.post(
                "/documents",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=form_data,
            )
            assert response.status_code == 201

        # List documents
        list_response = await async_client.get(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        result = list_response.json()

        assert result["total"] == 2
        assert len(result["items"]) == 2
        # Each item should have latest_version
        for item in result["items"]:
            assert "latest_version" in item
            assert item["latest_version"]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """List documents supports pagination."""
        data, token = await bootstrap_and_login(async_client, "admin@paginate.com")

        # Upload 5 documents
        for i in range(5):
            files = {"file": (f"doc{i}.txt", f"Content {i}".encode(), "text/plain")}
            form_data = {
                "title": f"Page Doc {i}",
                "document_type": "memo",
                "jurisdiction": "UAE",
                "language": "en",
                "confidentiality": "public",
            }
            await async_client.post(
                "/documents",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=form_data,
            )

        # First page
        response1 = await async_client.get(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 2, "offset": 0},
        )
        result1 = response1.json()
        assert result1["total"] == 5
        assert len(result1["items"]) == 2
        assert result1["limit"] == 2
        assert result1["offset"] == 0

        # Second page
        response2 = await async_client.get(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": 2, "offset": 2},
        )
        result2 = response2.json()
        assert result2["total"] == 5
        assert len(result2["items"]) == 2
        assert result2["offset"] == 2


@pytest.mark.integration
class TestDocumentGet:
    """Tests for getting document details."""

    @pytest.mark.asyncio
    async def test_get_document_with_versions(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Get document returns all versions."""
        data, token = await bootstrap_and_login(async_client, "admin@getdoc.com")

        # Upload document
        files = {"file": ("v1.pdf", b"v1", "application/pdf")}
        form_data = {
            "title": "Get Test Doc",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "internal",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )
        doc_id = response.json()["document"]["id"]

        # Add version 2
        files2 = {"file": ("v2.pdf", b"v2", "application/pdf")}
        await async_client.post(
            f"/documents/{doc_id}/versions",
            headers={"Authorization": f"Bearer {token}"},
            files=files2,
        )

        # Get document
        get_response = await async_client.get(
            f"/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 200
        result = get_response.json()

        assert result["title"] == "Get Test Doc"
        assert len(result["versions"]) == 2
        # Versions should be ordered by version_number desc
        assert result["versions"][0]["version_number"] == 2
        assert result["versions"][1]["version_number"] == 1

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Get non-existent document returns 404."""
        data, token = await bootstrap_and_login(async_client, "admin@notfound.com")

        response = await async_client.get(
            "/documents/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestDocumentDownload:
    """Tests for document download."""

    @pytest.mark.asyncio
    async def test_download_version(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Download a specific version returns correct content."""
        data, token = await bootstrap_and_login(async_client, "admin@download.com")

        # Upload document
        content = b"This is the test content for download"
        files = {"file": ("download_test.pdf", content, "application/pdf")}
        form_data = {
            "title": "Download Test",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "internal",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )
        doc_id = response.json()["document"]["id"]
        version_id = response.json()["version"]["id"]

        # Download
        download_response = await async_client.get(
            f"/documents/{doc_id}/versions/{version_id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert download_response.status_code == 200
        assert download_response.content == content
        assert "application/pdf" in download_response.headers.get("content-type", "")
        assert "attachment" in download_response.headers.get("content-disposition", "")
        assert "download_test.pdf" in download_response.headers.get("content-disposition", "")

    @pytest.mark.asyncio
    async def test_download_creates_audit_log(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Download creates audit log entry."""
        data, token = await bootstrap_and_login(async_client, "admin@dlaudit.com")

        # Upload document
        files = {"file": ("audit_dl.txt", b"content", "text/plain")}
        form_data = {
            "title": "Audit Download Test",
            "document_type": "memo",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "public",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=form_data,
        )
        doc_id = response.json()["document"]["id"]
        version_id = response.json()["version"]["id"]

        # Download
        await async_client.get(
            f"/documents/{doc_id}/versions/{version_id}/download",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Check audit log
        audit_response = await async_client.get(
            "/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
            params={"action": "document.download"},
        )
        assert audit_response.status_code == 200
        audit_data = audit_response.json()

        download_event = next(
            (e for e in audit_data["items"] if e["action"] == "document.download"),
            None,
        )
        assert download_event is not None
        assert download_event["status"] == "success"


@pytest.mark.integration
class TestRoleBasedAccess:
    """Tests for role-based access control."""

    @pytest.mark.asyncio
    async def test_viewer_can_list_documents(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """VIEWER role can list documents."""
        data, admin_token = await bootstrap_and_login(async_client, "admin@viewertest.com")

        # Create viewer user
        viewer_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "viewer@viewertest.com"},
        )
        viewer_id = viewer_response.json()["id"]

        # Add viewer to workspace
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": viewer_id, "role": "VIEWER"},
        )

        # Get viewer token
        viewer_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "viewer@viewertest.com",
            },
        )
        viewer_token = viewer_login.cookies.get("access_token")
        assert viewer_token

        # Upload document as admin
        files = {"file": ("admin.pdf", b"admin content", "application/pdf")}
        form_data = {
            "title": "Admin Doc",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "internal",
        }
        await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=form_data,
        )

        # Viewer can list
        list_response = await async_client.get(
            "/documents",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_viewer_cannot_upload(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """VIEWER role cannot upload documents."""
        data, admin_token = await bootstrap_and_login(async_client, "admin@viewernoupload.com")

        # Create viewer user
        viewer_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "viewer@viewernoupload.com"},
        )
        viewer_id = viewer_response.json()["id"]

        # Add viewer to workspace
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": viewer_id, "role": "VIEWER"},
        )

        # Get viewer token
        viewer_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "viewer@viewernoupload.com",
            },
        )
        viewer_token = viewer_login.cookies.get("access_token")
        assert viewer_token

        # Viewer tries to upload - should fail
        files = {"file": ("viewer.pdf", b"viewer content", "application/pdf")}
        form_data = {
            "title": "Viewer Doc",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "internal",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {viewer_token}"},
            files=files,
            data=form_data,
        )
        assert response.status_code == 403
        assert "EDITOR" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_viewer_can_download(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """VIEWER role can download documents."""
        data, admin_token = await bootstrap_and_login(async_client, "admin@viewerdl.com")

        # Create viewer
        viewer_response = await async_client.post(
            f"/tenants/{data['tenant_id']}/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"email": "viewer@viewerdl.com"},
        )
        viewer_id = viewer_response.json()["id"]

        await async_client.post(
            f"/workspaces/{data['workspace_id']}/memberships",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"user_id": viewer_id, "role": "VIEWER"},
        )

        viewer_login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "viewer@viewerdl.com",
            },
        )
        viewer_token = viewer_login.cookies.get("access_token")
        assert viewer_token

        # Admin uploads document
        content = b"downloadable content"
        files = {"file": ("dltest.pdf", content, "application/pdf")}
        form_data = {
            "title": "DL Test",
            "document_type": "memo",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "public",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=form_data,
        )
        doc_id = response.json()["document"]["id"]
        version_id = response.json()["version"]["id"]

        # Viewer downloads
        dl_response = await async_client.get(
            f"/documents/{doc_id}/versions/{version_id}/download",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert dl_response.status_code == 200
        assert dl_response.content == content


@pytest.mark.integration
class TestPolicyEnforcement:
    """Tests for policy enforcement on upload."""

    @pytest.mark.asyncio
    async def test_upload_blocked_by_language_policy(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Upload blocked when language not in policy allowlist."""
        data, admin_token = await bootstrap_and_login(async_client, "admin@langpolicy.com")

        # Create restrictive policy that only allows English
        policy_response = await async_client.post(
            "/policy-profiles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "English Only Policy",
                "description": "Only allows English documents",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en"],  # Only English!
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE", "DIFC", "ADGM", "KSA"],
                    "feature_flags": {},
                },
            },
        )
        assert policy_response.status_code == 201
        policy_id = policy_response.json()["id"]

        # Attach policy to workspace
        attach_response = await async_client.post(
            f"/workspaces/{data['workspace_id']}/policy-profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"policy_profile_id": policy_id},
        )
        assert attach_response.status_code == 200

        # Try to upload Arabic document - should fail
        files = {"file": ("arabic.pdf", b"Arabic content", "application/pdf")}
        form_data = {
            "title": "Arabic Contract",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "ar",  # Arabic - not allowed!
            "confidentiality": "internal",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=form_data,
        )
        assert response.status_code == 403
        assert "language" in response.json()["detail"].lower()
        assert "'ar'" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_blocked_by_jurisdiction_policy(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Upload blocked when jurisdiction not in policy allowlist."""
        data, admin_token = await bootstrap_and_login(async_client, "admin@jurispolicy.com")

        # Create policy that only allows UAE
        policy_response = await async_client.post(
            "/policy-profiles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "UAE Only Policy",
                "config": {
                    "allowed_workflows": [],
                    "allowed_input_languages": ["en", "ar", "mixed"],
                    "allowed_output_languages": ["en"],
                    "allowed_jurisdictions": ["UAE"],  # Only UAE!
                    "feature_flags": {},
                },
            },
        )
        policy_id = policy_response.json()["id"]

        # Attach policy
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/policy-profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"policy_profile_id": policy_id},
        )

        # Try to upload DIFC document - should fail
        files = {"file": ("difc.pdf", b"DIFC content", "application/pdf")}
        form_data = {
            "title": "DIFC Contract",
            "document_type": "contract",
            "jurisdiction": "DIFC",  # Not allowed!
            "language": "en",
            "confidentiality": "internal",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=form_data,
        )
        assert response.status_code == 403
        assert "jurisdiction" in response.json()["detail"].lower()
        assert "'DIFC'" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_allowed_when_policy_permits(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Upload succeeds when language and jurisdiction are allowed."""
        data, admin_token = await bootstrap_and_login(async_client, "admin@permissive.com")

        # Create permissive policy
        policy_response = await async_client.post(
            "/policy-profiles",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "name": "Permissive Policy",
                "config": {
                    "allowed_workflows": ["*"],
                    "allowed_input_languages": ["en", "ar", "mixed"],
                    "allowed_output_languages": ["en", "ar"],
                    "allowed_jurisdictions": ["UAE", "DIFC", "ADGM", "KSA"],
                    "feature_flags": {},
                },
            },
        )
        policy_id = policy_response.json()["id"]

        # Attach policy
        await async_client.post(
            f"/workspaces/{data['workspace_id']}/policy-profile",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"policy_profile_id": policy_id},
        )

        # Upload Arabic DIFC document - should succeed
        files = {"file": ("allowed.pdf", b"Allowed content", "application/pdf")}
        form_data = {
            "title": "Allowed Contract",
            "document_type": "contract",
            "jurisdiction": "DIFC",
            "language": "ar",
            "confidentiality": "internal",
        }
        response = await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {admin_token}"},
            files=files,
            data=form_data,
        )
        assert response.status_code == 201


@pytest.mark.integration
class TestTenantIsolation:
    """Tests for tenant and workspace isolation."""

    @pytest.mark.asyncio
    async def test_documents_isolated_between_workspaces(
        self,
        async_client: AsyncClient,
        clean_documents_db,
    ):
        """Documents in one workspace are not visible in another."""
        # Create first tenant/workspace
        data1, token1 = await bootstrap_and_login(async_client, "admin@ws1.com")

        # Upload document in workspace 1
        files = {"file": ("ws1.pdf", b"WS1 content", "application/pdf")}
        form_data = {
            "title": "WS1 Doc",
            "document_type": "contract",
            "jurisdiction": "UAE",
            "language": "en",
            "confidentiality": "internal",
        }
        await async_client.post(
            "/documents",
            headers={"Authorization": f"Bearer {token1}"},
            files=files,
            data=form_data,
        )

        # Create second tenant/workspace
        data2, token2 = await bootstrap_and_login(async_client, "admin@ws2.com")

        # List documents in workspace 2 - should be empty
        list_response = await async_client.get(
            "/documents",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 0

        # List in workspace 1 - should have 1 document
        list_response1 = await async_client.get(
            "/documents",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert list_response1.json()["total"] == 1
