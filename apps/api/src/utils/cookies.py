"""Cookie utilities for httpOnly auth cookies.

This module handles setting and clearing authentication cookies.
Uses httpOnly cookies to prevent XSS token theft.

Cookie Configuration:
- access_token: httpOnly, Path=/
- refresh_token: httpOnly, Path=/auth (or /api/auth behind proxy)
- SameSite is configurable via COOKIE_SAMESITE env var (default: lax)

Security Notes:
- Secure flag is environment-dependent:
  - dev: Secure=false (allows localhost without HTTPS)
  - staging/prod: Secure=true (enforced even before SSL)
  - SameSite=none forces Secure=true regardless of environment
- SameSite=lax provides CSRF protection for same-site deployments
- SameSite=none is required for cross-site deployments (e.g. separate subdomains)
- When behind reverse proxy with API_ROOT_PATH=/api, cookie paths are adjusted
"""

from fastapi import Response

from src.config import settings

# Cookie names
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def _get_access_token_path() -> str:
    """Get access token cookie path, accounting for API root path.

    Access token uses "/" in direct mode, or the root_path in proxy mode.
    """
    # Access token needs to be sent to all endpoints
    # In proxy mode, paths are /api/*, so use /api (or just /)
    # Using "/" is safest as it works in both modes
    return "/"


def _get_refresh_token_path() -> str:
    """Get refresh token cookie path, accounting for API root path.

    Refresh token is only sent to /auth/* endpoints.
    When behind proxy at /api, it needs to be /api/auth.
    """
    root_path = settings.api_root_path.rstrip("/") if settings.api_root_path else ""
    return f"{root_path}/auth" if root_path else "/auth"


def set_access_token_cookie(
    response: Response,
    token: str,
    max_age_seconds: int | None = None,
) -> None:
    """Set the access token httpOnly cookie.

    Args:
        response: FastAPI Response object
        token: The access token JWT string
        max_age_seconds: Optional max age (defaults to access_token_expires_minutes)
    """
    if max_age_seconds is None:
        max_age_seconds = settings.access_token_expires_minutes * 60

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        max_age=max_age_seconds,
        path=_get_access_token_path(),
        secure=settings.cookie_secure_flag,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def set_refresh_token_cookie(
    response: Response,
    token: str,
    max_age_seconds: int | None = None,
) -> None:
    """Set the refresh token httpOnly cookie.

    Args:
        response: FastAPI Response object
        token: The refresh token JWT string
        max_age_seconds: Optional max age (defaults to refresh_token_expires_days)
    """
    if max_age_seconds is None:
        max_age_seconds = settings.refresh_token_expires_days * 24 * 60 * 60

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        max_age=max_age_seconds,
        path=_get_refresh_token_path(),
        secure=settings.cookie_secure_flag,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_max_age: int | None = None,
    refresh_max_age: int | None = None,
) -> None:
    """Set both auth cookies (access + refresh).

    Args:
        response: FastAPI Response object
        access_token: The access token JWT string
        refresh_token: The refresh token JWT string
        access_max_age: Optional max age for access token
        refresh_max_age: Optional max age for refresh token
    """
    set_access_token_cookie(response, access_token, access_max_age)
    set_refresh_token_cookie(response, refresh_token, refresh_max_age)


def clear_access_token_cookie(response: Response) -> None:
    """Clear the access token cookie.

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path=_get_access_token_path(),
        secure=settings.cookie_secure_flag,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def clear_refresh_token_cookie(response: Response) -> None:
    """Clear the refresh token cookie.

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path=_get_refresh_token_path(),
        secure=settings.cookie_secure_flag,
        httponly=True,
        samesite=settings.cookie_samesite,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies (access + refresh).

    Args:
        response: FastAPI Response object
    """
    clear_access_token_cookie(response)
    clear_refresh_token_cookie(response)
