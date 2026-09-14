"""ClickHouse connection adapter (clickhouse-connect async wrapper)."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import clickhouse_connect
from app.core.logging.setup import get_logger
from clickhouse_connect.driver.asyncclient import AsyncClient

logger = get_logger("capability.clickhouse")


class ClickHouseConnection:
    def __init__(
        self, host: str, port: int = 8123, user: str = "default", password: str = "", database: str = "trading"
    ) -> None:
        self._cfg = dict(host=host, port=port, username=user, password=password, database=database)
        self._client: AsyncClient | None = None

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
            client = await self._get()
            await client.ping()
            return True
        except Exception:
            logger.warning("clickhouse_ping_failed")
            return False

    async def dispose(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.close()
            self._client = None
