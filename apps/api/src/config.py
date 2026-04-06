"""Application configuration using pydantic-settings."""

import logging
import os
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Track if we've already warned about legacy env vars
_legacy_warning_emitted = False


def _get_with_fallback(primary_key: str, fallback_key: str, default: str) -> str:
    """Get env var with fallback to legacy key, emitting warning if fallback used.

    Args:
        primary_key: Canonical S3_* env var name
        fallback_key: Legacy AWS_* env var name
        default: Default value if neither is set

    Returns:
        The resolved value
    """
    global _legacy_warning_emitted

    primary_value = os.environ.get(primary_key)
    if primary_value is not None:
        return primary_value

    fallback_value = os.environ.get(fallback_key)
    if fallback_value is not None:
        if not _legacy_warning_emitted:
            logger.warning(
                "Using legacy AWS_* env vars; please migrate to S3_*. "
                "See apps/api/README.md for canonical variable names."
            )
            _legacy_warning_emitted = True
        return fallback_value

    return default


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment (dev | staging | prod)
    # Controls safety rails for features like dev-login
    environment: Literal["dev", "staging", "prod"] = "dev"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # API Root Path (for reverse proxy mounting)
    # Set to "/api" when running behind a reverse proxy that mounts at /api
    # Default is empty string (root path) for direct access
    api_root_path: str = ""

    # Database
    database_url: str = "postgresql://aiden:aiden_dev_password@localhost:5432/aiden"

    # Test Database (uses same postgres but different database name)
    test_database_url: str = (
        "postgresql://aiden:aiden_dev_password@localhost:5432/aiden_test"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Collabora / WOPI
    # collabora_url  — browser-accessible URL for the Collabora iframe (localhost:9980)
    # wopi_internal_url — Docker-internal URL Collabora server calls for WOPI (api:8000)
    # wopi_public_url   — browser-accessible API URL shown in editor URLs (localhost:8000)
    # wopi_base_url     — legacy alias for wopi_internal_url, kept for backwards compat
    collabora_url: str = "http://localhost:9980"
    wopi_internal_url: str = "http://api:8000/api/v1/wopi"
    wopi_public_url: str = "http://localhost:8000/api/v1/wopi"
    wopi_base_url: str = "http://localhost:8000/api/v1/wopi"  # legacy

    # =========================================================================
    # S3/MinIO Storage Configuration (Canonical: S3_*)
    # =========================================================================
    # Primary vars: S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY,
    #               S3_BUCKET_NAME, S3_REGION, S3_USE_SSL, S3_FORCE_PATH_STYLE
    # Legacy fallback (deprecated): AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID,
    #                               AWS_SECRET_ACCESS_KEY
    # =========================================================================

    # These are set via model_validator to support fallback logic
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "aiden-storage"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    s3_force_path_style: bool = True  # Required for MinIO

    @model_validator(mode="before")
    @classmethod
    def resolve_s3_vars_with_fallback(cls, values: dict) -> dict:
        """Resolve S3 vars with fallback to legacy AWS_* vars."""
        # Only apply fallback logic if the canonical var is not in values
        # This allows explicit settings to take precedence

        if "s3_endpoint_url" not in values or values.get("s3_endpoint_url") is None:
            values["s3_endpoint_url"] = _get_with_fallback(
                "S3_ENDPOINT_URL", "AWS_ENDPOINT_URL", "http://localhost:9000"
            )

        if "s3_access_key_id" not in values or values.get("s3_access_key_id") is None:
            values["s3_access_key_id"] = _get_with_fallback(
                "S3_ACCESS_KEY_ID", "AWS_ACCESS_KEY_ID", "minioadmin"
            )

        if (
            "s3_secret_access_key" not in values
            or values.get("s3_secret_access_key") is None
        ):
            values["s3_secret_access_key"] = _get_with_fallback(
                "S3_SECRET_ACCESS_KEY", "AWS_SECRET_ACCESS_KEY", "minioadmin"
            )

        if "s3_bucket_name" not in values or values.get("s3_bucket_name") is None:
            # Also check legacy MINIO_BUCKET
            bucket = os.environ.get("S3_BUCKET_NAME")
            if bucket is None:
                bucket = os.environ.get("MINIO_BUCKET", "aiden-storage")
            values["s3_bucket_name"] = bucket

        return values

    # CORS - stored as comma-separated string, accessed via property
    cors_origins_str: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "http://localhost:3100,http://127.0.0.1:3100,"
        "http://localhost:3101,http://127.0.0.1:3101,"
        "http://localhost:9980,http://127.0.0.1:9980"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    # Authentication
    # AUTH_MODE: "jwt" uses Bearer tokens, "headers" uses legacy X-*-Id headers
    auth_mode: Literal["jwt", "headers"] = "jwt"

    # JWT Configuration
    # WARNING: This default is for development only. Set a strong secret in production!
    jwt_secret: str = "INSECURE_DEV_SECRET_CHANGE_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60  # Legacy: kept for backwards compatibility

    # Cookie-based Auth (v2 - httpOnly cookies)
    # ACCESS_TOKEN_EXPIRES_MINUTES: Short-lived access token (default: 15 min)
    # REFRESH_TOKEN_EXPIRES_DAYS: Long-lived refresh token (default: 7 days)
    access_token_expires_minutes: int = 15
    refresh_token_expires_days: int = 7

    # Cookie security settings
    # In dev: Secure=false (allows localhost without HTTPS)
    # In staging/prod: Secure=true (enforced even before SSL setup)
    cookie_secure: bool | None = None  # Auto-derived from environment if None

    # SameSite policy for auth cookies.
    # "lax"  — default, safe for same-site deployments
    # "none" — required when frontend and API are on different sites
    #          (e.g. separate Railway *.up.railway.app subdomains)
    #          Requires Secure=true (auto-set in non-dev environments)
    cookie_samesite: Literal["lax", "none", "strict"] = "lax"

    @property
    def cookie_secure_flag(self) -> bool:
        """Get the Secure flag for cookies based on environment."""
        if self.cookie_secure is not None:
            return self.cookie_secure
        # SameSite=none requires Secure=true regardless of environment
        if self.cookie_samesite == "none":
            return True
        # Auto-derive: Secure=false only in dev
        return self.environment != "dev"

    # Dev Login (passwordless auth for development)
    # Set to false in production to disable /auth/dev-login endpoint
    # SAFETY: Will be force-disabled in staging/prod environments
    auth_allow_dev_login: bool = True

    @model_validator(mode="after")
    def validate_environment_safety_rails(self) -> "Settings":
        """Enforce environment safety rails.

        - Dev-login is ONLY allowed in dev environment
        - If ENVIRONMENT != dev and auth_allow_dev_login=true, raise error
        """
        if self.environment != "dev" and self.auth_allow_dev_login:
            raise ValueError(
                f"CRITICAL SECURITY ERROR: Environment safety rails violation.\n"
                f"\n"
                f"  Current configuration:\n"
                f"    ENVIRONMENT = {self.environment}\n"
                f"    AUTH_ALLOW_DEV_LOGIN = true\n"
                f"\n"
                f"  This combination is forbidden. Dev-login is only allowed in 'dev' environment.\n"
                f"\n"
                f"  Remediation (choose one):\n"
                f"    1. Set ENVIRONMENT=dev (for local development)\n"
                f"    2. Set AUTH_ALLOW_DEV_LOGIN=false (for staging/prod)\n"
            )
        return self

    # =========================================================================
    # LLM Configuration
    # =========================================================================
    # LLM_PROVIDER: "stub" (default, for testing) or "openai"
    # LLM_MODEL: Model name (provider-specific, optional)
    # LLM_API_KEY: API key (required for OpenAI)
    # =========================================================================
    llm_provider: str = "stub"
    llm_model: str | None = None
    llm_api_key: str | None = None

    # =========================================================================
    # Global Legal Corpus Configuration
    # =========================================================================
    # GLOBAL_CORPUS_ENABLED_IN_PROD: Enable global corpus management in production
    # Default is false for safety. Set to true only after proper review.
    # =========================================================================
    global_corpus_enabled_in_prod: bool = False

    # =========================================================================
    # Platform Admin Bootstrap Configuration
    # =========================================================================
    # PLATFORM_ADMIN_EMAIL: Email of user to designate as platform admin on startup
    # This is a one-time bootstrap mechanism for dev/staging environments.
    #
    # Behavior:
    # - On startup (dev/staging): If user with this email exists, set is_platform_admin=true
    # - If user doesn't exist: Log a warning (do NOT auto-create user)
    # - In production: This is BLOCKED unless GLOBAL_CORPUS_ENABLED_IN_PROD=true
    #
    # Safety:
    # - Only works in dev/staging by default
    # - Requires existing user (no auto-creation)
    # - All bootstrap actions are logged
    # =========================================================================
    platform_admin_email: str | None = None


settings = Settings()
