"""Add policy_profiles table and workspace policy_profile_id FK.

Revision ID: 20250124_000003
Revises: 20250124_000002
Create Date: 2025-01-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250124_000003"
down_revision: Union[str, None] = "20250124_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create policy_profiles table
    op.create_table(
        "policy_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_policy_profiles_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy_profiles")),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_policy_profiles_tenant_name"
        ),
    )
    op.create_index(
        op.f("ix_policy_profiles_tenant_id"),
        "policy_profiles",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_policy_profiles_tenant_default"),
        "policy_profiles",
        ["tenant_id", "is_default"],
        unique=False,
    )

    # Add policy_profile_id column to workspaces table
    op.add_column(
        "workspaces",
        sa.Column(
            "policy_profile_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        op.f("fk_workspaces_policy_profile_id_policy_profiles"),
        "workspaces",
        "policy_profiles",
        ["policy_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_workspaces_policy_profile_id"),
        "workspaces",
        ["policy_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remove policy_profile_id from workspaces
    op.drop_index(op.f("ix_workspaces_policy_profile_id"), table_name="workspaces")
    op.drop_constraint(
        op.f("fk_workspaces_policy_profile_id_policy_profiles"),
        "workspaces",
        type_="foreignkey",
    )
    op.drop_column("workspaces", "policy_profile_id")

    # Drop policy_profiles table
    op.drop_index(
        op.f("ix_policy_profiles_tenant_default"), table_name="policy_profiles"
    )
    op.drop_index(op.f("ix_policy_profiles_tenant_id"), table_name="policy_profiles")
    op.drop_table("policy_profiles")
