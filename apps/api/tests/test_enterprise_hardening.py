"""Tests for enterprise hardening features (Agent #22).

This module tests:
- WorkflowResultStatus enum in workflow responses
- Prompt/model fingerprinting
- Token version for session revocation
- Environment safety rails
- Audit log enhancements
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import AuditLog, User
from src.schemas.workflow_status import WorkflowResultStatus
from src.utils.jwt import create_access_token, decode_access_token
from src.utils.hashing import hash_prompt, hash_question, hash_text


# =============================================================================
# WorkflowResultStatus Enum Tests
# =============================================================================


class TestWorkflowResultStatus:
    """Tests for WorkflowResultStatus enum."""

    def test_status_values_are_strings(self):
        """Status values should be string-compatible for JSON serialization."""
        assert WorkflowResultStatus.SUCCESS.value == "success"
        assert WorkflowResultStatus.INSUFFICIENT_SOURCES.value == "insufficient_sources"
        assert WorkflowResultStatus.POLICY_DENIED.value == "policy_denied"
        assert WorkflowResultStatus.CITATION_VIOLATION.value == "citation_violation"
        assert WorkflowResultStatus.VALIDATION_FAILED.value == "validation_failed"
        assert WorkflowResultStatus.GENERATION_FAILED.value == "generation_failed"

    def test_all_statuses_defined(self):
        """All required statuses should be defined."""
        expected = {
            "success",
            "insufficient_sources",
            "policy_denied",
            "citation_violation",
            "validation_failed",
            "generation_failed",
        }
        actual = {s.value for s in WorkflowResultStatus}
        assert actual == expected


# =============================================================================
# Prompt Hash Tests
# =============================================================================


class TestHashingUtilities:
    """Tests for unified hashing utilities (src.utils.hashing)."""

    def test_hash_prompt_deterministic(self):
        """Same prompt should produce same hash."""
        prompt = "Test prompt for hashing"
        hash1 = hash_prompt(prompt)
        hash2 = hash_prompt(prompt)
        assert hash1 == hash2

    def test_hash_prompt_different_prompts(self):
        """Different prompts should produce different hashes."""
        hash1 = hash_prompt("Prompt A")
        hash2 = hash_prompt("Prompt B")
        assert hash1 != hash2

    def test_hash_prompt_with_system_prompt(self):
        """System prompt should be included in hash."""
        prompt = "User prompt"
        system = "System instructions"
        
        hash_without = hash_prompt(prompt)
        hash_with = hash_prompt(prompt, system)
        
        assert hash_without != hash_with

    def test_hash_is_sha256_length(self):
        """Hash should be SHA256 format (64 hex chars)."""
        hash_result = hash_prompt("Test")
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_hash_question_deterministic(self):
        """hash_question should be deterministic."""
        question = "What is the termination clause?"
        hash1 = hash_question(question)
        hash2 = hash_question(question)
        assert hash1 == hash2

    def test_hash_text_is_base_function(self):
        """hash_text should produce same result as hash_question for same input."""
        text = "Some text to hash"
        assert hash_text(text) == hash_question(text)

    def test_hash_functions_consistency(self):
        """All hash functions should use same underlying algorithm."""
        # hash_prompt with no system prompt should equal hash_text
        text = "Same text"
        assert hash_prompt(text) == hash_text(text)
        assert hash_prompt(text) == hash_question(text)


# =============================================================================
# Token Version Tests
# =============================================================================


class TestTokenVersion:
    """Tests for token_version in JWT."""

    def test_create_token_with_version(self):
        """Token should include token_version claim."""
        token = create_access_token(
            user_id="user-123",
            tenant_id="tenant-456",
            workspace_id="workspace-789",
            role="ADMIN",
            token_version=5,
        )
        
        payload = decode_access_token(token)
        assert payload.token_version == 5

    def test_create_token_default_version(self):
        """Token should default to version 1 if not specified."""
        token = create_access_token(
            user_id="user-123",
            tenant_id="tenant-456",
            workspace_id="workspace-789",
            role="ADMIN",
        )
        
        payload = decode_access_token(token)
        assert payload.token_version == 1


@pytest.mark.asyncio
class TestTokenVersionValidation:
    """Integration tests for token_version validation."""

    async def test_user_has_token_version_column(
        self,
        tenant_factory,
        user_factory,
    ):
        """User model should have token_version column."""
        tenant = await tenant_factory()
        user = await user_factory(tenant)
        
        assert hasattr(user, "token_version")
        assert user.token_version == 1  # Default value

    async def test_old_token_fails_after_logout_all(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Token should fail validation after token_version is incremented."""
        # Create test entities
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant)
        await membership_factory(workspace, user, role="ADMIN")
        
        # Create token with current version
        old_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            role="ADMIN",
            token_version=user.token_version,
        )
        
        # Verify token works initially
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 200
        
        # Increment token_version (simulating logout-all)
        user.token_version += 1
        clean_db.add(user)
        await clean_db.commit()
        
        # Old token should now fail
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 401

    async def test_token_revoked_returns_structured_error(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Token revocation should return structured error with error_code."""
        # Create test entities
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant)
        await membership_factory(workspace, user, role="ADMIN")
        
        # Create token with old version
        old_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            role="ADMIN",
            token_version=user.token_version,
        )
        
        # Increment token_version
        user.token_version += 1
        clean_db.add(user)
        await clean_db.commit()
        
        # Old token should return structured error
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert response.status_code == 401
        
        # Verify structured error format
        detail = response.json().get("detail", {})
        assert isinstance(detail, dict), "detail should be a dict for token_revoked"
        assert detail.get("error_code") == "token_revoked"
        assert "session" in detail.get("message", "").lower()
        assert "sign in" in detail.get("message", "").lower()


# =============================================================================
# Environment Safety Rails Tests
# =============================================================================


class TestEnvironmentSafetyRails:
    """Tests for environment safety rails."""

    def test_dev_environment_allows_dev_login(self):
        """Dev environment should allow dev login."""
        settings = Settings(
            environment="dev",
            auth_allow_dev_login=True,
            _env_file=None,  # Don't load .env
        )
        assert settings.environment == "dev"
        assert settings.auth_allow_dev_login is True

    def test_staging_rejects_dev_login(self):
        """Staging environment should reject dev login=true."""
        with pytest.raises(ValueError) as exc_info:
            Settings(
                environment="staging",
                auth_allow_dev_login=True,
                _env_file=None,
            )
        assert "auth_allow_dev_login" in str(exc_info.value).lower()
        assert "staging" in str(exc_info.value).lower()

    def test_prod_rejects_dev_login(self):
        """Prod environment should reject dev login=true."""
        with pytest.raises(ValueError) as exc_info:
            Settings(
                environment="prod",
                auth_allow_dev_login=True,
                _env_file=None,
            )
        assert "auth_allow_dev_login" in str(exc_info.value).lower()
        assert "prod" in str(exc_info.value).lower()

    def test_error_message_contains_remediation_steps(self):
        """Error message should contain clear remediation steps."""
        with pytest.raises(ValueError) as exc_info:
            Settings(
                environment="prod",
                auth_allow_dev_login=True,
                _env_file=None,
            )
        error_msg = str(exc_info.value)
        # Should mention current configuration
        assert "ENVIRONMENT = prod" in error_msg
        assert "AUTH_ALLOW_DEV_LOGIN = true" in error_msg
        # Should contain remediation options
        assert "ENVIRONMENT=dev" in error_msg
        assert "AUTH_ALLOW_DEV_LOGIN=false" in error_msg
        # Should be clear about the problem
        assert "forbidden" in error_msg.lower() or "not allowed" in error_msg.lower()

    def test_staging_allows_dev_login_false(self):
        """Staging should work with dev login disabled."""
        settings = Settings(
            environment="staging",
            auth_allow_dev_login=False,
            _env_file=None,
        )
        assert settings.environment == "staging"
        assert settings.auth_allow_dev_login is False

    def test_prod_allows_dev_login_false(self):
        """Prod should work with dev login disabled."""
        settings = Settings(
            environment="prod",
            auth_allow_dev_login=False,
            _env_file=None,
        )
        assert settings.environment == "prod"
        assert settings.auth_allow_dev_login is False


# =============================================================================
# Health Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Tests for /health endpoint."""

    async def test_health_returns_environment(
        self,
        async_client: AsyncClient,
    ):
        """Health endpoint should return environment."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "environment" in data
        assert data["status"] == "ok"
        # Default environment in tests is "dev"
        assert data["environment"] in ("dev", "staging", "prod")


# =============================================================================
# Logout-All Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
class TestLogoutAllEndpoint:
    """Tests for /auth/logout-all endpoint."""

    async def test_logout_all_increments_token_version(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """logout-all should increment user's token_version."""
        # Create test entities
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant)
        await membership_factory(workspace, user, role="ADMIN")
        
        initial_version = user.token_version
        
        # Create token
        token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            role="ADMIN",
            token_version=initial_version,
        )
        
        # Call logout-all
        response = await async_client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        
        # Refresh user from DB
        await clean_db.refresh(user)
        assert user.token_version == initial_version + 1

    async def test_logout_all_creates_audit_log(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """logout-all should create audit log entry."""
        # Create test entities
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant)
        await membership_factory(workspace, user, role="ADMIN")
        
        token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            role="ADMIN",
            token_version=user.token_version,
        )
        
        # Clear audit logs
        await clean_db.execute(text("DELETE FROM audit_logs"))
        await clean_db.commit()
        
        # Call logout-all
        response = await async_client.post(
            "/auth/logout-all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        
        # Check audit log
        result = await clean_db.execute(
            select(AuditLog).where(AuditLog.action == "auth.logout_all")
        )
        audit_log = result.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.status == "success"
        assert audit_log.user_id == user.id


# =============================================================================
# Workflow Audit Log Tests
# =============================================================================


@pytest.mark.asyncio
class TestWorkflowAuditLogs:
    """Tests for workflow audit log enhancements."""

    async def test_audit_log_includes_environment(
        self,
        tenant_factory,
        workspace_factory,
        user_factory,
        membership_factory,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Audit logs should include environment field in meta."""
        # Create test entities with proper setup
        tenant = await tenant_factory()
        workspace = await workspace_factory(tenant)
        user = await user_factory(tenant)
        await membership_factory(workspace, user, role="ADMIN")
        
        token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            role="ADMIN",
            token_version=user.token_version,
        )
        
        # Clear existing logs
        await clean_db.execute(text("DELETE FROM audit_logs"))
        await clean_db.commit()
        
        # Make a request that creates an audit log (auth.me)
        await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        # Check audit log includes environment
        result = await clean_db.execute(
            select(AuditLog).where(AuditLog.action == "auth.me")
        )
        audit_log = result.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.meta is not None
        assert "environment" in audit_log.meta
