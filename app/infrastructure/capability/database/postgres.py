"""Postgres async connection/session — capability adapter (sqlalchemy + asyncpg)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config.settings import Settings
from app.core.logging.setup import get_logger
from app.infrastructure.capability.database.dsn import normalize_asyncpg_dsn
from magic_di import Connectable
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = get_logger("capability.postgres")


class PostgresConnection(Connectable):
    def __init__(self, settings: Settings) -> None:
        self._dsn = settings.database_url
        self._pool_size = 5
        self._max_overflow = 10
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def __disconnect__(self) -> None:
        await self.dispose()

    def _ensure_engine(self) -> AsyncEngine:
        if self._engine is None:
            dsn, connect_args = normalize_asyncpg_dsn(self._dsn)
            self._engine = create_async_engine(
                dsn,
                pool_pre_ping=True,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                connect_args=connect_args,
                echo=False,
            )
            self._session_factory = async_sessionmaker(bind=self._engine, class_=AsyncSession, expire_on_commit=False)
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Per-call session maker — repos create their own session per operation."""
        if self._session_factory is None:
            self._ensure_engine()
        assert self._session_factory is not None
        return self._session_factory

    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        factory = self._session_factory or async_sessionmaker(
            bind=self._ensure_engine(), class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            yield session

    async def ping(self) -> bool:
        engine = self._ensure_engine()
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("postgres_ping_failed", error_type=type(exc).__name__, error=str(exc))
            return False

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
