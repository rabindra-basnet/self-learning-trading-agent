"""Redis async client — lifecycle wrapper (create, ping, dispose)."""

from __future__ import annotations

from app.core.logging.setup import get_logger
from redis.asyncio import Redis, from_url

logger = get_logger("capability.redis")


class RedisConnection:
    def __init__(self, url: str = "redis://localhost:6379/0") -> None:
        self._url = url
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = from_url(self._url, decode_responses=True)
        return self._client

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            logger.warning("redis_ping_failed")
            return False

    async def dispose(self) -> None:
        if self._client is not None:
            await self.client.aclose()
            self._client = None
