"""Add organizations and organization_memberships tables.

Revision ID: 20260402_000003
Revises: 20260402_000002
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa

revision = "20260402_000003"
down_revision = "20260402_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("tenant_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("workspace_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("master_user_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_organizations_tenant_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name="fk_organizations_workspace_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["master_user_id"], ["users.id"], name="fk_organizations_master_user_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
    )
    op.create_index("ix_organizations_workspace_id", "organizations", ["workspace_id"])
    op.create_index("ix_organizations_tenant_id", "organizations", ["tenant_id"])

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("organization_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="MEMBER"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_org_memberships_org_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_org_memberships_user_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_organization_memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_membership_org_user"),
    )
    op.create_index("ix_org_memberships_org_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_org_memberships_user_id", "organization_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
