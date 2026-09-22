"""Alembic environment — async engine, DSN from app settings.

Every slice exposes its own `DeclarativeBase`; each base's metadata is merged
into `target_metadata` here so one migration history covers the whole engine.
Tables carry no schema: migrations build the default `public` schema.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from app.core.config.settings import get_settings
from app.infrastructure.capability.database.base import Base
from app.infrastructure.capability.database.dsn import normalize_asyncpg_dsn

# Importing a slice's model module registers its tables on `Base.metadata`.
from app.modules.auth.infrastructure.stores import postgres_repos  # noqa: F401
from app.modules.trading.infrastructure.repositories import postgres as trading_postgres  # noqa: F401
from app.modules.trading.infrastructure.repositories import postgres_order as trading_order_postgres  # noqa: F401
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(
    obj: Any,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    """Keep autogenerate away from objects this application does not own."""
    return not (type_ == "table" and reflected and compare_to is None)


def _database_url() -> tuple[str, dict[str, object]]:
    return normalize_asyncpg_dsn(get_settings().database_url)


def _configure(**kwargs: Any) -> None:
    context.configure(
        target_metadata=target_metadata,
        include_object=include_object,
        **kwargs,
    )


def run_migrations_offline() -> None:
    url, _ = _database_url()
    _configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url, connect_args = _database_url()
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with engine.connect() as connection:
        await connection.run_sync(_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
