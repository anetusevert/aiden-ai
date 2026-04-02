"""Tests for cookie-based authentication with refresh token rotation.

Test Categories:
- Unit tests (TestJWTTokenTypes): No database required
- Integration tests (all others): Require PostgreSQL running

Run unit tests only:
    uv run pytest tests/test_cookie_auth.py::TestJWTTokenTypes -v

Run integration tests only:
    uv run pytest -m integration tests/test_cookie_auth.py -v
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models import RefreshSession, User
from src.utils.jwt import (
    TokenTypeMismatchError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


@pytest.mark.unit
class TestJWTTokenTypes:
    """Unit tests for JWT token type handling.

    These tests do NOT require a database connection.
    Run with: uv run pytest tests/test_cookie_auth.py::TestJWTTokenTypes -v
    """

    def test_access_token_has_correct_type(self):
        """Access token has token_type='access'."""
        token = create_access_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
        )

        payload = decode_access_token(token)
        assert payload.token_type == "access"

    def test_refresh_token_has_correct_type_and_jti(self):
        """Refresh token has token_type='refresh' and a jti claim."""
        token, jti, expires_at = create_refresh_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
        )

        payload = decode_refresh_token(token)
        assert payload.token_type == "refresh"
        assert payload.jti == jti
        assert payload.jti is not None

    def test_decode_access_token_rejects_refresh_token(self):
        """decode_access_token raises TokenTypeMismatchError for refresh tokens."""
        token, _, _ = create_refresh_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
        )

        with pytest.raises(TokenTypeMismatchError):
            decode_access_token(token)

    def test_decode_refresh_token_rejects_access_token(self):
        """decode_refresh_token raises TokenTypeMismatchError for access tokens."""
        token = create_access_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
        )

        with pytest.raises(TokenTypeMismatchError):
            decode_refresh_token(token)

    def test_refresh_token_custom_jti(self):
        """Refresh token can be created with custom jti."""
        custom_jti = "custom-unique-id-123"
        token, jti, _ = create_refresh_token(
            user_id="test-user-id",
            tenant_id="test-tenant-id",
            workspace_id="test-workspace-id",
            role="ADMIN",
            jti=custom_jti,
        )

        assert jti == custom_jti
        payload = decode_refresh_token(token)
        assert payload.jti == custom_jti


@pytest.mark.integration
class TestCookieDevLogin:
    """Tests for cookie-based /auth/dev-login endpoint."""

    @pytest.mark.asyncio
    async def test_dev_login_sets_cookies(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Dev login sets access_token and refresh_token cookies."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Cookie Auth Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@cookietest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Dev login
        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@cookietest.com",
            },
        )
        assert login.status_code == 200

        # Check response body
        login_data = login.json()
        assert login_data["auth_mode"] == "cookie"
        assert login_data["user_id"] == data["admin_user_id"]
        assert login_data["email"] == "admin@cookietest.com"
        assert login_data["expires_in"] == settings.access_token_expires_minutes * 60

        # Check cookies are set
        cookies = login.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    @pytest.mark.asyncio
    async def test_dev_login_creates_refresh_session(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Dev login creates a refresh session in the database."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Session Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@sessiontest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Dev login
        await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@sessiontest.com",
            },
        )

        # Check refresh session exists
        result = await clean_db.execute(
            select(RefreshSession).where(RefreshSession.user_id == data["admin_user_id"])
        )
        session = result.scalar_one_or_none()
        assert session is not None
        assert session.revoked_at is None
        assert session.jti is not None

    @pytest.mark.asyncio
    async def test_dev_login_cookie_attributes(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Dev login sets cookies with correct attributes (Path, SameSite, HttpOnly)."""
        # Bootstrap tenant
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Cookie Attrs Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@cookieattrs.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Dev login
        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@cookieattrs.com",
            },
        )
        assert login.status_code == 200

        # Parse Set-Cookie headers
        set_cookie_headers = login.headers.get_list("set-cookie")
        assert len(set_cookie_headers) >= 2, "Expected at least 2 Set-Cookie headers"

        # Find access_token and refresh_token cookies
        access_cookie = None
        refresh_cookie = None
        for header in set_cookie_headers:
            if header.startswith("access_token="):
                access_cookie = header
            elif header.startswith("refresh_token="):
                refresh_cookie = header

        assert access_cookie is not None, "access_token cookie not found"
        assert refresh_cookie is not None, "refresh_token cookie not found"

        # Verify access_token attributes
        access_lower = access_cookie.lower()
        assert "httponly" in access_lower, "access_token missing HttpOnly"
        assert "samesite=lax" in access_lower, "access_token missing SameSite=Lax"
        assert "path=/" in access_lower, "access_token missing Path=/"
        # In dev environment, Secure should be absent or false
        if settings.environment == "dev":
            assert "secure" not in access_lower or "secure=false" in access_lower or (
                "; secure" not in access_lower
            ), "access_token should not have Secure in dev"

        # Verify refresh_token attributes
        refresh_lower = refresh_cookie.lower()
        assert "httponly" in refresh_lower, "refresh_token missing HttpOnly"
        assert "samesite=lax" in refresh_lower, "refresh_token missing SameSite=Lax"
        assert "path=/auth" in refresh_lower, "refresh_token missing Path=/auth"
        # In dev environment, Secure should be absent or false
        if settings.environment == "dev":
            assert "secure" not in refresh_lower or "secure=false" in refresh_lower or (
                "; secure" not in refresh_lower
            ), "refresh_token should not have Secure in dev"


