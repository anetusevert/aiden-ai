"""Alembic environment configuration."""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the SQLAlchemy Base and all models to ensure they're registered
from src.database import Base
from src.models import (  # noqa: F401
    AuditLog,
    Conversation,
    Document,
    DocumentVersion,
    Message,
    PolicyProfile,
    Tenant,
    TwinObservation,
    User,
    UserTwin,
    Workspace,
    WorkspaceMembership,
)

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from environment variable if available
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Alembic uses sync driver, so ensure we use psycopg2 not asyncpg
    if "asyncpg" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
