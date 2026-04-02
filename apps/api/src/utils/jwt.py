"""JWT token utilities for authentication.

This module handles JWT creation and verification for the Aiden.ai API.
Tokens contain user identity and authorization claims.

Token Types:
- Access Token: Short-lived (default 15 min), used for API authorization
- Refresh Token: Long-lived (default 7 days), used to obtain new access tokens
  Contains a unique jti (JWT ID) for rotation tracking.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

import jwt
from pydantic import BaseModel

from src.config import settings


class JWTPayload(BaseModel):
    """JWT token payload structure.

    Contains all claims embedded in access/refresh tokens.
    """

    sub: str  # user_id
    tenant_id: str
    workspace_id: str
    role: str  # ADMIN, EDITOR, or VIEWER
    exp: datetime
    iat: datetime

    # Token type: "access" or "refresh"
    token_type: Literal["access", "refresh"] = "access"

    # Optional claims for extensibility
    email: str | None = None

    # Token version for revocation support (must match user.token_version)
    token_version: int = 1

    # JWT ID - unique identifier for refresh tokens (for rotation tracking)
    jti: str | None = None


class JWTError(Exception):
    """Base exception for JWT-related errors."""

    pass


class TokenExpiredError(JWTError):
    """Raised when token has expired."""

    pass


class InvalidTokenError(JWTError):
    """Raised when token is invalid (malformed, bad signature, etc.)."""

    pass


class TokenTypeMismatchError(JWTError):
    """Raised when token type doesn't match expected type."""

    pass


def create_access_token(
    user_id: str,
    tenant_id: str,
    workspace_id: str,
    role: str,
    email: str | None = None,
    token_version: int = 1,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new JWT access token.

    Args:
        user_id: The user's unique identifier (becomes 'sub' claim)
        tenant_id: The tenant the user belongs to
        workspace_id: The workspace context for this token
        role: User's role in the workspace (ADMIN, EDITOR, VIEWER)
        email: Optional user email to include in token
        token_version: User's current token_version (for revocation support)
        expires_delta: Custom expiration time (defaults to settings.access_token_expires_minutes)

    Returns:
        Encoded JWT token string
    """
    now = datetime.now(UTC)

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expires_minutes)

    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "workspace_id": str(workspace_id),
        "role": role,
        "exp": expire,
        "iat": now,
        "token_version": token_version,
        "token_type": "access",
    }

    if email:
        payload["email"] = email

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    user_id: str,
    tenant_id: str,
    workspace_id: str,
    role: str,
    token_version: int = 1,
    jti: str | None = None,
    expires_delta: timedelta | None = None,
) -> tuple[str, str, datetime]:
    """Create a new JWT refresh token.

    Args:
        user_id: The user's unique identifier (becomes 'sub' claim)
        tenant_id: The tenant the user belongs to
        workspace_id: The workspace context for this token
        role: User's role in the workspace (ADMIN, EDITOR, VIEWER)
        token_version: User's current token_version (for revocation support)
        jti: Optional JWT ID (generated if not provided)
        expires_delta: Custom expiration time (defaults to settings.refresh_token_expires_days)

    Returns:
        Tuple of (encoded_token, jti, expires_at)
    """
    now = datetime.now(UTC)

    if expires_delta is None:
        expires_delta = timedelta(days=settings.refresh_token_expires_days)

    expire = now + expires_delta

    if jti is None:
        jti = str(uuid4())

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "workspace_id": str(workspace_id),
        "role": role,
        "exp": expire,
        "iat": now,
        "token_version": token_version,
        "token_type": "refresh",
        "jti": jti,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    return token, jti, expire


def decode_access_token(token: str) -> JWTPayload:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode

    Returns:
        JWTPayload with the decoded claims

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token is invalid (bad signature, malformed, etc.)
        TokenTypeMismatchError: If the token is not an access token
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        result = JWTPayload(**payload)

        # Validate token type
        if result.token_type != "access":
            raise TokenTypeMismatchError(
                f"Expected access token, got {result.token_type}"
            )

        return result
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {e}") from e


def decode_refresh_token(token: str) -> JWTPayload:
    """Decode and validate a JWT refresh token.

    Args:
        token: The JWT token string to decode

    Returns:
        JWTPayload with the decoded claims

    Raises:
        TokenExpiredError: If the token has expired
        InvalidTokenError: If the token is invalid (bad signature, malformed, etc.)
        TokenTypeMismatchError: If the token is not a refresh token
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        result = JWTPayload(**payload)

        # Validate token type
        if result.token_type != "refresh":
            raise TokenTypeMismatchError(
                f"Expected refresh token, got {result.token_type}"
            )

        # Refresh tokens must have jti
        if not result.jti:
            raise InvalidTokenError("Refresh token missing jti claim")

        return result
    except jwt.ExpiredSignatureError as e:
        raise TokenExpiredError("Refresh token has expired") from e
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid refresh token: {e}") from e
