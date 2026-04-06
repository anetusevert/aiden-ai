"""Add clients, cases, case_documents, case_notes, case_events tables.

Revision ID: 20260406_000003
Revises: 20260406_000002
Create Date: 2026-04-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260406_000003"
down_revision: Union[str, None] = "20260406_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("client_type", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("display_name_ar", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("national_id", sa.String(50), nullable=True),
        sa.Column("nationality", sa.String(100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("trade_name", sa.String(255), nullable=True),
        sa.Column("cr_number", sa.String(100), nullable=True),
        sa.Column("vat_number", sa.String(100), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("incorporation_country", sa.String(100), nullable=True),
        sa.Column("org_type", sa.String(100), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name=op.f("fk_clients_org_id_organizations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_clients_created_by_users"), ondelete="SET NULL"),
    )
    op.create_index("ix_clients_org_id", "clients", ["org_id"])
    op.create_index("ix_clients_client_type", "clients", ["client_type"])
    op.create_index("ix_clients_is_active", "clients", ["is_active"])
    op.create_index("ix_clients_cr_number", "clients", ["cr_number"])

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("title_ar", sa.String(255), nullable=True),
        sa.Column("case_number", sa.String(100), nullable=True),
        sa.Column("internal_ref", sa.String(100), nullable=True),
        sa.Column("practice_area", sa.String(100), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("court_name", sa.String(255), nullable=True),
        sa.Column("court_circuit", sa.String(100), nullable=True),
        sa.Column("judge_name", sa.String(255), nullable=True),
        sa.Column("opposing_counsel", sa.String(255), nullable=True),
        sa.Column("opposing_party", sa.String(255), nullable=True),
        sa.Column("opened_at", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("closed_at", sa.Date(), nullable=True),
        sa.Column("next_deadline", sa.Date(), nullable=True),
        sa.Column("next_deadline_description", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amin_briefing", sa.Text(), nullable=True),
        sa.Column("lead_lawyer", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], name=op.f("fk_cases_org_id_organizations"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_cases_client_id_clients"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_lawyer"], ["users.id"], name=op.f("fk_cases_lead_lawyer_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_cases_created_by_users"), ondelete="SET NULL"),
    )
    op.create_index("ix_cases_org_id", "cases", ["org_id"])
    op.create_index("ix_cases_client_id", "cases", ["client_id"])
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_priority", "cases", ["priority"])
    op.create_index("ix_cases_practice_area", "cases", ["practice_area"])
    op.create_index("ix_cases_next_deadline", "cases", ["next_deadline"])
    op.create_index("ix_cases_lead_lawyer", "cases", ["lead_lawyer"])

    op.create_table(
        "case_documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("attached_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("document_role", sa.String(50), nullable=False, server_default="general"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_documents")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_case_documents_case_id_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["office_documents.id"], name=op.f("fk_case_documents_document_id_office_documents"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attached_by"], ["users.id"], name=op.f("fk_case_documents_attached_by_users"), ondelete="SET NULL"),
        sa.UniqueConstraint("case_id", "document_id", name="uq_case_documents_case_document"),
    )

    op.create_table(
        "case_notes",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_amin_generated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_notes")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_case_notes_case_id_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_case_notes_created_by_users"), ondelete="SET NULL"),
    )
    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"])

    op.create_table(
        "case_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_events")),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], name=op.f("fk_case_events_case_id_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_case_events_created_by_users"), ondelete="SET NULL"),
    )
    op.create_index("ix_case_events_case_id", "case_events", ["case_id"])
    op.create_index("ix_case_events_event_type", "case_events", ["event_type"])
    op.create_index("ix_case_events_event_date", "case_events", ["event_date"])


def downgrade() -> None:
    op.drop_table("case_events")
    op.drop_table("case_notes")
    op.drop_table("case_documents")
    op.drop_table("cases")
    op.drop_table("clients")
