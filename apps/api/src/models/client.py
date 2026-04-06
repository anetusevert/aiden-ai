"""Client model for case-centric legal practice management."""

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.case import Case
    from src.models.user import User


class Client(Base):
    """A client entity — individual, company, or organisation."""

    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_org_id", "org_id"),
        Index("ix_clients_client_type", "client_type"),
        Index("ix_clients_is_active", "is_active"),
        Index("ix_clients_cr_number", "cr_number"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true",
    )

    # Individual-specific
    national_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Company-specific
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cr_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    incorporation_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Organisation-specific
    org_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Metadata
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )

    # Relationships
    cases: Mapped[list["Case"]] = relationship(
        "Case", back_populates="client", cascade="all, delete-orphan",
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by], lazy="selectin",
    )
