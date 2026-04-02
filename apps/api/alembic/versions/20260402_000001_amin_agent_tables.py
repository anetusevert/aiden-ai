"""Amin agent tables: conversations, messages, user_twins, twin_observations.

Revision ID: 20260402_000001
Revises: 20260401_000001
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260402_000001"
down_revision = "20260401_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_conversations_workspace_id_workspaces", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_conversations_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_created_at", "conversations", ["created_at"])

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_call_id", sa.String(200), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], name="fk_messages_conversation_id_conversations", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    op.create_table(
        "user_twins",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("profile", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("work_patterns", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("drafting_style", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("review_priorities", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("learned_corrections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("personality_model", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("consolidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_twins_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_twins"),
        sa.UniqueConstraint("user_id", name="uq_user_twins_user_id"),
    )

    op.create_table(
        "twin_observations",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("observation_type", sa.String(100), nullable=False),
        sa.Column("observation_data", postgresql.JSONB(), nullable=False),
        sa.Column("consolidated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_twin_observations_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_twin_observations"),
    )
    op.create_index("ix_twin_observations_user_id", "twin_observations", ["user_id"])
    op.create_index("ix_twin_observations_consolidated", "twin_observations", ["consolidated"])


def downgrade() -> None:
    op.drop_table("twin_observations")
    op.drop_table("user_twins")
    op.drop_table("messages")
    op.drop_table("conversations")
