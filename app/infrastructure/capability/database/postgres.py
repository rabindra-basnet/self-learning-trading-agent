"""Postgres async connection/session — capability adapter (sqlalchemy + asyncpg)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.logging.setup import get_logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = get_logger("capability.postgres")


class PostgresConnection:
    def __init__(self, dsn: str, *, pool_size: int = 5, max_overflow: int = 10) -> None:
        self._dsn = dsn
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _ensure_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self._dsn,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                echo=False,
            )
            self._session_factory = async_sessionmaker(bind=self._engine, class_=AsyncSession, expire_on_commit=False)
        return self._engine

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
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            return True
        except Exception:
            logger.warning("postgres_ping_failed")
            return False

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
