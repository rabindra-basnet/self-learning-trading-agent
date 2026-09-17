"""ClickHouse connection adapter (clickhouse-connect async wrapper)."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import clickhouse_connect
from app.core.config.settings import Settings
from app.core.logging.setup import get_logger
from clickhouse_connect.driver.asyncclient import AsyncClient
from magic_di import Connectable

logger = get_logger("capability.clickhouse")


class ClickHouseConnection(Connectable):
    def __init__(self, settings: Settings) -> None:
        self._cfg: dict[str, Any] = dict(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
            secure=settings.clickhouse_secure,
        )
        self._client: AsyncClient | None = None

    async def __disconnect__(self) -> None:
        await self.dispose()

    async def _get_client(self) -> AsyncClient:
        if self._client is None:
            self._client = await clickhouse_connect.get_async_client(**self._cfg)
        return self._client

    @asynccontextmanager
    async def client_scope(self) -> AsyncGenerator[AsyncClient, None]:
        client = await self._get_client()
        yield client

    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception as exc:
            logger.warning("clickhouse_ping_failed", error_type=type(exc).__name__, error=str(exc))
            return False

    async def dispose(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.close()
            self._client = None