@pytest.mark.integration
class TestCookieAuthMe:
    """Tests for /auth/me with cookie authentication."""

    @pytest.mark.asyncio
    async def test_auth_me_works_with_cookie(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """GET /auth/me works with access_token cookie."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Me Cookie Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@mecookie.com", "full_name": "Cookie Admin"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@mecookie.com",
            },
        )
        cookies = login.cookies

        # Call /auth/me with cookie
        me_response = await async_client.get(
            "/auth/me",
            cookies={"access_token": cookies["access_token"]},
        )
        assert me_response.status_code == 200

        me_data = me_response.json()
        assert me_data["user_id"] == data["admin_user_id"]
        assert me_data["email"] == "admin@mecookie.com"
        assert me_data["auth_mode"] == "cookie"


@pytest.mark.integration
class TestRefreshTokenRotation:
    """Tests for /auth/refresh endpoint with token rotation."""

    @pytest.mark.asyncio
    async def test_refresh_rotates_tokens(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """POST /auth/refresh rotates refresh token and issues new access token."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Refresh Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@refreshtest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@refreshtest.com",
            },
        )
        original_cookies = login.cookies
        original_refresh = original_cookies["refresh_token"]

        # Refresh
        refresh = await async_client.post(
            "/auth/refresh",
            cookies={"refresh_token": original_refresh},
        )
        assert refresh.status_code == 200

        refresh_data = refresh.json()
        assert refresh_data["auth_mode"] == "cookie"
        assert refresh_data["expires_in"] == settings.access_token_expires_minutes * 60

        # New cookies should be set
        new_cookies = refresh.cookies
        assert "access_token" in new_cookies
        assert "refresh_token" in new_cookies
        assert new_cookies["refresh_token"] != original_refresh

    @pytest.mark.asyncio
    async def test_refresh_revokes_old_session(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """POST /auth/refresh revokes the old refresh session."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Revoke Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@revoketest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@revoketest.com",
            },
        )

        # Get original session
        result = await clean_db.execute(
            select(RefreshSession)
            .where(RefreshSession.user_id == data["admin_user_id"])
            .where(RefreshSession.revoked_at.is_(None))
        )
        original_session = result.scalar_one()
        original_jti = original_session.jti

        # Refresh
        await async_client.post(
            "/auth/refresh",
            cookies={"refresh_token": login.cookies["refresh_token"]},
        )

        # Re-query to see updated state
        await clean_db.expire_all()
        result = await clean_db.execute(
            select(RefreshSession).where(RefreshSession.jti == original_jti)
        )
        old_session = result.scalar_one()
        assert old_session.revoked_at is not None

        # New session should exist
        result = await clean_db.execute(
            select(RefreshSession)
            .where(RefreshSession.user_id == data["admin_user_id"])
            .where(RefreshSession.revoked_at.is_(None))
        )
        new_session = result.scalar_one()
        assert new_session.jti != original_jti

    @pytest.mark.asyncio
    async def test_reused_refresh_token_detected(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Using a revoked refresh token returns 401 with refresh_reuse_detected."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Reuse Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@reusetest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@reusetest.com",
            },
        )
        original_refresh = login.cookies["refresh_token"]

        # First refresh (should succeed)
        refresh1 = await async_client.post(
            "/auth/refresh",
            cookies={"refresh_token": original_refresh},
        )
        assert refresh1.status_code == 200

        # Try to reuse original refresh token (should fail)
        refresh2 = await async_client.post(
            "/auth/refresh",
            cookies={"refresh_token": original_refresh},
        )
        assert refresh2.status_code == 401

        error = refresh2.json()
        assert error["detail"]["error_code"] == "refresh_reuse_detected"


@pytest.mark.integration
class TestLogout:
    """Tests for /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_clears_cookies_and_revokes_session(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """POST /auth/logout clears cookies and revokes refresh session."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Logout Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@logouttest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@logouttest.com",
            },
        )

        # Logout
        logout = await async_client.post(
            "/auth/logout",
            cookies={
                "access_token": login.cookies["access_token"],
                "refresh_token": login.cookies["refresh_token"],
            },
        )
        assert logout.status_code == 200
        assert logout.json()["message"] == "Successfully logged out"

        # Session should be revoked
        await clean_db.expire_all()
        result = await clean_db.execute(
            select(RefreshSession)
            .where(RefreshSession.user_id == data["admin_user_id"])
        )
        session = result.scalar_one()
        assert session.revoked_at is not None

    @pytest.mark.asyncio
    async def test_logout_clears_cookies_with_correct_path(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """POST /auth/logout clears cookies with correct Path attributes."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Logout Path Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@logoutpath.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@logoutpath.com",
            },
        )

        # Logout
        logout = await async_client.post(
            "/auth/logout",
            cookies={
                "access_token": login.cookies["access_token"],
                "refresh_token": login.cookies["refresh_token"],
            },
        )
        assert logout.status_code == 200

        # Parse Set-Cookie headers for clearing
        set_cookie_headers = logout.headers.get_list("set-cookie")
        assert len(set_cookie_headers) >= 2, "Expected at least 2 Set-Cookie headers for clearing"

        # Find clearing cookies
        access_clear = None
        refresh_clear = None
        for header in set_cookie_headers:
            if header.startswith("access_token="):
                access_clear = header
            elif header.startswith("refresh_token="):
                refresh_clear = header

        assert access_clear is not None, "access_token clear cookie not found"
        assert refresh_clear is not None, "refresh_token clear cookie not found"

        # Verify clearing with correct path
        access_lower = access_clear.lower()
        refresh_lower = refresh_clear.lower()

        # Cookies should be cleared (max-age=0 or expires in past)
        assert "max-age=0" in access_lower or "expires=" in access_lower
        assert "max-age=0" in refresh_lower or "expires=" in refresh_lower

        # Path must match original setting for cookies to be cleared properly
        assert "path=/" in access_lower, "access_token clear missing Path=/"
        assert "path=/auth" in refresh_lower, "refresh_token clear missing Path=/auth"


