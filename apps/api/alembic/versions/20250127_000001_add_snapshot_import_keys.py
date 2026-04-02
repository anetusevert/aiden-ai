"""Add snapshot import keys for idempotent harvester ingestion.

Revision ID: 20250127_000001
Revises: 20250125_000002
Create Date: 2025-01-27

This migration adds:
1. instrument_key column to legal_instruments for dedupe (jurisdiction, source_name, sha256(url))
2. Unique constraint on (jurisdiction, instrument_key)
3. import_batch_id column to legal_instruments
4. version_key column to legal_instrument_versions for dedupe (raw_sha256)
5. Unique constraint on (legal_instrument_id, version_key)
6. import_batch_id column to legal_instrument_versions
7. imported_at column to legal_instrument_versions

These columns enable idempotent bulk import from gcc-harvester snapshots.
See docs/IMPORT_CONTRACT.md for the full specification.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250127_000001"
down_revision: Union[str, None] = "20250125_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add columns to legal_instruments
    op.add_column(
        "legal_instruments",
        sa.Column(
            "instrument_key",
            sa.Text(),
            nullable=True,
            comment="Dedupe key: {jurisdiction}:{source_name}:{sha256(source_url)[:16]}",
        ),
    )
    op.add_column(
        "legal_instruments",
        sa.Column(
            "import_batch_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
            comment="UUID of the snapshot import batch that created/updated this instrument",
        ),
    )

    # Step 2: Add index on instrument_key
    op.create_index(
        op.f("ix_legal_instruments_instrument_key"),
        "legal_instruments",
        ["instrument_key"],
        unique=False,
    )

    # Step 3: Add unique constraint on (jurisdiction, instrument_key)
    # Using a partial unique index to allow NULLs (for manually created instruments)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_legal_instruments_jurisdiction_instrument_key
        ON legal_instruments (jurisdiction, instrument_key)
        WHERE instrument_key IS NOT NULL
        """
    )

    # Step 4: Add columns to legal_instrument_versions
    op.add_column(
        "legal_instrument_versions",
        sa.Column(
            "version_key",
            sa.Text(),
            nullable=True,
            comment="Dedupe key: raw_sha256 from harvester snapshot",
        ),
    )
    op.add_column(
        "legal_instrument_versions",
        sa.Column(
            "import_batch_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
            comment="UUID of the snapshot import batch that created this version",
        ),
    )
    op.add_column(
        "legal_instrument_versions",
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when this version was imported from a snapshot",
        ),
    )

    # Step 5: Add index on version_key
    op.create_index(
        op.f("ix_legal_instrument_versions_version_key"),
        "legal_instrument_versions",
        ["version_key"],
        unique=False,
    )

    # Step 6: Add unique constraint on (legal_instrument_id, version_key)
    # Using a partial unique index to allow NULLs (for manually uploaded versions)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_legal_instrument_versions_instrument_version_key
        ON legal_instrument_versions (legal_instrument_id, version_key)
        WHERE version_key IS NOT NULL
        """
    )


def downgrade() -> None:
    # Drop unique constraint on versions
    op.execute("DROP INDEX IF EXISTS uq_legal_instrument_versions_instrument_version_key")

    # Drop index on version_key
    op.drop_index(
        op.f("ix_legal_instrument_versions_version_key"),
        table_name="legal_instrument_versions",
    )

    # Drop columns from legal_instrument_versions
    op.drop_column("legal_instrument_versions", "imported_at")
    op.drop_column("legal_instrument_versions", "import_batch_id")
    op.drop_column("legal_instrument_versions", "version_key")

    # Drop unique constraint on instruments
    op.execute("DROP INDEX IF EXISTS uq_legal_instruments_jurisdiction_instrument_key")

    # Drop index on instrument_key
    op.drop_index(
        op.f("ix_legal_instruments_instrument_key"),
        table_name="legal_instruments",
    )

    # Drop columns from legal_instruments
    op.drop_column("legal_instruments", "import_batch_id")
    op.drop_column("legal_instruments", "instrument_key")
