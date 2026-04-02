"""Refresh session model for token rotation tracking."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.user import User


class RefreshSession(Base):
    """Refresh session model - tracks issued refresh tokens for rotation.

    Each row represents a refresh token that has been issued. When a refresh
    token is used, the old session is revoked (revoked_at set) and a new
    session is created with a new jti.

    This enables:
    - Refresh token rotation (detect reuse attacks)
    - Session listing/management
    - Targeted session revocation

    Attributes:
        id: Primary key UUID
        user_id: The user this session belongs to
        jti: Unique JWT ID claim - identifies this specific refresh token
        created_at: When the token was issued
        expires_at: When the token expires
        revoked_at: When the token was revoked (null if still valid)
        last_used_at: When the token was last used to refresh
        user_agent: Optional browser/client user agent
        ip_address: Optional client IP address
    """

    __tablename__ = "refresh_sessions"
    __table_args__ = (
        Index("ix_refresh_sessions_user_id", "user_id"),
        Index("ix_refresh_sessions_jti", "jti", unique=True),
        Index("ix_refresh_sessions_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    jti: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_sessions")

    def is_valid(self, current_time: datetime) -> bool:
        """Check if this session is valid (not expired, not revoked)."""
        if self.revoked_at is not None:
            return False
        if current_time > self.expires_at:
            return False
        return True
