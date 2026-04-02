"""Digital twin models for personalized Amin behavior."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.user import User


class UserTwin(Base):
    """Consolidated digital twin profile for a user.

    Stores learned preferences, patterns, and context that
    make Amin's responses personalized to each lawyer.
    """

    __tablename__ = "user_twins"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    profile: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    work_patterns: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    drafting_style: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    review_priorities: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    learned_corrections: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    personality_model: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    soul_dimensions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
    interaction_count: Mapped[int] = mapped_column(
        default=0, server_default="0"
    )
    consolidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")


class TwinObservation(Base):
    """Raw observation recorded during a user-Amin interaction.

    Observations are the input to the dream consolidation cycle.
    They capture what happened (tools used, topics discussed, preferences shown)
    and are periodically consolidated into the UserTwin profile.
    """

    __tablename__ = "twin_observations"
    __table_args__ = (
        Index("ix_twin_observations_user_id", "user_id"),
        Index("ix_twin_observations_consolidated", "consolidated"),
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
    observation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    observation_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    consolidated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")