@pytest.mark.integration
class TestLogoutAll:
    """Tests for /auth/logout-all endpoint."""

    @pytest.mark.asyncio
    async def test_logout_all_increments_token_version(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """POST /auth/logout-all increments user.token_version."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Logout All Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@logoutall.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@logoutall.com",
            },
        )

        # Get original token_version
        result = await clean_db.execute(
            select(User).where(User.id == data["admin_user_id"])
        )
        user = result.scalar_one()
        original_version = user.token_version

        # Logout all
        logout = await async_client.post(
            "/auth/logout-all",
            cookies={"access_token": login.cookies["access_token"]},
        )
        assert logout.status_code == 200

        # Token version should be incremented
        await clean_db.expire_all()
        result = await clean_db.execute(
            select(User).where(User.id == data["admin_user_id"])
        )
        user = result.scalar_one()
        assert user.token_version == original_version + 1

    @pytest.mark.asyncio
    async def test_logout_all_revokes_all_sessions(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """POST /auth/logout-all revokes all refresh sessions."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Revoke All Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@revokeall.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        # Login twice to create multiple sessions
        login1 = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@revokeall.com",
            },
        )

        await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@revokeall.com",
            },
        )

        # Should have 2 sessions
        result = await clean_db.execute(
            select(RefreshSession)
            .where(RefreshSession.user_id == data["admin_user_id"])
            .where(RefreshSession.revoked_at.is_(None))
        )
        sessions = result.scalars().all()
        assert len(sessions) == 2

        # Logout all
        await async_client.post(
            "/auth/logout-all",
            cookies={"access_token": login1.cookies["access_token"]},
        )

        # All sessions should be revoked
        await clean_db.expire_all()
        result = await clean_db.execute(
            select(RefreshSession)
            .where(RefreshSession.user_id == data["admin_user_id"])
            .where(RefreshSession.revoked_at.is_(None))
        )
        sessions = result.scalars().all()
        assert len(sessions) == 0


@pytest.mark.integration
class TestTokenVersionMismatch:
    """Tests for token_version validation."""

    @pytest.mark.asyncio
    async def test_token_version_mismatch_returns_token_revoked(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ):
        """Access token with wrong token_version returns token_revoked error."""
        # Bootstrap and login
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Version Test",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {"password": "Testpass123", "email": "admin@versiontest.com"},
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@versiontest.com",
            },
        )
        access_token = login.cookies["access_token"]

        # Increment token_version directly
        result = await clean_db.execute(
            select(User).where(User.id == data["admin_user_id"])
        )
        user = result.scalar_one()
        user.token_version += 1
        await clean_db.commit()

        # Access token should now be invalid
        me_response = await async_client.get(
            "/auth/me",
            cookies={"access_token": access_token},
        )
        assert me_response.status_code == 401

        error = me_response.json()
        assert error["detail"]["error_code"] == "token_revoked"
