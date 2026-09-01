"""Alembic environment configuration for SUS.

Uses the application's database engine and ORM metadata so that:
- The same database URL (from Settings) is used by both the app and migrations.
- All models registered on Base.metadata are available for autogenerate.
- SQLite pragmas (WAL, foreign_keys) are applied to the migration connection.
"""

from __future__ import annotations

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, event

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Set up Python logging from the .ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ---------------------------------------------------------------------------
# Import application metadata
# ---------------------------------------------------------------------------
# We import Base (DeclarativeBase) and all ORM models so that
# Base.metadata is fully populated for autogenerate / migration comparison.

from src.config import settings  # noqa: E402
from src.database.base import Base  # noqa: E402
import src.database.models  # noqa: E402, F401  — registers all tables on Base.metadata

target_metadata = Base.metadata

# Resolve database URL with clear priority:
#   1. SUS_DATABASE_URL env var (for tests / overrides)
#   2. Application Settings (production default)
#   3. alembic.ini placeholder (fallback)
import os as _os
_db_url = _os.environ.get("SUS_DATABASE_URL") or settings.database_url
config.set_main_option("sqlalchemy.url", _db_url)


# ---------------------------------------------------------------------------
# SQLite connection event handler (pragmas)
# ---------------------------------------------------------------------------
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable WAL mode and foreign keys on SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without a live connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL to stdout (or a file) without requiring a live database
    connection. Useful for generating migration SQL scripts.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (live connection)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Apply SQLite pragmas if needed
    if settings.database_url.startswith("sqlite"):
        event.listen(connectable, "connect", _set_sqlite_pragmas)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
