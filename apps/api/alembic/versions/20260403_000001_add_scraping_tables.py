"""Add scraping_sources and scraping_jobs tables.

Revision ID: 20260403_000001
Revises: 20260402_000003
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260403_000001"
down_revision = "20260402_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scraping_sources",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("connector_name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("harvest_limit", sa.Integer(), nullable=False, server_default=sa.text("500")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_job_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_scraping_sources"),
    )
    op.create_index("ix_scraping_sources_connector_name", "scraping_sources", ["connector_name"])
    op.create_index("ix_scraping_sources_enabled", "scraping_sources", ["enabled"])

    op.create_table(
        "scraping_jobs",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("source_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("connector_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("triggered_by", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_listed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("items_upserted", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("items_failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("run_log", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["source_id"], ["scraping_sources.id"],
            name="fk_scraping_jobs_source_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scraping_jobs"),
    )
    op.create_index("ix_scraping_jobs_source_id", "scraping_jobs", ["source_id"])
    op.create_index("ix_scraping_jobs_status", "scraping_jobs", ["status"])
    op.create_index("ix_scraping_jobs_created_at_desc", "scraping_jobs", [sa.text("created_at DESC")])

    # Add FK from scraping_sources.last_job_id -> scraping_jobs.id
    op.create_foreign_key(
        "fk_scraping_sources_last_job_id",
        "scraping_sources", "scraping_jobs",
        ["last_job_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_scraping_sources_last_job_id", "scraping_sources", type_="foreignkey")
    op.drop_table("scraping_jobs")
    op.drop_table("scraping_sources")
