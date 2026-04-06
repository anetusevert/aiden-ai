"""Case, CaseDocument, CaseNote, and CaseEvent models for case-centric practice management."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base

if TYPE_CHECKING:
    from src.models.client import Client
    from src.models.office import OfficeDocument
    from src.models.user import User


class Case(Base):
    """A legal case/matter linked to a client."""

    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_org_id", "org_id"),
        Index("ix_cases_client_id", "client_id"),
        Index("ix_cases_status", "status"),
        Index("ix_cases_priority", "priority"),
        Index("ix_cases_practice_area", "practice_area"),
        Index("ix_cases_next_deadline", "next_deadline"),
        Index("ix_cases_lead_lawyer", "lead_lawyer"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()),
    )
    org_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    title_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    internal_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)

    practice_area: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active",
    )
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="medium",
    )

    # Court / litigation fields
    court_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    court_circuit: Mapped[str | None] = mapped_column(String(100), nullable=True)
    judge_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opposing_counsel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opposing_party: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Dates
    opened_at: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date(),
    )
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_deadline_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Content
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amin_briefing: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Assignments
    lead_lawyer: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    client: Mapped["Client"] = relationship("Client", back_populates="cases", lazy="selectin")
    lead_lawyer_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[lead_lawyer], lazy="selectin",
    )
    created_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[created_by], lazy="selectin",
    )
    case_documents: Mapped[list["CaseDocument"]] = relationship(
        "CaseDocument", back_populates="case", cascade="all, delete-orphan",
    )
    notes: Mapped[list["CaseNote"]] = relationship(
        "CaseNote", back_populates="case", cascade="all, delete-orphan",
    )
    events: Mapped[list["CaseEvent"]] = relationship(
        "CaseEvent", back_populates="case", cascade="all, delete-orphan",
    )


class CaseDocument(Base):
    """Junction table linking OfficeDocuments to Cases."""

    __tablename__ = "case_documents"
    __table_args__ = (
        UniqueConstraint("case_id", "document_id", name="uq_case_documents_case_document"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("office_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    attached_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    document_role: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="general",
    )

    case: Mapped["Case"] = relationship("Case", back_populates="case_documents")
    document: Mapped["OfficeDocument"] = relationship("OfficeDocument", lazy="selectin")
    attached_by_user: Mapped["User"] = relationship("User", lazy="selectin")


class CaseNote(Base):
    """A note attached to a case — user or Amin generated."""

    __tablename__ = "case_notes"
    __table_args__ = (
        Index("ix_case_notes_case_id", "case_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_amin_generated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false",
    )
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

    case: Mapped["Case"] = relationship("Case", back_populates="notes")
    created_by_user: Mapped["User | None"] = relationship("User", lazy="selectin")


class CaseEvent(Base):
    """Timeline event for a case — audit trail of all activity."""

    __tablename__ = "case_events"
    __table_args__ = (
        Index("ix_case_events_case_id", "case_id"),
        Index("ix_case_events_event_type", "event_type"),
        Index("ix_case_events_event_date", "event_date"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()),
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    case: Mapped["Case"] = relationship("Case", back_populates="events")
    created_by_user: Mapped["User | None"] = relationship("User", lazy="selectin")
