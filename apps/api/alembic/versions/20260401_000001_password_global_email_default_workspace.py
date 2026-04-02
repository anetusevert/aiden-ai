"""Password auth, global unique email, default workspace.

Revision ID: 20260401_000001
Revises: 20250127_000001
Create Date: 2026-04-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "20260401_000001"
down_revision: Union[str, None] = "20250127_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("email_normalized", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "default_workspace_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
    )

    conn.execute(
        text("UPDATE users SET email_normalized = lower(trim(email)) WHERE email_normalized IS NULL")
    )

    dupes = conn.execute(
        text(
            """
            SELECT email_normalized, count(*) AS c
            FROM users
            WHERE email_normalized IS NOT NULL
            GROUP BY email_normalized
            HAVING count(*) > 1
            """
        )
    ).fetchall()
    if dupes:
        raise RuntimeError(
            "Cannot migrate: duplicate normalized emails exist. Resolve duplicates first: "
            + ", ".join(f"{r[0]} ({r[1]} rows)" for r in dupes[:5])
        )

    op.alter_column("users", "email_normalized", nullable=False)

    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")

    op.create_index(
        "uq_users_email_normalized",
        "users",
        ["email_normalized"],
        unique=True,
    )

    op.create_foreign_key(
        op.f("fk_users_default_workspace_id_workspaces"),
        "users",
        "workspaces",
        ["default_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_users_default_workspace_id"),
        "users",
        ["default_workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_default_workspace_id"), table_name="users")
    op.drop_constraint(
        op.f("fk_users_default_workspace_id_workspaces"),
        "users",
        type_="foreignkey",
    )
    op.drop_index("uq_users_email_normalized", table_name="users")
    op.create_unique_constraint(
        "uq_users_tenant_email",
        "users",
        ["tenant_id", "email"],
    )
    op.drop_column("users", "default_workspace_id")
    op.drop_column("users", "email_normalized")
    op.drop_column("users", "password_hash")
